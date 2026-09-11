"""The two prompts, as properties of the rendered strings.

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

from .conftest import RUN_DATASETS


@pytest.fixture(scope="module")
def rendered(banks, release, config):
    """Every dataset's prompts, rendered as `render_prompts` renders them."""
    return {d: prompts.render(banks[d], release.class_names(d), size=config["size"], anchors=True)
            for d in RUN_DATASETS}


def names_a(text, phrase):
    """Does `text` use `phrase` as a whole word?

    Word boundaries, so an identifier that merely contains a class name does not count as naming
    it: pathmnist's concept `necrotic_debris` is the criterion for its class `debris`, bloodmnist's
    `cytoplasm_basophilia` is a staining property and not the cell `basophil`, and neither is ever
    offered to the model as a category. `_` is a word character, which is what makes that work."""
    return re.search(rf"\b{re.escape(phrase)}\b", text, re.IGNORECASE) is not None


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_the_concept_prompt_names_no_class(rendered, dataset):
    p = rendered[dataset]
    text = p["prompts"]["concept"]["system"] + "\n" + p["prompts"]["concept"]["user"]
    named = [c for c in p["classes"] if names_a(text, c)]
    assert not named, f"the concept prompt names {named}"


@pytest.mark.parametrize("dataset", RUN_DATASETS)
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


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_the_zero_shot_prompt_lists_the_classes_in_label_index_order(rendered, release, dataset):
    p = rendered[dataset]
    user = p["prompts"]["zero_shot"]["user"]
    assert p["classes"] == release.class_names(dataset)
    positions = [user.index(f"{i}. {name}") for i, name in enumerate(p["classes"], start=1)]
    assert positions == sorted(positions)
    for name in p["classes"]:
        assert f'"{name}": <probability>' in user


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_the_keys_a_reply_must_carry(rendered, banks, release, dataset):
    """What the score stage validates a response against: the concept ids in bank order, and the
    class names in label-index order."""
    p = rendered[dataset]
    assert p["prompts"]["concept"]["keys"] == [c["id"] for c in banks[dataset].concepts]
    assert p["prompts"]["zero_shot"]["keys"] == release.class_names(dataset)


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_rendering_is_deterministic(banks, release, rendered, config, dataset):
    again = prompts.render(banks[dataset], release.class_names(dataset),
                           size=config["size"], anchors=True)
    assert again == rendered[dataset]


def test_the_prompt_hash_covers_both_messages():
    """The hash recorded in every score manifest changes when the system message changes, not only
    when the questions do, so an archive cannot be attributed to a prompt that did not produce it."""
    a = prompts.prompt_sha256("system", "user")
    assert a == prompts.prompt_sha256("system", "user")
    assert a != prompts.prompt_sha256("system.", "user")
    assert a != prompts.prompt_sha256("system", "user.")


def test_every_rendered_prompt_has_its_own_hash(rendered):
    hashes = [rendered[d]["prompts"][k]["sha256"] for d in RUN_DATASETS for k in ("concept", "zero_shot")]
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
