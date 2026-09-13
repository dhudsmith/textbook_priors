"""H5's rendering and arithmetic, without a network.

What is checked here is everything about arms Z, T and E that does not need the embedding model:
that an image's answers and a class's fingerprint render through one renderer and so compare like
with like; that T reads exactly the subset of the bank arm B reads - `any` renders nothing for a
class, a missing answer nothing for an image; that the template is applied and nothing else is
invented; and that the cosine and the permutation control behave. The embedder itself is checked by
running one dataset first and reading its texts and its similarity matrix by hand, before the other
five (WORKFLOW.md section 9).
"""
import numpy as np
import pytest

from priors import classify as arms
from priors import embed

from .conftest import ROOT

TEMPLATE = "{modality}. {text}"


@pytest.fixture(scope="module")
def bank():
    from priors import data
    return data.load_bank("pneumoniamnist", str(ROOT / "data/concepts"))


@pytest.fixture(scope="module")
def classes():
    from priors import data
    return data.load_release(str(ROOT / "config/medmnist.yaml")).class_names("pneumoniamnist")


def test_a_fingerprint_renders_its_committed_anchors_in_bank_order_and_skips_any(bank, classes):
    order, anchors = embed.anchors_of(bank)
    for name in classes:
        fingerprint = bank.classes[name]["fingerprint"]
        text = embed.fingerprint_text(bank, name, TEMPLATE)
        assert text.startswith(bank.modality + ". ")
        committed = [cid for cid in order if fingerprint.get(cid) not in (None, "any")]
        for cid in committed:
            assert anchors[cid][fingerprint[cid]]["text"].rstrip(". ") in text, f"{name}/{cid}"
        for cid in order:
            if fingerprint.get(cid) == "any":
                for level, spec in anchors[cid].items():
                    assert spec["text"].rstrip(". ") not in text, f"{name}/{cid}: an `any` leaked"
        # order: the committed anchors appear in the bank's concept order
        positions = [text.index(anchors[cid][fingerprint[cid]]["text"].rstrip(". ")) for cid in committed]
        assert positions == sorted(positions), name


def test_an_image_renders_through_the_same_renderer_as_a_fingerprint(bank):
    """T compares like with like: the same anchors, the same order, the same template."""
    order, anchors = embed.anchors_of(bank)
    row = {"answers": {cid: list(anchors[cid])[0] for cid in order}}
    as_image = embed.answer_text(bank, row, TEMPLATE)
    as_class = embed.describe(bank, row["answers"], TEMPLATE)
    assert as_image == as_class


def test_a_missing_answer_renders_nothing_and_an_empty_image_renders_the_modality_alone(bank):
    order, anchors = embed.anchors_of(bank)
    full = {cid: list(anchors[cid])[0] for cid in order}
    partial = dict(full); partial[order[0]] = None
    assert anchors[order[0]][full[order[0]]]["text"].rstrip(". ") not in embed.answer_text(bank, {"answers": partial}, TEMPLATE)
    assert embed.answer_text(bank, {"answers": {}}, TEMPLATE) == bank.modality + ". "
    assert embed.committed_count(bank, partial) == len(order) - 1


def test_a_level_off_the_scale_is_refused_rather_than_rendered(bank):
    order, _ = embed.anchors_of(bank)
    with pytest.raises(ValueError):
        embed.describe(bank, {order[0]: "not_a_level"}, TEMPLATE)


def test_arm_z_target_is_the_humanised_name_under_the_modality(bank, classes):
    for name in classes:
        text = embed.name_text(bank, name, TEMPLATE)
        assert text == f"{bank.modality}. {embed.humanise(name)}."
    assert embed.humanise("lung-left_lobe") == "lung left lobe"


def test_the_two_pneumoniamnist_fingerprints_render_differently(bank, classes):
    """If they did not, T could not separate the classes and would be uninformative by construction."""
    a, b = (embed.fingerprint_text(bank, c, TEMPLATE) for c in classes)
    assert a != b


def test_every_run_dataset_renders_every_class_and_no_fingerprint_is_empty(config, release):
    from priors import data
    template = config["embed"]["template"]
    for ds in config["datasets"]:
        bank = data.load_bank(ds, str(ROOT / config["conceptdir"]))
        for name in release.class_names(ds):
            fp = embed.fingerprint_text(bank, name, template)
            assert embed.committed_count(bank, bank.classes[name]["fingerprint"]) > 0, f"{ds}/{name}"
            assert fp.startswith(bank.modality + ". ") and fp.endswith("."), f"{ds}/{name}"
            assert embed.name_text(bank, name, template).startswith(bank.modality + ". ")


def test_cosine_scores_rank_an_image_by_its_own_direction():
    classes = np.eye(3, dtype=np.float32)
    images = np.array([[3.0, 0.1, 0.0], [0.0, 0.2, 5.0]], dtype=np.float32)
    scores = embed.cosine_scores(images, classes)
    assert scores.shape == (2, 3)
    assert scores.argmax(axis=1).tolist() == [0, 2]
    assert np.all(scores <= 1.0 + 1e-6)


def test_the_similarity_matrix_is_symmetric_with_a_unit_diagonal():
    rng = np.random.default_rng(0)
    m = embed.similarity_matrix(rng.normal(size=(5, 16)))
    assert m.shape == (5, 5)
    assert np.allclose(m, m.T)
    assert np.allclose(np.diag(m), 1.0, atol=1e-5)


def test_the_permutation_control_moves_every_class_vector_off_its_own_class():
    """T's control reuses B's: rows permuted across classes."""
    matrix = np.eye(5, dtype=np.float32)
    permuted = arms.permute_fingerprints(matrix, seed=0)
    assert permuted.shape == matrix.shape
    assert not np.array_equal(permuted, matrix)
    assert np.allclose(sorted(permuted.sum(axis=1)), [1] * 5)


def test_normalise_leaves_a_zero_row_zero_rather_than_nan():
    out = embed.normalise(np.array([[0.0, 0.0], [3.0, 4.0]]))
    assert np.array_equal(out[0], [0.0, 0.0])
    assert np.allclose(out[1], [0.6, 0.8])


def test_the_text_hash_is_order_sensitive_and_separator_safe():
    assert embed.sha256(["a", "b"]) != embed.sha256(["b", "a"])
    assert embed.sha256(["ab", ""]) != embed.sha256(["a", "b"])
