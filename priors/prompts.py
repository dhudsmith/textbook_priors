"""prompts: the two prompts, both pure functions of the bank and the label map (WORKFLOW.md section 7).

The concept prompt asks for a level per concept and never names a class; the zero-shot prompt asks
for a distribution over the class names and never mentions a concept. They are separate calls: in
one prompt the concept answers could be rationalisations of a class the model had already chosen,
and H2 would be circular. Every scale level is rendered with its anchor (the described visual
referent the bank cites), so an ordinal answer means what the source meant rather than what the
model guessed; the model still replies with the bare token, so the parser is unchanged either way.

Parsing never guesses: an answer that is not one of the listed tokens is a missing answer.
"""
from __future__ import annotations

import hashlib
import json
import re

import numpy as np

CONCEPT_SYSTEM = (
    "You are a careful observer describing the visual features of a single medical image. "
    "You answer only from what is visible in the image, choosing one of the listed levels for "
    "each question, and you reply with a JSON object and nothing else."
)
ZEROSHOT_SYSTEM = (
    "You are a careful reader of a single medical image. You reply with a JSON object and "
    "nothing else."
)


def render_concept(bank: dict, anchors: bool = True) -> tuple[str, str]:
    """(system, user) for the concept prompt. Names no class; lists every concept with its scale."""
    lines = [f"The image is {bank['modality']}.", "",
             "Answer each question below from the image alone. For each question choose exactly one "
             "of its listed levels" + (", using the description after each level as the meaning of that "
                                       "level." if anchors else ".")]
    for i, c in enumerate(bank["concepts"], 1):
        lines += ["", f"{i}. id: {c['id']}", f"   question: {c['question']}"]
        for lv in c["scale"]:
            if anchors:
                lines.append(f"   - {lv}: {' '.join(str(c['anchors'][lv]['text']).split())}")
            else:
                lines.append(f"   - {lv}")
    ids = [c["id"] for c in bank["concepts"]]
    example = json.dumps({ids[0]: bank["concepts"][0]["scale"][0]})[:-1] + ", ...}"
    lines += ["", "Reply with one JSON object mapping every id above to the chosen level token, written "
                  f"exactly as listed, for example {example}. Include every id exactly once and no other keys."]
    return CONCEPT_SYSTEM, "\n".join(lines)


def zeroshot_options(names: list[str], override: dict | None) -> list[str]:
    """Display names for arm A in label-index order: the label map, or config's clinical names
    where the keys are not clinical terms (retinamnist's digit strings)."""
    if not override:
        return list(names)
    return [str(override.get(n, n)) for n in names]


def render_zeroshot(modality: str, options: list[str]) -> tuple[str, str]:
    """(system, user) for the zero-shot prompt. Mentions no concept; states the modality."""
    lines = [f"The image is {modality}.", "",
             "Which one of the following best describes this image?"]
    lines += [f"- {o}" for o in options]
    lines += ["", "Reply with one JSON object whose keys are exactly the options above, written as listed, "
                  "and whose values are your probabilities that each option is the correct description. "
                  "Include every option; the probabilities must sum to 1."]
    return ZEROSHOT_SYSTEM, "\n".join(lines)


def prompt_hash(system: str, user: str) -> str:
    return hashlib.sha256((system + "\n\x00\n" + user).encode()).hexdigest()


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.S)


def extract_json(text: str):
    """The first JSON object in a reply, tolerating a code fence or prose around it; None if none."""
    if text is None:
        return None
    m = _FENCE.search(text)
    cand = m.group(1) if m else text
    start = cand.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(cand)):
            ch = cand[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    try:
                        obj = json.loads(cand[start:i + 1])
                        return obj if isinstance(obj, dict) else None
                    except json.JSONDecodeError:
                        break
        start = cand.find("{", start + 1)
    return None


def _norm(s) -> str:
    return re.sub(r"\s+", " ", str(s)).strip().lower()


def parse_concept(text: str, bank: dict) -> tuple[dict, int]:
    """id -> level (None where missing or not on the scale); and the count of missing answers."""
    obj = extract_json(text) or {}
    keys = {_norm(k): v for k, v in obj.items()}
    out, missing = {}, 0
    for c in bank["concepts"]:
        v = keys.get(_norm(c["id"]))
        tokens = {_norm(lv): lv for lv in c["scale"]}
        lv = tokens.get(_norm(v)) if isinstance(v, str) else None
        out[c["id"]] = lv
        missing += lv is None
    return out, missing


def parse_zeroshot(text: str, options: list[str]):
    """A probability vector over the options in order, or None when the reply is unusable. Missing
    options count as 0; anything non-numeric or a non-positive total is unusable."""
    obj = extract_json(text)
    if not obj:
        return None
    keys = {_norm(k): v for k, v in obj.items()}
    p = np.zeros(len(options))
    for i, o in enumerate(options):
        v = keys.get(_norm(o))
        if v is None:
            continue
        try:
            p[i] = max(float(v), 0.0)
        except (TypeError, ValueError):
            return None
    s = p.sum()
    if not np.isfinite(s) or s <= 0:
        return None
    return p / s
