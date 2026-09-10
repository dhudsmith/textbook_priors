"""cache: the MedMNIST npz files as memory-mappable uint8 arrays, one .npy per split.

The npz members are DEFLATE-compressed, so `np.load(f)["train_images"]` decompresses the whole
split into RAM: 13.5 GB for pathmnist at 224. Every downstream reader would pay that, and a
training job would pay it on a GPU node. This stage pays it once, and streams: the zip member is
read in row chunks and written straight to a .npy file, so the job's memory does not scale with
the dataset. A second rule draws the seeded test sample and labelled pool (WORKFLOW.md section 4).
"""
from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

import numpy as np
from numpy.lib import format as npf

from . import data as D

ROWS_PER_CHUNK = 256      # 256 x 150 KB rows at 224 RGB = 38 MB per read


def md5sum(path, block=1 << 24) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        while chunk := f.read(block):
            h.update(chunk)
    return h.hexdigest()


def _read_header(f):
    version = npf.read_magic(f)
    if version == (1, 0):
        return npf.read_array_header_1_0(f)
    return npf.read_array_header_2_0(f)


def stream_member(zf: zipfile.ZipFile, member: str, dest: Path, rows_per_chunk=ROWS_PER_CHUNK):
    """Copy one .npy member of an npz into a fresh .npy at `dest`, chunk by chunk, with plain
    sequential writes: the bytes of a C-ordered .npy are the header followed by the array, so no
    array is ever materialised, and the kernel throttles the writer rather than piling dirty
    memmap pages against the job's memory limit."""
    with zf.open(member) as f:
        shape, fortran, dtype = _read_header(f)
        if fortran:
            raise ValueError(f"{member}: Fortran order is not expected in MedMNIST files")
        dest.parent.mkdir(parents=True, exist_ok=True)
        n = int(shape[0]) if shape else 1
        row = int(np.prod(shape[1:], dtype=np.int64)) * dtype.itemsize if shape else dtype.itemsize
        tmp = dest.with_suffix(dest.suffix + ".tmp")
        with open(tmp, "wb") as out:
            npf.write_array_header_2_0(out, {"descr": npf.dtype_to_descr(dtype), "fortran_order": False,
                                             "shape": tuple(int(s) for s in shape)})
            i = 0
            while i < n:
                m = min(rows_per_chunk, n - i)
                buf = f.read(m * row)
                if len(buf) != m * row:
                    raise IOError(f"{member}: short read at row {i}")
                out.write(buf)
                i += m
        tmp.replace(dest)
    return tuple(int(s) for s in shape), str(dtype)


def build(raw: Path, out_dir: Path, expected: dict, size: int, n_channels: int) -> dict:
    """npz -> {split}_{images,labels}.npy under out_dir; verifies the split sizes against the
    release pin and the image geometry against the requested size. Returns the metadata."""
    meta = {"source": str(raw), "source_md5": md5sum(raw), "splits": {}}
    with zipfile.ZipFile(raw) as zf:
        names = set(zf.namelist())
        for split in D.SPLITS:
            for what in ("images", "labels"):
                member = f"{split}_{what}.npy"
                if member not in names:
                    raise KeyError(f"{raw.name} has no member {member}")
                shape, dtype = stream_member(zf, member, out_dir / member)
                meta["splits"].setdefault(split, {})[what] = {"shape": shape, "dtype": dtype}
            img = meta["splits"][split]["images"]["shape"]
            lab = meta["splits"][split]["labels"]["shape"]
            n = int(expected[split])
            if img[0] != n or lab[0] != n:
                raise ValueError(f"{raw.name} {split}: {img[0]} images / {lab[0]} labels, release says {n}")
            want = (n, size, size) if n_channels == 1 else (n, size, size, 3)
            if tuple(img) != want:
                raise ValueError(f"{raw.name} {split}: image shape {img}, expected {want}")
    return meta


def write_sample(cache: Path, ds: str, cfg: dict, out: Path) -> dict:
    """The seeded test sample and labelled pool at 224, with their images, as one small npz."""
    task = D.task_string(cfg, ds)
    test_lab = np.load(cache / "test_labels.npy")
    train_lab = np.load(cache / "train_labels.npy")
    test_idx, pool_idx = D.draw_sample(len(test_lab), len(train_lab), cfg["sample"])
    test_img = np.load(cache / "test_images.npy", mmap_mode="r")
    train_img = np.load(cache / "train_images.npy", mmap_mode="r")
    out.parent.mkdir(parents=True, exist_ok=True)
    np.savez(out, test_idx=test_idx, pool_idx=pool_idx,
             test_images=np.ascontiguousarray(test_img[test_idx]),
             pool_images=np.ascontiguousarray(train_img[pool_idx]),
             test_labels=test_lab[test_idx], pool_labels=train_lab[pool_idx])
    y_test = D.labels_1d(test_lab[test_idx], task)
    y_pool = D.labels_1d(train_lab[pool_idx], task)
    counts = (lambda y: np.bincount(y, minlength=D.n_classes(cfg, ds)).tolist()) if y_test.ndim == 1 \
        else (lambda y: y.sum(0).tolist())
    return {"test_n": int(len(test_idx)), "pool_n": int(len(pool_idx)), "seed": int(cfg["sample"]["seed"]),
            "test_class_counts": counts(y_test), "pool_class_counts": counts(y_pool),
            "test_idx_first": test_idx[:5].tolist(), "pool_idx_first": pool_idx[:5].tolist()}
