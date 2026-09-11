"""The sampler: the drawn indices, and the streaming reader that fetches their rows.

The reader is the one piece of this workflow that cannot be checked by reading it. It inflates a
deflated zip member and walks it with forward seeks and a byte count per row, so an off-by-one in
the header parse or the gap arithmetic would return real images from the wrong indices - a silent
relabelling of the whole study rather than a crash. These tests build a small release-shaped npz,
where the row contents are known from the index, and check that what comes back is what was asked
for, including the awkward cases: the first row, the last row, adjacent rows, one row, all rows.
"""
import numpy as np
import pytest

from priors import sample

from .conftest import RUN_DATASETS


@pytest.fixture
def fake_release(tmp_path):
    """A release-shaped npz: `<split>_images.npy` and `<split>_labels.npy`, deflated as the real
    files are, with row i of the images filled with the value i so a row identifies itself."""
    n, side = 40, 5
    images = np.arange(n, dtype=np.uint8).repeat(side * side * 3).reshape(n, side, side, 3)
    labels = (np.arange(n) % 4).astype(np.uint8).reshape(n, 1)
    path = tmp_path / "fake_224.npz"
    np.savez_compressed(path, test_images=images, test_labels=labels,
                        train_images=images[::-1].copy(), train_labels=labels[::-1].copy())
    return path, images, labels


def test_indices_are_ascending_unique_and_in_range():
    idx = sample.sample_indices(1000, 50, seed=0)
    assert len(idx) == 50 and len(set(idx.tolist())) == 50
    assert list(idx) == sorted(idx) and idx.min() >= 0 and idx.max() < 1000


def test_the_same_seed_draws_the_same_sample_and_another_seed_does_not():
    assert list(sample.sample_indices(1000, 50, 0)) == list(sample.sample_indices(1000, 50, 0))
    assert list(sample.sample_indices(1000, 50, 1)) != list(sample.sample_indices(1000, 50, 0))


def test_a_sample_larger_than_the_split_is_refused():
    """Better a failed job than a sample drawn with replacement, which would put the same image in
    the test set twice and quietly weight it double in every AUC."""
    with pytest.raises(ValueError):
        sample.sample_indices(100, 101, seed=0)


@pytest.mark.parametrize("indices", [[0], [39], [0, 39], [7, 8, 9], list(range(40)), [3, 17, 31]])
def test_the_streaming_reader_returns_the_rows_it_was_asked_for(fake_release, indices):
    path, images, _ = fake_release
    rows = sample.read_rows(path, "test", indices)
    assert rows.shape == (len(indices), *images.shape[1:])
    assert rows.dtype == images.dtype
    assert np.array_equal(rows, images[indices])
    # Row i is filled with i, so a wrong row would be uniform in the wrong value rather than noise.
    assert [int(r.flat[0]) for r in rows] == list(indices)


def test_the_reader_keeps_the_splits_apart(fake_release):
    """`train` is the reversed array in the fixture, so a reader that fell back to the first member
    of the zip, or ignored its split argument, would be caught here."""
    path, images, _ = fake_release
    assert np.array_equal(sample.read_rows(path, "train", [0, 1]), images[::-1][[0, 1]])


def test_the_reader_refuses_indices_it_cannot_serve(fake_release):
    path, _, _ = fake_release
    with pytest.raises(ValueError):
        sample.read_rows(path, "test", [5, 3])          # not ascending: the pass is forward only
    with pytest.raises(ValueError):
        sample.read_rows(path, "test", [2, 2])          # repeated
    with pytest.raises(ValueError):
        sample.read_rows(path, "test", [40])            # beyond the split


def test_labels_are_read_whole(fake_release):
    path, _, labels = fake_release
    assert np.array_equal(sample.read_labels(path, "test").reshape(-1), labels.reshape(-1))


def test_draw_reports_the_sample_beside_the_split_it_came_from(fake_release):
    path, images, labels = fake_release
    drawn = sample.draw(path, "test", k=12, seed=0)
    assert drawn["n"] == 12 and drawn["split_n"] == len(images)
    assert np.array_equal(drawn["images"], images[drawn["indices"]])
    assert np.array_equal(drawn["labels"].reshape(-1), labels.reshape(-1)[drawn["indices"]])
    assert sum(drawn["class_counts"].values()) == 12
    assert sum(drawn["split_class_counts"].values()) == len(images)


def test_the_samples_fit_inside_the_official_splits(config, release):
    """A dataset with fewer test images than the sample, or fewer train images than the pool, would
    fail at the far end of a 12 GB read; the pinned split sizes say so in a millisecond."""
    for dataset in RUN_DATASETS:
        n = release.dataset(dataset)["n_samples"]
        assert n["test"] >= config["sample"]["test_n"], dataset
        assert n["train"] >= config["sample"]["pool_n"], dataset
