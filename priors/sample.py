"""sample: the two seeded samples every arm is measured on, taken out of a release file.

Each dataset contributes one 500-image test sample - shared by every arm and every model, so that
every comparison in the study is paired - and one 2000-image labelled pool, the largest point of
the learning curve (WORKFLOW.md section 4). Both are drawn from the official splits with one seed
from config, and the drawn indices are written into the result, so the sample is defined by a file
rather than by rerunning this code.

The 224-pixel releases are 0.2 to 12.6 GB each and their members are deflated, so there is no
random access: `np.load` would materialise a 13.5 GB array to keep 2000 images of it. This module
inflates the image member as a stream and copies out only the wanted rows, holding one row at a
time. Cost is one sequential pass; peak memory is the size of the sample, not of the split.
"""
from __future__ import annotations

import zipfile
from io import BytesIO

import numpy as np


def sample_indices(n: int, k: int, seed: int) -> np.ndarray:
    """`k` of `n` row indices without replacement, ascending.

    Ascending because the reader makes one forward pass, and because the order of the sample must
    not silently become part of the analysis: the nested subsets of the curve are drawn by the
    classify stage from its own seeds (WORKFLOW.md section 3), so this order carries no meaning
    beyond the source file's own.
    """
    if k > n:
        raise ValueError(f"asked for {k} of {n} rows")
    rng = np.random.default_rng(seed)
    return np.sort(rng.choice(n, size=k, replace=False))


def read_labels(path, split: str) -> np.ndarray:
    """A whole label member: a few hundred kilobytes at most, so it is read outright."""
    with zipfile.ZipFile(path) as z:
        return np.load(BytesIO(z.read(f"{split}_labels.npy")))


def read_rows(path, split: str, indices) -> np.ndarray:
    """The requested rows of `<split>_images.npy`, inflated as a stream.

    The member is a .npy file inside a zip: magic, header, then C-ordered rows of equal size. Only
    forward seeks are used, which a deflated zip member serves by inflating and discarding, so the
    pass never rewinds and never holds more than one row.
    """
    indices = np.asarray(indices)
    if indices.size and (np.any(np.diff(indices) <= 0) or indices[0] < 0):
        raise ValueError("indices must be ascending and unique")

    with zipfile.ZipFile(path) as z, z.open(f"{split}_images.npy") as f:
        version = np.lib.format.read_magic(f)
        if version == (1, 0):
            shape, fortran_order, dtype = np.lib.format.read_array_header_1_0(f)
        elif version == (2, 0):
            shape, fortran_order, dtype = np.lib.format.read_array_header_2_0(f)
        else:
            raise ValueError(f"{path}/{split}_images.npy: unsupported .npy version {version}")
        if fortran_order:
            raise ValueError(f"{path}/{split}_images.npy is Fortran-ordered; rows are not contiguous")
        if indices.size and indices[-1] >= shape[0]:
            raise ValueError(f"index {indices[-1]} beyond the {shape[0]} rows of {split}")

        row_shape = shape[1:]
        row_bytes = int(np.prod(row_shape)) * dtype.itemsize
        out = np.empty((len(indices), *row_shape), dtype=dtype)

        at = 0                                          # the next row the stream will hand back
        for position, index in enumerate(indices):
            if index > at:
                f.seek(row_bytes * (index - at), 1)     # inflate and discard the gap
                at = index
            raw = f.read(row_bytes)
            if len(raw) != row_bytes:
                raise EOFError(f"{split} row {index}: {len(raw)} of {row_bytes} bytes")
            out[position] = np.frombuffer(raw, dtype=dtype).reshape(row_shape)
            at = index + 1
    return out


def class_counts(labels) -> dict:
    """Per-class counts, keyed by the label index as a string so the JSON keeps its order."""
    values, counts = np.unique(np.asarray(labels).reshape(-1), return_counts=True)
    return {str(int(v)): int(c) for v, c in zip(values, counts)}


def draw(path, split: str, k: int, seed: int) -> dict:
    """One sample: the indices, their images and labels, and the counts a reader should check.

    `split_class_counts` is the whole split's balance, kept beside the sample's own so that the
    report can show what the seed drew against what it drew from, rather than asserting that 500
    images are representative.
    """
    labels = read_labels(path, split).reshape(-1)
    indices = sample_indices(len(labels), k, seed)
    return {
        "indices": indices,
        "labels": labels[indices],
        "images": read_rows(path, split, indices),
        "n": int(len(indices)),
        "split_n": int(len(labels)),
        "class_counts": class_counts(labels[indices]),
        "split_class_counts": class_counts(labels),
    }
