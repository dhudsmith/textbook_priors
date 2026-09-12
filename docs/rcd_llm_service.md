# The RCD LLM service, as this project found it

Reference notes on `https://llm.rcd.clemson.edu/v1`, the shared service this workflow's scoring
stage calls. Two kinds of statement are mixed here and are labelled: what the **documentation**
says, and what this project **measured**. No rule reads this file; it is context for a person or
an agent deciding what to ask the service for. Facts that a rule depends on live in
`config/config.yaml`, and findings stay in `CHANGELOG.md`.

Documentation captured 2026-09-12 from the RCD *Available Models* page; the model metadata below
was read the same day from the service's own endpoint, which is the authority when the two differ.

## Asking the service what it has

The documented `/v1/models` endpoint lists ids only. The **`?full=true`** form is the useful one
and is how every table below was built:

```bash
curl -s -H "Authorization: Bearer $RCD_LLM_API_KEY" \
  'https://llm.rcd.clemson.edu/v1/models?full=true'
```

Each entry carries `features`, `lifecycle`, `license`, `endpoints`, `max_context`, a prose
`description`, `instances_running`, and — the field that matters most here — a `reasoning` block
naming the effort levels that model accepts. Prefer this endpoint over probing: a call that
answers tells you the model exists, but the metadata tells you what it supports before you spend
anything.

**The metadata covers locally hosted models only.** The same listing also returns the OpenAI
gateway models (`gpt-*`, `o*`), and for those the `features` list is absent, so a gateway model
that does accept images is not marked as accepting them. Measured, not documented: `gpt-5.5` and
`gpt-5.6-terra` both answered this workflow's concept prompt with a 224-pixel image attached.

## Lifecycle tiers

Documented. A model's tier says what promise the service makes about it, and a study that runs for
weeks should read this before choosing.

| tier | what it promises |
|---|---|
| `experimental` | under evaluation; the engine may be buggy or updated; may be removed without notice |
| `active` | stable, no engine updates expected, deprecated for at least a week before retirement |
| `active-lts` | as `active`, plus two weeks' notice and never retired mid-semester |
| `deprecated` | usable until a stated `retirement_date` |
| `retired` | offline until requested; kept so published work can be replicated |

The four models this study scores are all `active`. The newer Qwen builds (`qwen3.6-27b-fp8`,
`qwen3.6-35b-a3b-fp8`) are `experimental`, which is a reason to pin the served model name in every
manifest — as this workflow already does — rather than a reason to avoid them.

## Vision-capable models (locally hosted)

Read 2026-09-12 from `?full=true`, filtered to entries whose `features` include `images`.

| model | lifecycle | reasoning levels | context | note |
|---|---|---|---|---|
| `qwen3.5-9b` | active | none, high | 262144 | this study's ladder, smallest |
| `gemma-4-12b` | active | none, high | 262144 | this study's ladder |
| `qwen3.8-27b-fp8` | active | none, low, medium, xhigh | 262144 | this study's primary model |
| `gemma-4-31b` | active | none, high | 262144 | this study's ladder, largest |
| `qwen3.6-27b-fp8` | experimental | none, high | 262144 | newer generation, same size as the primary |
| `qwen3.6-35b-a3b-fp8` | experimental | none, high | 262144 | mixture of experts, ~3B active |
| `qwen3-omni-30b-a3b` | active | none, high | 32768 | audio and video as well as images |
| `cub` | active | (alias) | 262144 | **alias** for `qwen3.8-27b-fp8` |
| `Qwen3.6-27B-LoRA-fermipy` | experimental | — | — | no instance running; a domain LoRA |

**No open-weight vision model larger than `gemma-4-31b` is served.** The largest model on the
service, `glm-5.3` (753B, aliased as `tiger`), is text-only, as are `deepseek-v4-pro`,
`gptoss-120b` and the GLM 5.x builds: they reject an image with
`400 ... is not a multimodal model`. So this study's H3 ladder cannot be extended upward in
parameter count without leaving open weights. It can be extended *sideways* — a newer generation
at the same size — or to a closed gateway model as a reference bar rather than a ladder point.

**Two aliases exist and both are traps for a study.** `cub` ("a smaller agentic capable model")
and `tiger` ("the most powerful model we are currently hosting") point at whatever the service
currently considers best; `cub`'s target today is this study's own primary model. An alias makes
an archive unreproducible by design, which is exactly what recording `served_model` in every
manifest defends against. Name the target, never the alias.

## Reasoning: what we got wrong, and what is true

**Measured 2026-09-12, and it corrects an earlier conclusion of this project.** The claim in
`WORKFLOW.md` §7 and in `priors/llm.py` was that the primary model "spends its whole token budget
in `reasoning_content` and returns nothing" with thinking on. That is what was observed, but the
cause was not the service: it was `max_tokens: 512`, this workflow's own budget. Thinking works.

One call per cell, the real concept prompt and a real 224-pixel image, pneumoniamnist image 0:

| model | thinking | budget 512 | budget 2048 | budget 4096+ |
|---|---|---|---|---|
| `qwen3.8-27b-fp8` | off | parses, 112 tok, 3.8 s | same | same |
| `qwen3.8-27b-fp8` | on | truncated | parses, 1578 tok, 62 s | parses |
| `gemma-4-12b` | on | truncated | parses, 1447 tok, 10 s | — |
| `gemma-4-31b` | on | truncated | parses, 1171 tok, 30 s | — |
| `qwen3.5-9b` | on | truncated | truncated | still truncated at 8192 |

So three of the four models answer with thinking on once the budget is four times larger, at
roughly ten to sixteen times the wall-clock per call. `qwen3.5-9b` is the exception and did not
finish a chain of thought within 8192 tokens on this prompt.

**`reasoning_effort` is a first-class parameter on the local stack**, and is cleaner than the
`chat_template_kwargs.enable_thinking` switch this workflow sends (`priors/llm.py`). The levels a
model accepts are in its `reasoning` metadata. On the primary model, all four work:

| `reasoning_effort` | completion tokens | wall clock | answer parses |
|---|---|---|---|
| `none` | 112 | 4.9 s | yes |
| `low` | 982 | 39.4 s | yes |
| `medium` | 986 | 41.3 s | yes |
| `xhigh` | 1578 | 68.0 s | yes |

Note that the service's **default** for this model is `xhigh`, so a caller who sets nothing gets
the slowest and most expensive setting. This workflow always sets the switch explicitly, which is
why its archive is consistent.

The gateway models take `reasoning_effort` too but reject `minimal`, and they require
`max_completion_tokens` where the local stack takes `max_tokens`.

## Answer fields

Measured, and the reason `priors/llm.py` archives the whole message object. A served model may put
its answer in `content`, in `reasoning_content`, or in `reasoning`. With thinking **off**,
`qwen3.5-9b` puts finished JSON in `reasoning` — not a chain of thought, the answer itself. With
thinking **on**, every model tested put the chain of thought in `reasoning` and the answer in
`content`, so the field a reader should trust depends on the setting. A reader that knows only
`content` recorded 3,000 good answers as missing once (`CHANGELOG.md`, 2026-09-11).

## Throughput

Measured on this workflow's own jobs, and the single most important operational fact here:
**concurrency buys no throughput on the primary model.** One call costs 1.5 s alone and 42.8 s
with 24 of our own jobs in flight; aggregate throughput is flat or slightly worse. The published
`concurrency` figures are a politeness limit, not a rate. Budget wall clock from the serial rate
and the number of calls, not from the cap. The full measurement is in `CHANGELOG.md`
(2026-09-12, "The service serialises us").

Multiply that by the thinking-on factor above before planning any run with reasoning enabled.
