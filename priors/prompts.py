"""prompts: the two prompt strings, rendered from the concept bank and the label map.

Both prompts are pure functions of a dataset's bank, its release label map, the image size and the
`vlm.prompt.anchors` switch: no image, no model and no randomness enters here. Rendering is its own
rule (WORKFLOW.md section 7) so that the string sent to the model, the string hashed into every
score manifest, and the string the report or the live demo prints are one artifact rather than
three copies of a format that can drift apart.

Two prompts, kept separable on purpose, because H2 turns on it:

  * the CONCEPT prompt (arms B and C) asks for one level per concept, renders every level's cited
    anchor text, and never names a class;
  * the ZERO-SHOT prompt (arm A) asks for a distribution over the class names and never mentions
    a concept.

A third, DIRECTED prompt existed here between 2026-09-12 and 2026-09-12 and carried the whole bank
into a zero-shot question (arm D). It was removed with the arm: designed after the numbers were in,
it could decide nothing, and every reader of the report had to be told so twice. CHANGELOG.md keeps
what it measured.

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


def render_zero_shot_prompt(bank: Bank, classes: list[str], size: int, gloss: dict | None = None) -> dict:
    """The zero-shot prompt: the class names in label-index order and a distribution over them.
    Mentions no concept, so arm A is the undirected baseline H2 needs.

    `gloss` maps a class name to the words it stands for, for a release whose names are not
    clinical terms: retinamnist's are the digit strings "0" to "4", and a model asked to choose among
    digits is not being asked a diagnosis question, which would hand H2 a free vote. The gloss is
    shown in the listing only; the JSON keys the model answers with stay the release names, so the
    parser, the archive and every arm are unchanged. No gloss, no change to the string: the six
    datasets scored before it existed render byte for byte as they did (their hashes are in the
    archive), which the smoke tier checks."""
    gloss = gloss or {}
    listing = "\n".join(f"  {i}. {name}" + (f" ({gloss[name]})" if name in gloss else "")
                        for i, name in enumerate(classes, start=1))
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


def render(bank: Bank, classes: list[str], size: int, anchors: bool,
           gloss: dict | None = None, multi_label: bool = False) -> dict:
    """Everything a score job needs about a dataset's prompts: both rendered prompts with their
    hashes, and the concept scales the response parser validates answers against.

    A multi-label task gets no zero-shot prompt at all: "exactly one of these categories" is false
    of an image that carries several findings or none, and arm A is not defined for it (WORKFLOW.md
    section 3). `None` rather than a prompt nobody should send."""
    rows = concept_rows(bank)
    return {
        "modality": bank.modality,
        "anchors": anchors,
        "multi_label": multi_label,
        "concepts": rows,
        "classes": list(classes),
        "prompts": {
            "concept": render_concept_prompt(bank, rows, size=size, anchors=anchors),
            "zero_shot": (None if multi_label
                          else render_zero_shot_prompt(bank, classes, size=size, gloss=gloss)),
        },
    }


# Which arms read each rendered prompt, for the human-readable render below: concept is one
# prompt shared by two arms - C only differs from B in what happens to the scores after the call
# - so it is one block, not two, and says so.
_ARMS = {"concept": "B, C", "zero_shot": "A"}


def render_txt(dataset: str, rendered: dict) -> str:
    """`rendered` (what `render_prompts` wrote) as plain text, one block per prompt, for a human
    reader rather than a score job.

    Reads straight from the same dict every score manifest hashes and every score call sends, so
    this is a second view of one artifact and not a third rendering of the prompt logic
    (WORKFLOW.md section 7). Decides no hypothesis: a convenience, not a result."""
    blocks = [f"{dataset}", "=" * len(dataset), ""]
    for key in ("zero_shot", "concept"):
        msg = rendered["prompts"][key]
        if msg is None:                     # a multi-label task has no zero-shot prompt
            blocks += [f"--- arm {_ARMS[key]}: no {key} prompt (multi-label task) ---", ""]
            continue
        blocks += [
            f"--- arm {_ARMS[key]}: {key} prompt (sha256 {msg['sha256']}) ---",
            "",
            "[system]",
            msg["system"],
            "",
            "[user]",
            msg["user"],
            "",
        ]
    return "\n".join(blocks)
