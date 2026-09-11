"""The concept bank against the schema CONCEPT_BANK.md defines.

The bank is this project's prior knowledge and its only label-free predictor, so a careless
fingerprint costs a hypothesis rather than a decimal place (CONCEPT_BANK.md). Every rule stated
there as machine-checkable is checked here, over all twelve committed files, and the two structural
rules its prose requires - the organ files sharing one concept block, and retinamnist's monotone
grades - are checked as well.

What is NOT checked here is everything the prose leaves to a reader: that a concept describes what
is visible rather than the diagnosis, that adjacent anchors are separable, that a fingerprint is
the textbook's expectation and not a guess at the dataset's statistics. Those were the review
passes recorded in data/concepts/README.md, and no test can stand in for them.
"""
import re
from pathlib import Path

import pytest

from .conftest import BANK_DATASETS, INFO

# CONCEPT_BANK.md's `task` vocabulary, and the raw `medmnist` string each value must correspond to.
TASK_VOCABULARY = {
    "multi-class": "multi-class",
    "binary": "binary-class",
    "multi-label": "multi-label, binary-class",
    "ordinal": "ordinal-regression",
}


def label_names(dataset):
    """The dataset's class names, in label-index order, from the installed package."""
    label = INFO[dataset]["label"]
    return [label[k] for k in sorted(label, key=int)]


@pytest.mark.parametrize("dataset", BANK_DATASETS)
def test_dataset_and_class_names_match_the_medmnist_label_map(banks, dataset):
    bank = banks[dataset]
    assert bank.doc["dataset"] == dataset
    assert sorted(bank.classes) == sorted(label_names(dataset))


@pytest.mark.parametrize("dataset", BANK_DATASETS)
def test_task_vocabulary_agrees_with_the_raw_medmnist_task(banks, dataset):
    """`task` is CONCEPT_BANK.md's vocabulary, `medmnist_task` the package's string verbatim, and
    the two must agree - the mapping between them is recorded rather than inferred."""
    doc = banks[dataset].doc
    assert doc["medmnist_task"] == INFO[dataset]["task"]
    assert TASK_VOCABULARY[doc["task"]] == doc["medmnist_task"]


@pytest.mark.parametrize("dataset", BANK_DATASETS)
def test_every_concept_has_an_id_a_question_an_ordered_scale_and_a_source(banks, dataset):
    concepts = banks[dataset].concepts
    ids = [c["id"] for c in concepts]
    assert len(ids) == len(set(ids)), "concept ids repeat"
    for c in concepts:
        assert re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)*", c["id"]), c["id"]
        # A question, not a statement. Some carry a clarifying sentence after the question mark
        # (the organ files explain the radiological left-right convention), so ask for the mark
        # rather than for it to come last.
        assert "?" in c["question"], f"{c['id']}: the question asks nothing"
        assert 2 <= len(c["scale"]) <= 5, f"{c['id']}: {len(c['scale'])} levels"
        assert len(set(c["scale"])) == len(c["scale"]), f"{c['id']}: levels repeat"
        assert c.get("sources"), f"{c['id']}: no source key"


@pytest.mark.parametrize("dataset", BANK_DATASETS)
def test_concept_count_is_six_to_twelve(banks, dataset):
    """Fewer than six cannot separate the classes; more than twelve dilutes the prompt and the
    regression (CONCEPT_BANK.md). The cap is also what keeps the concept prompt readable."""
    assert 6 <= len(banks[dataset].concepts) <= 12


@pytest.mark.parametrize("dataset", BANK_DATASETS)
def test_every_level_carries_an_anchor_with_text_and_sources(banks, dataset):
    """Exactly one anchor per scale level, none missing and none named that is not in the scale.
    The concept prompt renders these, so a concept without them renders nothing (WORKFLOW.md 7)."""
    for c in banks[dataset].concepts:
        anchors = c.get("anchors")
        assert anchors, f"{c['id']}: no anchors block"
        assert sorted(anchors) == sorted(c["scale"]), f"{c['id']}: anchors do not match the scale"
        for level, anchor in anchors.items():
            assert anchor.get("text", "").strip(), f"{c['id']}/{level}: no anchor text"
            assert anchor.get("sources"), f"{c['id']}/{level}: no source key"


@pytest.mark.parametrize("dataset", BANK_DATASETS)
def test_anchor_texts_are_distinct_and_do_not_restate_their_own_level(banks, dataset):
    """An anchor says what the level looks like. Two anchors that share a text cannot be told
    apart, and one that only spells out its own token ("marked" for `marked`) is unsourced in any
    useful sense - it is exactly the missing threshold the anchors were added to supply."""
    for c in banks[dataset].concepts:
        texts = [" ".join(a["text"].split()).lower() for a in c["anchors"].values()]
        assert len(set(texts)) == len(texts), f"{c['id']}: two anchors share a text"
        for level, anchor in c["anchors"].items():
            words = re.sub(r"[^a-z0-9]+", " ", anchor["text"].lower()).split()
            assert words != level.lower().split("_"), f"{c['id']}/{level}: anchor restates the level"
            assert len(words) > len(level.split("_")), f"{c['id']}/{level}: anchor says nothing more"


@pytest.mark.parametrize("dataset", BANK_DATASETS)
def test_every_fingerprint_names_every_concept_with_a_level_or_any(banks, dataset):
    """`any` is the deliberate "the literature does not commit here"; anything else must be a level
    of that concept's own scale, since arm B compares a fingerprint level by level."""
    bank = banks[dataset]
    scales = {c["id"]: c["scale"] for c in bank.concepts}
    for name, cls in bank.classes.items():
        fingerprint = cls["fingerprint"]
        assert sorted(fingerprint) == sorted(scales), f"{name}: fingerprint does not name every concept"
        for cid, level in fingerprint.items():
            assert level == "any" or level in scales[cid], f"{name}/{cid}: {level!r} is not a level"


@pytest.mark.parametrize("dataset", BANK_DATASETS)
def test_every_source_key_resolves_to_a_citation_with_a_doi_or_url(banks, dataset):
    """Every key used by a concept, an anchor or a class exists in `provenance.sources` with a
    citation and a locator. The bank's claim is that it is cited, so a dangling key is a defect."""
    doc = banks[dataset].doc
    sources = {s["key"]: s for s in doc["provenance"]["sources"]}
    for key, source in sources.items():
        assert source.get("citation", "").strip(), f"{key}: no citation"
        assert source.get("doi") or source.get("url"), f"{key}: no DOI or URL"

    used = set()
    for c in banks[dataset].concepts:
        used.update(c["sources"])
        for anchor in c["anchors"].values():
            used.update(anchor["sources"])
    for cls in banks[dataset].classes.values():
        used.update(cls.get("sources", []))
    assert not (used - set(sources)), f"source keys used but not declared: {sorted(used - set(sources))}"


@pytest.mark.parametrize("dataset", BANK_DATASETS)
def test_review_is_recorded_and_says_it_was_simulated(banks, dataset):
    """No clinician has reviewed these files, and every file has to say so in the place a reader
    looks for the sign-off. If this project ever gets a real review, this test is what changes."""
    reviewed_by = banks[dataset].doc["provenance"]["reviewed_by"]
    assert "simulated" in reviewed_by.lower()


def test_the_three_organ_files_share_one_byte_identical_concepts_block(banks):
    """The same eleven organs in three planes: the concept set is one text, so a cross-plane
    comparison cannot be a comparison of two differently worded question sets."""
    blocks = []
    for dataset in ("organamnist", "organcmnist", "organsmnist"):
        text = Path(banks[dataset].file).read_text()
        blocks.append(text[text.index("\nconcepts:"):text.index("\nclasses:")])
    assert blocks[0] == blocks[1] == blocks[2]


def test_retinamnist_fingerprints_are_monotone_across_the_grades(banks):
    """Diabetic retinopathy is graded 0 to 4 by severity, so on every concept the committed levels
    must not go down as the grade goes up; the ordered scales are what carry the ordinal task."""
    bank = banks["retinamnist"]
    grades = sorted(bank.classes, key=int)
    assert grades == ["0", "1", "2", "3", "4"]
    for c in bank.concepts:
        committed = [c["scale"].index(bank.classes[g]["fingerprint"][c["id"]])
                     for g in grades if bank.classes[g]["fingerprint"][c["id"]] != "any"]
        assert committed == sorted(committed), f"{c['id']}: levels fall as the grade rises"
