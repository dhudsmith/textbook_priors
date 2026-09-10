"""The concept bank against every rule CONCEPT_BANK.md fixes, plus the two structural checks its
README requires, plus the release pin against the installed medmnist package."""
import re

import pytest

from priors import data as D
from tests.conftest import DATASETS


@pytest.mark.parametrize("ds", DATASETS)
def test_bank_file_obeys_the_schema(cfg, release, ds):
    problems = D.validate_bank(D.load_bank(cfg, ds), ds, release["datasets"][ds])
    assert not problems, f"{ds}:\n  " + "\n  ".join(problems)


@pytest.mark.parametrize("ds", DATASETS)
def test_classes_are_the_label_map_in_order(cfg, release, ds):
    names = D.class_names(cfg, ds)
    assert names == [release["datasets"][ds]["label"][str(i)] for i in range(len(names))]
    assert set(D.load_bank(cfg, ds)["classes"]) == set(names)


def _concepts_block(text):
    m = re.search(r"^concepts:\n(.*?)^classes:", text, re.S | re.M)
    assert m, "no concepts block"
    return m.group(1)


def test_organ_files_share_one_concepts_block(cfg):
    files = [D.bank_path(cfg, ds).read_text() for ds in ("organamnist", "organcmnist", "organsmnist")]
    blocks = [_concepts_block(t) for t in files]
    assert blocks[0] == blocks[1] == blocks[2], "the three organ*mnist concepts blocks must be byte-identical"
    parsed = [D.load_bank(cfg, ds)["concepts"] for ds in ("organamnist", "organcmnist", "organsmnist")]
    assert parsed[0] == parsed[1] == parsed[2]


def test_retinamnist_fingerprints_are_monotone_across_grades(cfg):
    assert D.retina_monotone(D.load_bank(cfg, "retinamnist")) == []


def test_release_pin_matches_the_installed_medmnist(release):
    medmnist = pytest.importorskip("medmnist")
    from medmnist.info import INFO, __version__
    assert __version__ == release["medmnist_version"]
    for ds, d in release["datasets"].items():
        info = INFO[ds]
        assert d["task"] == info["task"]
        assert d["n_channels"] == info["n_channels"]
        assert d["n_samples"] == info["n_samples"]
        assert d["label"] == {str(k): v for k, v in info["label"].items()}
        assert d["files"][28]["md5"] == info["MD5"] and info["url"].endswith(d["files"][28]["name"] + "?download=1")
        assert d["files"][224]["md5"] == info["MD5_224"] and info["url_224"].endswith(d["files"][224]["name"] + "?download=1")
        assert info["url"].startswith(release["record"])


def test_fingerprint_matrix_masks_any_and_maps_evenly(cfg):
    bank = D.load_bank(cfg, "breastmnist")
    names = D.class_names(cfg, "breastmnist")
    F = D.fingerprint_matrix(bank, names)
    assert F.shape == (2, len(bank["concepts"]))
    for k, name in enumerate(names):
        for j, c in enumerate(bank["concepts"]):
            lv = bank["classes"][name]["fingerprint"][c["id"]]
            if lv == "any":
                assert F[k, j] != F[k, j]            # NaN
            else:
                assert abs(F[k, j] - c["scale"].index(lv) / (len(c["scale"]) - 1)) < 1e-12
    assert list(D.scale_values(["a", "b", "c", "d", "e"])) == [0.0, 0.25, 0.5, 0.75, 1.0]


def test_answers_matrix_marks_missing_and_off_scale(cfg):
    bank = D.load_bank(cfg, "breastmnist")
    c0 = bank["concepts"][0]
    good = {c["id"]: c["scale"][-1] for c in bank["concepts"]}
    bad = dict(good, **{c0["id"]: "not-a-level"})
    X = D.answers_matrix(bank, [good, bad, None])
    assert X[0].tolist() == [1.0] * len(bank["concepts"])
    assert X[1, 0] != X[1, 0] and X[1, 1] == 1.0
    assert all(v != v for v in X[2])


def test_bank_hash_is_the_file_hash(cfg):
    import hashlib
    p = D.bank_path(cfg, "octmnist")
    assert D.file_hash(p) == hashlib.sha256(p.read_bytes()).hexdigest()
