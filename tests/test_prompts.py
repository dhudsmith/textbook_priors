"""Both prompts, as properties of the rendered strings.

H2 asks whether directing the VLM at cited visual features beats asking it for the diagnosis, and
it is only a fair question if the two prompts stay apart: the concept prompt must name no class and
the zero-shot prompt must mention no concept (WORKFLOW.md sections 2 and 7). That is checked here
on the strings themselves rather than promised in the prose, because it is the kind of property a
later edit to a bank or a template breaks quietly.

The tests render from the bank and the release, not from results/prompts/, so they fail before a
job runs rather than after the archive has been written.
"""
import dataclasses
import re

import pytest

from priors import prompts

from .conftest import INFO, RUN_DATASETS


def render_as_the_rule_does(banks, release, config, dataset, anchors=True):
    """`prompts.render` with the arguments `render_prompts` gives it: the dataset's gloss, if config
    has one, and whether the task is multi-label."""
    gloss = (config["vlm"]["prompt"].get("class_gloss") or {}).get(dataset)
    return prompts.render(banks[dataset], release.class_names(dataset), size=config["size"],
                          anchors=anchors, gloss=gloss, multi_label=release.multi_label(dataset))


@pytest.fixture(scope="module")
def rendered(banks, release, config):
    """Every dataset's prompts, rendered as `render_prompts` renders them."""
    return {d: render_as_the_rule_does(banks, release, config, d) for d in RUN_DATASETS}


# The datasets with a zero-shot prompt, which is every single-label one: the multi-label task has
# arms C and P alone (WORKFLOW.md section 3) and `render` gives it `zero_shot: None`.
ZERO_SHOT_DATASETS = [d for d in RUN_DATASETS
                      if not INFO[d]["task"].startswith("multi-label")]

# The prompt hashes the response archive was bought under, one pair per dataset scored before the
# renderer learned about glosses and multi-label tasks (results/prompts/<dataset>.json in the
# owner's checkout, 2026-09-11). Pinned so that no later change to the renderer can quietly turn
# 27,000 archived answers into answers to a different question: the manifests carry these hashes
# and a rerun would compare against them.
ARCHIVE_HASHES = {
    "pathmnist": ("905c1b6f6c1991f6c4f2e8f245397cdc8b6a536f0fe43dca8553e13e2c711661",
                  "0c72cbd01bca24940afb825ae63892a65bd00507476b4ef3eb9b52a366830a41"),
    "dermamnist": ("a4a8088519e9d45cc25fec30e1cef9f797d77bd6bf1b18051256487afd8aaa6e",
                   "6bd31912d04a0a0e42b83744fdbee12ed91a3530dd588857fa90b5a1323c1096"),
    "octmnist": ("40d2f179319a81626ded17cef977601340991341dbc6bcf5faedad55db86dd3e",
                 "33f95fdc2bc77927cb2557c105c2f2ceda2fce50e0315463646d63b624117544"),
    "pneumoniamnist": ("5cabc4d848c7c30556a15c25e65b1889863ef1abc2700126ecc337427b62965e",
                       "d3285ebf39882934e707c19513fa72d2c8757c9690caa75c02da8328b8fec1ca"),
    "bloodmnist": ("4a3f77c8ad67e6bb5d838514c83bd0ffeeff3896b57fd2c17f9d476354e629af",
                   "b1cb28f9745d2dac6cc5d9f79e62e229f849fc5e03f46effabee3ffae4446b71"),
    "organamnist": ("9c33f158d4ae40dcf11b00af6653d4dcf07a21aad3c85a48cbe3f87ceda800cf",
                    "4e4c0e26b60ac15251411c5c98f6621fdeae817493af0551ea2522d88f46a74a"),
}


@pytest.mark.parametrize("dataset", sorted(ARCHIVE_HASHES))
def test_the_archived_datasets_still_render_the_prompts_that_bought_them(rendered, dataset):
    p = rendered[dataset]["prompts"]
    assert (p["concept"]["sha256"], p["zero_shot"]["sha256"]) == ARCHIVE_HASHES[dataset]


def names_a(text, phrase):
    """Does `text` use `phrase` as a whole word?

    Word boundaries, so an identifier that merely contains a class name does not count as naming
    it: pathmnist's concept `necrotic_debris` is the criterion for its class `debris`, bloodmnist's
    `cytoplasm_basophilia` is a staining property and not the cell `basophil`, and neither is ever
    offered to the model as a category. `_` is a word character, which is what makes that work."""
    return re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE) is not None


@pytest.mark.parametrize("dataset", ZERO_SHOT_DATASETS)
def test_the_concept_prompt_names_no_class(rendered, config, dataset):
    """H2's non-circularity, as a property of the rendered string. Two datasets need a word:

    * the multi-label task is not in this list at all, because it has no arm A or B for H2 to
      compare, and its class names ARE radiographic signs (effusion, mass, nodule) that a bank of
      visible features must name;
    * retinamnist's class names are the digits "0" to "4", which are not diagnoses and appear in the
      concept prompt as ordinary numbers ("the 4-2-1 rule"). What must not leak there is what the
      digits stand for, so the glossed names are checked in their place."""
    p = rendered[dataset]
    text = p["prompts"]["concept"]["system"] + "\n" + p["prompts"]["concept"]["user"]
    gloss = (config["vlm"]["prompt"].get("class_gloss") or {}).get(dataset, {})
    names = [gloss.get(c, c) for c in p["classes"] if not c.isdigit() or c in gloss]
    named = [c for c in names if names_a(text, c)]
    assert not named, f"the concept prompt names {named}"


def test_a_gloss_is_shown_beside_the_name_and_the_keys_stay_the_release_names(rendered, config):
    gloss = config["vlm"]["prompt"]["class_gloss"]["retinamnist"]
    p = rendered["retinamnist"]["prompts"]["zero_shot"]
    for name, words in gloss.items():
        assert f"{name} ({words})" in p["user"]
        assert f'"{name}": <probability>' in p["user"]
    assert p["keys"] == rendered["retinamnist"]["classes"]


def test_the_multi_label_task_has_no_zero_shot_prompt(rendered, release):
    multi = [d for d in RUN_DATASETS if release.multi_label(d)]
    assert multi == ["chestmnist"]
    p = rendered["chestmnist"]
    assert p["multi_label"] is True and p["prompts"]["zero_shot"] is None
    assert p["prompts"]["concept"]["keys"], "the concept prompt is still rendered"


@pytest.mark.parametrize("dataset", ZERO_SHOT_DATASETS)
def test_the_zero_shot_prompt_mentions_no_concept(rendered, dataset):
    p = rendered[dataset]
    text = p["prompts"]["zero_shot"]["system"] + "\n" + p["prompts"]["zero_shot"]["user"]
    # Concept ids, questions and anchor texts, but not the bare level tokens: levels are ordinary
    # words - dermamnist's `colour_count` runs `one`, `two`, ... - and "exactly one of these 7
    # categories" is not a mention of a concept.
    mentioned = [c["id"] for c in p["concepts"]
                 if names_a(text, c["id"]) or c["question"] in text
                 or any(anchor in text for anchor in c["anchors"].values())]
    assert not mentioned, f"the zero-shot prompt mentions {mentioned}"


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_the_concept_prompt_asks_every_question_at_every_level_with_its_anchor(rendered, dataset):
    p = rendered[dataset]
    user = p["prompts"]["concept"]["user"]
    for c in p["concepts"]:
        assert c["question"] in user, c["id"]
        assert sorted(c["anchors"]) == sorted(c["scale"]), c["id"]
        for level in c["scale"]:
            assert level in user and c["anchors"][level] in user, f"{c['id']}/{level}"
        # The reply template spells out the alternatives, so the model is told the exact tokens.
        assert f'"{c["id"]}": "{"|".join(c["scale"])}"' in user, c["id"]


@pytest.mark.parametrize("dataset", ZERO_SHOT_DATASETS)
def test_the_zero_shot_prompt_lists_the_classes_in_label_index_order(rendered, release, dataset):
    p = rendered[dataset]
    user = p["prompts"]["zero_shot"]["user"]
    assert p["classes"] == release.class_names(dataset)
    positions = [user.index(f"{i}. {name}") for i, name in enumerate(p["classes"], start=1)]
    assert positions == sorted(positions)
    for name in p["classes"]:
        assert f'"{name}": <probability>' in user


@pytest.mark.parametrize("dataset", ZERO_SHOT_DATASETS)
def test_the_two_prompts_are_two_different_strings(rendered, dataset):
    """Each prompt is hashed into the archive it produced, so two arms sharing a hash would make
    their two archives indistinguishable after the fact."""
    p = rendered[dataset]["prompts"]
    hashes = {k: p[k]["sha256"] for k in ("concept", "zero_shot")}
    assert len(set(hashes.values())) == 2, hashes
    assert p["concept"]["user"] != p["zero_shot"]["user"]


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_the_keys_a_reply_must_carry(rendered, banks, release, dataset):
    """What the score stage validates a response against: the concept ids in bank order, and the
    class names in label-index order."""
    p = rendered[dataset]
    assert p["prompts"]["concept"]["keys"] == [c["id"] for c in banks[dataset].concepts]
    if p["prompts"]["zero_shot"] is not None:
        assert p["prompts"]["zero_shot"]["keys"] == release.class_names(dataset)


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_rendering_is_deterministic(banks, release, rendered, config, dataset):
    assert render_as_the_rule_does(banks, release, config, dataset) == rendered[dataset]


def test_the_prompt_hash_covers_both_messages():
    """The hash recorded in every score manifest changes when the system message changes, not only
    when the questions do, so an archive cannot be attributed to a prompt that did not produce it."""
    a = prompts.prompt_sha256("system", "user")
    assert a == prompts.prompt_sha256("system", "user")
    assert a != prompts.prompt_sha256("system.", "user")
    assert a != prompts.prompt_sha256("system", "user.")


def test_every_rendered_prompt_has_its_own_hash(rendered):
    hashes = [rendered[d]["prompts"][k]["sha256"]
              for d in RUN_DATASETS for k in ("concept", "zero_shot")
              if rendered[d]["prompts"][k] is not None]
    assert len(set(hashes)) == len(hashes)


def test_the_bare_levels_switch_drops_the_anchor_text(banks, release, config):
    """`vlm.prompt.anchors: false` is the `bare_levels` extension (WORKFLOW.md section 10): the
    same questions with the level names alone, which is what the bank looked like before it was
    anchored. It scores into a second archive, so the two prompts must differ."""
    bank, classes = banks["pneumoniamnist"], release.class_names("pneumoniamnist")
    size = config["size"]
    bare = prompts.render(bank, classes, size=size, anchors=False)["prompts"]["concept"]
    full = prompts.render(bank, classes, size=size, anchors=True)["prompts"]["concept"]
    assert bare["sha256"] != full["sha256"]
    assert bare["keys"] == full["keys"]
    for c in prompts.concept_rows(bank):
        assert c["question"] in bare["user"]
        assert ", ".join(c["scale"]) in bare["user"]
        for text in c["anchors"].values():
            assert text not in bare["user"]


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_the_txt_render_carries_every_prompt_string_once(rendered, dataset):
    """`render_txt` is a second view of the same dict, not a second rendering of the prompt logic
    (WORKFLOW.md section 7): every user string - the part that differs between the two prompts -
    must appear in it verbatim and exactly once, since arm B and arm C read the same concept
    prompt and it should not be printed twice under two different arm labels."""
    p = rendered[dataset]
    text = prompts.render_txt(dataset, p)
    assert text.startswith(dataset)
    for key, arms in (("concept", "B, C"), ("zero_shot", "A")):
        msg = p["prompts"][key]
        if msg is None:
            assert f"arm {arms}: no {key} prompt" in text
            continue
        assert f"arm {arms}: {key} prompt" in text
        assert msg["sha256"] in text
        assert msg["system"] in text
        assert text.count(msg["user"]) == 1


def test_a_level_without_an_anchor_is_refused(banks, release, config):
    """CONCEPT_BANK.md requires one anchor per level and the bank tests hold the files to it; this
    is the renderer refusing to ask about a level it cannot describe, so the failure lands on the
    prompt rather than on a model asked an undescribed question."""
    bank = banks["pneumoniamnist"]
    doc = {**bank.doc, "concepts": [dict(c) for c in bank.concepts]}
    doc["concepts"][0] = {**doc["concepts"][0], "anchors": {}}
    with pytest.raises(ValueError, match="anchor text"):
        prompts.render(dataclasses.replace(bank, doc=doc),
                       release.class_names("pneumoniamnist"), size=config["size"], anchors=True)
