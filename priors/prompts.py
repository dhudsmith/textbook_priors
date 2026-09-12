"""prompts: the two prompt strings, rendered from the concept bank and the label map.

Both prompts are pure functions of a dataset's bank, its release label map, the image size and the
`vlm.prompt.anchors` switch: no image, no model and no randomness enters here. Rendering is its own
rule (WORKFLOW.md section 7) so that the string sent to the model, the string hashed into every
score manifest, and the string the report or the live demo prints are one artifact rather than
three copies of a format that can drift apart.

Three prompts. The first two are kept separable on purpose, because H2 turns on it:

  * the CONCEPT prompt (arms B and C) asks for one level per concept, renders every level's cited
    anchor text, and never names a class;
  * the ZERO-SHOT prompt (arm A) asks for a distribution over the class names and never mentions
    a concept.

The third deliberately breaks that separation:

  * the DIRECTED prompt (arm D) carries the whole bank - the concepts with their anchors AND each
    class's textbook fingerprint - and then asks for a distribution over the classes. It is the
    same question arm A is asked, by a model that has just been handed the textbook.

Arm D was added after the first results, because H2 failed in a specific way: the permutation
controls showed the bank carries real class information, while arm B's nearest-fingerprint readout
lost to simply asking the model for the diagnosis. That says the estimator is lossy, not that the
bank is empty - and the obvious test is to let the model do the integration instead. Being
post-hoc, it decides nothing: it is reported as an extension, never as a pre-registered test.

Their system messages differ only in the sentence each task requires - both cast the model as an
expert reader - so the comparison is between what is asked for and not between two personas.
"""
from __future__ import annotations

import hashlib

from .data import Bank, one_line

# Both prompts open on the same framing: one image, its modality, its size, and the absence of
# everything a reader would normally have. The bank's `modality` line is the only dataset-specific
# part, and it names an imaging technique, never a diagnosis or a class.
_PREAMBLE = (
    "You are shown one image from a collection of {modality}. The image is {size} by {size} "
    "pixels, and comes with no clinical context, no patient information and no scale bar: judge "
    "only what this image shows."
)

_CONCEPT_SYSTEM = (
    "You are an expert reader of medical images. You report only what is visible in the image, "
    "and you answer with the JSON object you are asked for and nothing else."
)

_ZERO_SHOT_SYSTEM = (
    "You are an expert reader of medical images. You answer with the JSON object you are asked "
    "for and nothing else."
)


def prompt_sha256(system: str, user: str) -> str:
    """The prompt hash every score manifest records: the two messages, joined by a blank line.

    Hashing the pair rather than the user text alone means a change to the system message also
    marks the archive it produced as having been made by a different prompt."""
    return hashlib.sha256(f"{system}\n\n{user}".encode()).hexdigest()


def _message(system: str, user: str, keys: list[str]) -> dict:
    return {"system": system, "user": user, "keys": keys, "sha256": prompt_sha256(system, user)}


def concept_rows(bank: Bank) -> list[dict]:
    """The concepts as the prompt and the response parser see them: id, question, ordered scale and
    the anchor text of each level, all whitespace-normalised. This block travels with the rendered
    prompt so that the score stage validates an answer against the same artifact it sent."""
    rows = []
    for c in bank.concepts:
        anchors = c.get("anchors") or {}
        rows.append(
            {
                "id": c["id"],
                "question": one_line(c["question"]),
                "scale": [str(level) for level in c["scale"]],
                "anchors": {str(level): one_line(anchors[level]["text"]) for level in c["scale"]
                            if level in anchors},
            }
        )
    return rows


def render_concept_prompt(bank: Bank, rows: list[dict], size: int, anchors: bool) -> dict:
    """The concept prompt: one question per concept, its levels in scale order, and with
    `anchors` on, what each level looks like. Names no class, so arm B and arm C cannot be
    rationalisations of a diagnosis the model had already committed to."""
    blocks = []
    for i, row in enumerate(rows, start=1):
        block = [f"{i}. {row['id']}", f"   {row['question']}"]
        if anchors:
            # CONCEPT_BANK.md requires one anchor per level, and the smoke tier holds the bank to
            # it; refuse to render a prompt that would quietly ask about an undescribed level.
            missing = [level for level in row["scale"] if level not in row["anchors"]]
            if missing:
                raise ValueError(f"concept {row['id']} has no anchor text for {missing}")
            block.append("   Levels, in order, and what each looks like:")
            block += [f"     {level}: {row['anchors'][level]}" for level in row["scale"]]
        else:
            # The `bare_levels` extension (WORKFLOW.md section 10): the same questions with the
            # level names alone, which is what the bank looked like before it was anchored.
            block.append("   Levels, in order: " + ", ".join(row["scale"]))
        blocks.append("\n".join(block))

    template = "\n".join(
        f'  "{row["id"]}": "{"|".join(row["scale"])}"' + ("," if i < len(rows) else "")
        for i, row in enumerate(rows, start=1)
    )
    user = "\n\n".join(
        [
            _PREAMBLE.format(modality=bank.modality, size=size),
            f"Answer all {len(rows)} questions below about what is visible in this image. Each "
            "question lists its levels in order. For every question choose the one level that "
            "best fits this image.",
            "\n\n".join(blocks),
            f"Reply with one JSON object and nothing else: exactly {len(rows)} keys, the question "
            "names above, each value one of that question's levels copied exactly as written.",
            "{\n" + template + "\n}",
        ]
    )
    return _message(_CONCEPT_SYSTEM, user, [row["id"] for row in rows])


def render_zero_shot_prompt(bank: Bank, classes: list[str], size: int) -> dict:
    """The zero-shot prompt: the class names in label-index order and a distribution over them.
    Mentions no concept, so arm A is the undirected baseline H2 needs."""
    listing = "\n".join(f"  {i}. {name}" for i, name in enumerate(classes, start=1))
    template = "\n".join(
        f'  "{name}": <probability>' + ("," if i < len(classes) else "")
        for i, name in enumerate(classes, start=1)
    )
    user = "\n\n".join(
        [
            _PREAMBLE.format(modality=bank.modality, size=size),
            f"The image belongs to exactly one of these {len(classes)} categories:\n{listing}",
            f"How likely is each category for this image? Give every category a probability "
            f"between 0 and 1, and make the {len(classes)} probabilities sum to 1.",
            f"Reply with one JSON object and nothing else: exactly {len(classes)} keys, the "
            "category names above copied exactly as written, each value a number.",
            "{\n" + template + "\n}",
        ]
    )
    return _message(_ZERO_SHOT_SYSTEM, user, list(classes))


def render_directed_prompt(bank: Bank, classes: list[str], rows: list[dict], size: int) -> dict:
    """The whole bank in the prompt, and then the zero-shot question.

    Everything the concept prompt says about what to look at, plus what the textbook expects of
    each class, plus the class names - and the model is asked for the same distribution arm A is
    asked for. `any` is rendered as what it means in the bank ("the sources do not commit"), not
    dropped, because a class the literature is silent about on some feature is itself information.
    """
    blocks = []
    for i, row in enumerate(rows, start=1):
        block = [f"{i}. {row['id']}: {row['question']}"]
        block += [f"     {level}: {row['anchors'][level]}" for level in row["scale"]
                  if level in row["anchors"]]
        blocks.append("\n".join(block))

    fingerprints = []
    for name in classes:
        committed = bank.classes[name]["fingerprint"]
        parts = [f"{row['id']} = {committed.get(row['id'])}" for row in rows
                 if committed.get(row["id"]) not in (None, "any")]
        silent = [row["id"] for row in rows if committed.get(row["id"]) == "any"]
        line = f"  {name}: " + ("; ".join(parts) if parts else "no feature is committed")
        if silent:
            line += f"\n      (the sources do not commit on: {', '.join(silent)})"
        fingerprints.append(line)

    listing = "\n".join(f"  {i}. {name}" for i, name in enumerate(classes, start=1))
    template = "\n".join(f'  "{name}": <probability>' + ("," if i < len(classes) else "")
                         for i, name in enumerate(classes, start=1))
    user = "\n\n".join([
        _PREAMBLE.format(modality=bank.modality, size=size),
        f"The image belongs to exactly one of these {len(classes)} categories:\n{listing}",
        "Here is what an expert looks at in this modality, and what each level looks like:\n\n"
        + "\n\n".join(blocks),
        "Here is what the literature expects of each category on those features:\n"
        + "\n".join(fingerprints),
        f"Using that and the image, how likely is each category? Give every category a probability "
        f"between 0 and 1, and make the {len(classes)} probabilities sum to 1.",
        f"Reply with one JSON object and nothing else: exactly {len(classes)} keys, the category "
        "names above copied exactly as written, each value a number.",
        "{\n" + template + "\n}",
    ])
    return _message(_ZERO_SHOT_SYSTEM, user, list(classes))


def render(bank: Bank, classes: list[str], size: int, anchors: bool) -> dict:
    """Everything a score job needs about a dataset's prompts: both rendered prompts with their
    hashes, and the concept scales the response parser validates answers against."""
    rows = concept_rows(bank)
    return {
        "modality": bank.modality,
        "anchors": anchors,
        "concepts": rows,
        "classes": list(classes),
        "prompts": {
            "concept": render_concept_prompt(bank, rows, size=size, anchors=anchors),
            "zero_shot": render_zero_shot_prompt(bank, classes, size=size),
            "directed": render_directed_prompt(bank, classes, rows, size=size),
        },
    }
