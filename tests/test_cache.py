"""The streamed npz -> npy conversion on a tiny fixture, and the seeded sample."""
import json
import zipfile

import numpy as np
import pytest

from priors import cache as C
from priors import data as D


def _npz(path, n=(7, 3, 5), shape=(8, 8, 3), labels=1):
    rng = np.random.default_rng(0)
    arrays = {}
    for split, k in zip(D.SPLITS, n):
        arrays[f"{split}_images"] = rng.integers(0, 256, (k,) + shape, dtype=np.uint8)
        arrays[f"{split}_labels"] = rng.integers(0, 2, (k, labels), dtype=np.uint8)
    np.savez_compressed(path, **arrays)
    return arrays


def test_build_streams_every_member_exactly(tmp_path):
    raw = tmp_path / "toy.npz"
    arrays = _npz(raw)
    out = tmp_path / "cache"
    meta = C.build(raw, out, {"train": 7, "val": 3, "test": 5}, 8, 3)
    assert meta["source_md5"] == C.md5sum(raw)
    for name, arr in arrays.items():
        got = np.load(out / f"{name}.npy", mmap_mode="r")
        assert got.dtype == arr.dtype and np.array_equal(got, arr)
    assert meta["splits"]["train"]["images"]["shape"] == [7, 8, 8, 3] or tuple(meta["splits"]["train"]["images"]["shape"]) == (7, 8, 8, 3)


def test_build_streams_in_small_chunks(tmp_path):
    raw = tmp_path / "toy.npz"
    arrays = _npz(raw, n=(700, 3, 5), shape=(4, 4))
    with zipfile.ZipFile(raw) as zf:
        C.stream_member(zf, "train_images.npy", tmp_path / "t.npy", rows_per_chunk=64)
    assert np.array_equal(np.load(tmp_path / "t.npy"), arrays["train_images"])


def test_build_rejects_wrong_counts_and_geometry(tmp_path):
    raw = tmp_path / "toy.npz"
    _npz(raw)
    with pytest.raises(ValueError):
        C.build(raw, tmp_path / "c1", {"train": 8, "val": 3, "test": 5}, 8, 3)
    with pytest.raises(ValueError):
        C.build(raw, tmp_path / "c2", {"train": 7, "val": 3, "test": 5}, 28, 3)


def test_draw_sample_is_seeded_capped_and_test_first():
    s = {"test_n": 500, "pool_n": 2000, "seed": 0}
    t, p = D.draw_sample(156, 546, s)
    assert len(t) == 156 and len(p) == 546 and len(set(t)) == 156 and (np.diff(t) > 0).all()
    t2, p2 = D.draw_sample(7180, 89996, s)
    assert len(t2) == 500 and len(p2) == 2000 and t2.max() < 7180 and p2.max() < 89996
    assert np.array_equal(t2, D.draw_sample(7180, 89996, s)[0])
    assert np.array_equal(t2, D.draw_sample(7180, 89996, dict(s, pool_n=100))[0])      # pool_n cannot move the test sample
    assert not np.array_equal(t2, D.draw_sample(7180, 89996, dict(s, seed=1))[0])


def test_sample_sizes_cap_at_the_official_split(cfg):
    assert D.sample_sizes(cfg, "breastmnist") == {"test": 156, "pool": 546}
    assert D.sample_sizes(cfg, "retinamnist") == {"test": 400, "pool": 1080}
    assert D.sample_sizes(cfg, "pathmnist") == {"test": 500, "pool": 2000}


def test_write_sample_roundtrip(tmp_path, cfg):
    raw = tmp_path / "toy.npz"
    arrays = _npz(raw, n=(40, 5, 30), shape=(6, 6))
    out = tmp_path / "cache"
    C.build(raw, out, {"train": 40, "val": 5, "test": 30}, 6, 1)
    cfg2 = dict(cfg, sample={"test_n": 10, "pool_n": 20, "seed": 0})
    meta = C.write_sample(out, "pneumoniamnist", cfg2, tmp_path / "s.npz")
    with np.load(tmp_path / "s.npz") as z:
        assert z["test_images"].shape == (10, 6, 6) and z["pool_images"].shape == (20, 6, 6)
        assert np.array_equal(z["test_images"], arrays["test_images"][z["test_idx"]])
        assert np.array_equal(z["pool_labels"], arrays["train_labels"][z["pool_idx"]])
    assert meta["test_n"] == 10 and meta["pool_n"] == 20 and len(meta["test_class_counts"]) == 2


def test_labels_1d():
    assert D.labels_1d(np.array([[1], [0]]), "multi-class").tolist() == [1, 0]
    assert D.labels_1d(np.array([[1, 0], [0, 1]]), "multi-label, binary-class").shape == (2, 2)
