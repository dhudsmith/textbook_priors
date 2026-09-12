"""score: one image, one prompt, one archived answer.

This is the deterministic half of the scoring stage. `priors/llm.py` makes the call; everything
here turns a sampled image into the bytes the model sees, and a reply into either a validated
answer or a recorded absence. Nothing here guesses: an answer that does not parse, or that names a
level the scale does not have, becomes `null` with the raw text kept beside it, because a fabricated
level would enter arm C's design matrix as a real observation (WORKFLOW.md section 7).

The retry policy is the one the plan fixes: one retry with a doubled token budget on a malformed
answer, then missing. Truncation is the failure this is aimed at - a reply cut off mid-JSON is the
common malformed answer - and doubling the budget is the one repair that can fix it without
putting words in the model's mouth.
"""
from __future__ import annotations

import base64
import json
import re
import time
from io import BytesIO

import numpy as np
from PIL import Image

# A fenced block is the common wrapper a chat model puts round JSON even when told not to.
_FENCE = re.compile(r"^\s*```(?:json)?\s*(.*?)\s*```\s*$", re.DOTALL)


def png_data_url(image: np.ndarray) -> str:
    """One sampled image as the data URL the chat API takes.

    PNG because it is lossless: the study asks what a model sees in a 224-pixel medical image, and
    JPEG artefacts at the scale of a microaneurysm would be part of the answer.
    """
    array = np.asarray(image)
    if array.ndim == 2:
        mode = "L"
    elif array.ndim == 3 and array.shape[2] == 3:
        mode = "RGB"
    else:
        raise ValueError(f"cannot encode an image of shape {array.shape}")
    buffer = BytesIO()
    Image.fromarray(array.astype(np.uint8), mode=mode).save(buffer, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")


def extract_json(text: str):
    """The JSON object in a reply, or None.

    Tolerates the two wrappers that are not the model disobeying in any meaningful sense - a fenced
    block, and prose either side of a single object - and nothing else.
    """
    if not text:
        return None
    fenced = _FENCE.match(text)
    candidate = fenced.group(1) if fenced else text
    try:
        value = json.loads(candidate)
    except json.JSONDecodeError:
        start, end = candidate.find("{"), candidate.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            value = json.loads(candidate[start:end + 1])
        except json.JSONDecodeError:
            return None
    return value if isinstance(value, dict) else None


def parse_concept_answer(text: str, concepts: list[dict]) -> dict:
    """A concept reply against the scales it was asked about.

    Returns one entry per concept, in bank order: the level the model chose, or None. A key that is
    absent, a value that is not a string, and a value that is not a level of that concept's own
    scale are all the same thing here - no answer - and each is named in `invalid` so the archive
    says why. Extra keys the bank did not ask about are recorded and dropped.
    """
    value = extract_json(text)
    answers = {c["id"]: None for c in concepts}
    invalid: dict[str, str] = {}
    if value is None:
        return {"answers": answers, "invalid": {}, "unknown_keys": [], "parsed": False}

    for concept in concepts:
        cid, scale = concept["id"], concept["scale"]
        if cid not in value:
            invalid[cid] = "missing"
            continue
        given = value[cid]
        if isinstance(given, str) and given.strip() in scale:
            answers[cid] = given.strip()
        else:
            invalid[cid] = f"not a level: {given!r}"[:120]
    unknown = [k for k in value if k not in answers]
    return {"answers": answers, "invalid": invalid, "unknown_keys": unknown, "parsed": True}


def parse_zero_shot_answer(text: str, classes: list[str]) -> dict:
    """A zero-shot reply against the class names it was asked about.

    Returns the number the model gave each class, or None. The numbers are kept exactly as they
    came: a distribution that does not sum to one is the model's answer, and rescaling an image's
    vector by its own sum would change how that image ranks against others in every class column,
    which is what the AUC reads. Normalisation, if it happens at all, belongs to the classify stage
    where it is one documented function of this archive.
    """
    value = extract_json(text)
    scores = {name: None for name in classes}
    invalid: dict[str, str] = {}
    if value is None:
        return {"scores": scores, "invalid": {}, "unknown_keys": [], "parsed": False,
                "sums_to_one": None}

    for name in classes:
        if name not in value:
            invalid[name] = "missing"
            continue
        given = value[name]
        if isinstance(given, bool) or not isinstance(given, (int, float)):
            invalid[name] = f"not a number: {given!r}"[:120]
        elif not np.isfinite(given):
            invalid[name] = f"not finite: {given!r}"
        else:
            scores[name] = float(given)
    given_all = [v for v in scores.values() if v is not None]
    return {
        "scores": scores,
        "invalid": invalid,
        "unknown_keys": [k for k in value if k not in scores],
        "parsed": True,
        "sums_to_one": bool(len(given_all) == len(classes) and abs(sum(given_all) - 1.0) < 1e-3),
    }


def is_complete(parsed: dict, key: str = "answers") -> bool:
    """Did every question come back with a usable answer?

    The completeness an image is judged on (WORKFLOW.md section 3): a dataset-model cell more than
    5% incomplete is flagged in the report and excluded from the headline.
    """
    return all(v is not None for v in parsed[key].values())


def chunks(n: int, size: int) -> list[tuple[int, int]]:
    """The (start, stop) of each chunk of work, covering 0..n exactly once.

    One chunk is one job and one archive file, so this partition is what the fan-out is counted in
    and what a rerun is scoped to: a chunk that fails costs its own hundred calls again and nothing
    else. The last chunk is short when the split does not divide evenly.
    """
    if size <= 0:
        raise ValueError(f"chunk size {size}")
    return [(start, min(start + size, n)) for start in range(0, n, size)]


def ask_one(client, prompt: dict, image_url: str, kind: str, schema, max_tokens: int,
            content_retries: int = 1) -> dict:
    """One image, one prompt, up to `content_retries` extra attempts on a malformed answer.

    The repair is a doubled token budget and nothing else - the same prompt, the same temperature -
    because the failure this is aimed at is a reply cut off mid-JSON. Every attempt's raw text is
    kept, including the ones that failed, so the archive shows what the model actually said rather
    than only what could be read from it.
    """
    parse = parse_concept_answer if kind == "concept" else parse_zero_shot_answer
    field = "answers" if kind == "concept" else "scores"
    attempts = []
    budget = max_tokens

    for attempt in range(content_retries + 1):
        started = time.monotonic()
        reply = client.ask(prompt["system"], prompt["user"], image_url=image_url, max_tokens=budget)
        parsed = parse(reply.text, schema)
        attempts.append({
            "max_tokens": budget,
            # Round-trip seconds, kept per attempt because it is what sizes the scoring stage: a
            # chunk of 100 images costs 100 of these, and the rule's runtime request has to say so.
            "elapsed_s": round(time.monotonic() - started, 3),
            "text": reply.text,
            "served_model": reply.served_model,
            "finish_reason": reply.finish_reason,
            "field": reply.field,
            # The whole message, not only the text read out of it: an extraction is a guess about
            # another system's API, and a wrong guess must be repairable from the archive.
            "message": reply.message,
            "transport_attempts": reply.transport_attempts,
            "usage": reply.usage,
        })
        if is_complete(parsed, field):
            break
        budget *= 2

    return {
        field: parsed[field],
        "invalid": parsed["invalid"],
        "unknown_keys": parsed["unknown_keys"],
        "parsed": parsed["parsed"],
        "complete": is_complete(parsed, field),
        "content_attempts": len(attempts),
        "replies": attempts,
        **({"sums_to_one": parsed["sums_to_one"]} if kind == "zero_shot" else {}),
    }
