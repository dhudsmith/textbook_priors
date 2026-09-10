"""llm: the client against the RCD OpenAI-compatible service, and nothing about prompts or banks.

The key is read from an owner-only file whose path is in config; it is never in config, the
repository, a command line or a log. Backoff on 429 and 5xx and on connection errors; the raw
response text is what the caller archives before parsing (WORKFLOW.md section 7). `openai` is
imported lazily so the retry logic is testable in the light tier with a fake transport.
"""
from __future__ import annotations

import base64
import io
import os
import random
import time
from pathlib import Path

import numpy as np

RETRY_STATUS = {408, 409, 425, 429, 500, 502, 503, 504}


def read_key(path) -> str:
    p = Path(os.path.expanduser(str(path)))
    if not p.exists():
        raise FileNotFoundError(f"LLM key file {p} not found; see WORKFLOW.md section 7")
    key = p.read_text().strip()
    if not key:
        raise ValueError(f"LLM key file {p} is empty")
    return key


def make_client(cfg: dict):
    import openai
    return openai.OpenAI(api_key=read_key(cfg["key_file"]), base_url=cfg["base_url"],
                         timeout=float(cfg.get("timeout_s", 120)), max_retries=0)


def image_data_url(img: np.ndarray) -> str:
    """A uint8 image (H, W) or (H, W, 3) as a PNG data URL."""
    from PIL import Image
    arr = np.asarray(img)
    mode = "L" if arr.ndim == 2 else "RGB"
    buf = io.BytesIO()
    Image.fromarray(arr, mode=mode).save(buf, format="PNG", optimize=False)
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def status_of(exc) -> int | None:
    for attr in ("status_code", "status", "code"):
        v = getattr(exc, attr, None)
        if isinstance(v, int):
            return v
    resp = getattr(exc, "response", None)
    v = getattr(resp, "status_code", None)
    return v if isinstance(v, int) else None


def is_retryable(exc) -> bool:
    """429 and 5xx (and the few 4xx that mean "try again"), plus connection and timeout errors,
    which the openai package raises without a status code."""
    s = status_of(exc)
    if s is not None:
        return s in RETRY_STATUS
    name = type(exc).__name__
    return name in {"APIConnectionError", "APITimeoutError", "ConnectionError", "TimeoutError", "ReadTimeout"}


def call_with_backoff(send, *, http_retries: int, backoff_s: float, sleep=time.sleep, rng=random.random,
                      max_backoff_s: float = 120.0):
    """send() with exponential backoff and jitter on retryable failures. Returns (result, attempts);
    re-raises the last error after `http_retries` failed attempts, and anything non-retryable at once."""
    attempts = 0
    while True:
        attempts += 1
        try:
            return send(), attempts
        except Exception as exc:                # noqa: BLE001 - classified below
            if not is_retryable(exc) or attempts >= http_retries:
                raise
            delay = min(max_backoff_s, backoff_s * 2 ** (attempts - 1)) * (0.5 + rng())
            sleep(delay)


def chat_request(model: str, system: str, user: str, image_url: str, cfg: dict) -> dict:
    """The keyword arguments of one chat completion, so the request is inspectable and testable."""
    req = dict(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": [
                {"type": "text", "text": user},
                {"type": "image_url", "image_url": {"url": image_url}},
            ]},
        ],
        temperature=float(cfg.get("temperature", 0.0)),
        max_tokens=int(cfg.get("max_tokens", 600)),
    )
    if cfg.get("json_mode"):
        req["response_format"] = {"type": str(cfg["json_mode"])}
    extra = cfg.get("reasoning_extra_body") or {}
    if extra:
        req["extra_body"] = dict(extra)
    return req


def complete(client, request: dict, cfg: dict, sleep=time.sleep) -> dict:
    """One call with backoff. Returns the raw text and what the archive records about the call."""
    t0 = time.time()
    resp, attempts = call_with_backoff(lambda: client.chat.completions.create(**request),
                                       http_retries=int(cfg.get("http_retries", 8)),
                                       backoff_s=float(cfg.get("backoff_s", 2.0)), sleep=sleep)
    choice = resp.choices[0] if getattr(resp, "choices", None) else None
    msg = getattr(choice, "message", None)
    content = getattr(msg, "content", None)
    # vLLM's reasoning parser files a no-think Qwen3.5 reply under reasoning_content and leaves
    # content empty (seen on qwen3.5-9b, 2026-09-09); both are archived, and the answer is read
    # from content when there is one and from reasoning_content otherwise.
    reasoning = getattr(msg, "reasoning_content", None) or getattr(msg, "reasoning", None)
    text = content if isinstance(content, str) and content.strip() else reasoning
    usage = getattr(resp, "usage", None)
    return {
        "text": text,
        "content": content,
        "reasoning_content": reasoning,
        "served_model": getattr(resp, "model", None),
        "finish_reason": getattr(choice, "finish_reason", None),
        "usage": {k: getattr(usage, k, None) for k in ("prompt_tokens", "completion_tokens", "total_tokens")} if usage else None,
        "http_attempts": attempts,
        "latency_s": round(time.time() - t0, 3),
    }


def list_models(client) -> list[str]:
    return sorted(m.id for m in client.models.list().data)
