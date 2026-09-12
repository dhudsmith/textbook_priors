"""llm: the boundary between this workflow and a model it does not control.

Principle 7 of WORKFLOW.md section 5: the LLM boundary is explicit. Everything on this side of it
is recorded - the served model name, the prompt hash, the temperature, the reasoning setting, every
raw reply including the ones that failed to parse - and everything downstream is a deterministic
function of that record. This module makes exactly one kind of call and says exactly what came
back; it does not parse, score, or repair anything (priors/score.py does that).

Three things here were learned from the service rather than designed:

  * **Thinking must be turned off explicitly.** With reasoning left on, the primary model spends
    its whole token budget in `reasoning_content` and returns an empty `content`. The switch is
    `chat_template_kwargs.enable_thinking`, which is not an OpenAI parameter and has to travel in
    `extra_body`.
  * **Served models put the answer in different fields.** `content` is the usual one; one build
    uses `reasoning_content`; `qwen3.5-9b` uses `reasoning`, and with thinking off it puts the
    finished JSON there rather than any chain of thought. A reader that knows only `content`
    records three thousand good answers as missing, which is exactly what happened once.
  * **The whole message is archived, not the text pulled out of it.** Extraction is a reader's
    guess about someone else's API, and a guess belongs downstream of the record: with the raw
    message kept, a wrong guess is re-parsed from the archive instead of re-bought from the
    service.
  * **The service throttles**, so 429 and 5xx are retried with exponential backoff. That is a
    transport concern and is counted separately from the one content retry the scoring stage makes
    on a malformed answer.

The API key is read from a file whose path is in config and whose mode is owner-only. It is never
logged, never written to a manifest, and never passed on a command line.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import openai

# Where a served model may put its answer, in the order they are tried. `content` is the API's own
# field; the other two are what vLLM builds use for reasoning models, and at least one of them
# returns the final answer there even with thinking switched off.
ANSWER_FIELDS = ("content", "reasoning_content", "reasoning")

# Transport failures worth trying again: the service is busy, the connection dropped, or the
# gateway failed. Everything else - a bad request, a missing model, a rejected key - is a bug or a
# misconfiguration, and retrying it would only turn a clear error into a slow one.
RETRYABLE = (
    openai.RateLimitError,
    openai.APIConnectionError,
    openai.APITimeoutError,
    openai.InternalServerError,
)


def load_key(key_file) -> str:
    """The API key, from the owner-only file named in config.

    Read here and nowhere else. A key on a command line would reach the SLURM accounting database
    and every `ps` on the node; a key in a manifest would reach the repository.
    """
    path = Path(key_file).expanduser()
    key = path.read_text().strip()
    if not key:
        raise ValueError(f"{path} is empty")
    return key


def call_with_backoff(fn, attempts: int, base_delay: float = 1.0, retryable=RETRYABLE, sleep=time.sleep):
    """Call `fn`, retrying transport failures with exponential backoff.

    Returns (value, transport_attempts). The attempt count is returned rather than logged because
    it belongs in the unit's manifest: a chunk that needed forty attempts to place a hundred calls
    is evidence about the service, and the next run's concurrency cap should know it.
    """
    for attempt in range(1, attempts + 1):
        try:
            return fn(), attempt
        except retryable:
            if attempt == attempts:
                raise
            sleep(base_delay * 2 ** (attempt - 1))
    raise AssertionError("unreachable")


@dataclass
class Reply:
    """One model reply, as the archive records it."""

    text: str                      # what the model answered, or "" when it answered nothing
    served_model: str              # the name the service reports, not the name we asked for
    finish_reason: str | None
    field: str | None              # which message field the text came out of
    message: dict = field(default_factory=dict)   # the whole message, so a reader bug is fixable
    usage: dict = field(default_factory=dict)
    transport_attempts: int = 1


@dataclass
class Client:
    """One model on one service, with the settings every call shares.

    `reasoning` is transmitted as `chat_template_kwargs.enable_thinking`, the only form the served
    stack understands, and is recorded in every manifest so an archive says how it was produced.
    """

    model: str
    base_url: str
    key_file: str
    temperature: float = 0.0
    reasoning: str = "none"
    retries: int = 4                          # transport attempts, not content retries
    timeout: float = 120.0

    def __post_init__(self):
        self._client = openai.OpenAI(base_url=self.base_url, api_key=load_key(self.key_file),
                                     timeout=self.timeout)

    @property
    def extra_body(self) -> dict:
        return {"chat_template_kwargs": {"enable_thinking": self.reasoning != "none"}}

    def ask(self, system: str, user: str, image_url: str | None = None, max_tokens: int = 512) -> Reply:
        """One call: a system message, a user message, and at most one image."""
        content = [{"type": "text", "text": user}]
        if image_url is not None:
            content.append({"type": "image_url", "image_url": {"url": image_url}})

        def call():
            return self._client.chat.completions.create(
                model=self.model,
                messages=[{"role": "system", "content": system}, {"role": "user", "content": content}],
                temperature=self.temperature,
                max_tokens=max_tokens,
                extra_body=self.extra_body,
            )

        response, attempts = call_with_backoff(call, attempts=self.retries)
        return read_reply(response, attempts)


def as_dict(obj) -> dict:
    """A response object as plain data, whatever SDK version produced it."""
    if obj is None:
        return {}
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    try:
        return dict(obj)
    except Exception:
        return {}


def read_reply(response, transport_attempts: int = 1) -> Reply:
    """Pull the answer out of a completion, wherever the served stack put it.

    The fields are tried in order (ANSWER_FIELDS) and the one that answered is recorded, so a
    reader can tell a normal reply from a fallback rather than guess. The whole message is kept
    beside it: the extraction is a guess about another system's API, and when that guess was wrong
    - qwen3.5-9b answers in `reasoning` - the only way back was to buy the calls again.
    """
    choice = response.choices[0]
    message = as_dict(choice.message)
    text, found = "", None
    for name in ANSWER_FIELDS:
        value = (message.get(name) or "")
        if isinstance(value, str) and value.strip():
            text, found = value.strip(), name
            break
    return Reply(
        text=text,
        served_model=getattr(response, "model", "") or "",
        finish_reason=getattr(choice, "finish_reason", None),
        field=found,
        message=message,
        usage=as_dict(getattr(response, "usage", None)),
        transport_attempts=transport_attempts,
    )
