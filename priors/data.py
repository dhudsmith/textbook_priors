"""data: the workflow's fixed inputs and how every stage reads them.

Three things live here and nowhere else: the pinned MedMNIST release (config/medmnist.yaml: task
strings, label maps, split sizes, file names and checksums), the concept bank (data/concepts/*.yaml)
with the validation rules CONCEPT_BANK.md fixes, and the seeded test sample and labelled pool that
every arm predicts on (WORKFLOW.md section 4). Nothing here computes a result.
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parent.parent

# medmnist's raw task string -> the vocabulary of CONCEPT_BANK.md; the bank carries both.
TASKS = {
    "multi-class": "multi-class",
    "binary-class": "binary",
    "multi-label, binary-class": "multi-label",
    "ordinal-regression": "ordinal",
}
SPLITS = ("train", "val", "test")


def _path(p) -> Path:
    p = Path(os.path.expanduser(str(p)))
    return p if p.is_absolute() else ROOT / p


def load_yaml(p):
    return yaml.safe_load(_path(p).read_text())


def load_config(path=None) -> dict:
    return load_yaml(path or os.environ.get("PRIORS_CONFIG", "config/config.yaml"))


def load_release(cfg) -> dict:
    return load_yaml(cfg["release"])


def info(cfg, ds) -> dict:
    return load_release(cfg)["datasets"][ds]


def task_string(cfg, ds) -> str:
    return info(cfg, ds)["task"]


def class_names(cfg, ds) -> list[str]:
    """Class names in label-index order, verbatim from the medmnist label map."""
    lab = info(cfg, ds)["label"]
    return [lab[str(i)] for i in range(len(lab))]


def n_split(cfg, ds, split) -> int:
    return int(info(cfg, ds)["n_samples"][split])


def n_classes(cfg, ds) -> int:
    return len(info(cfg, ds)["label"])


def raw_path(cfg, ds, size) -> Path:
    return _path(cfg["rawdir"]) / info(cfg, ds)["files"][int(size)]["name"]


def cache_dir(cfg, ds, size) -> Path:
    return _path(cfg["cachedir"]) / f"{ds}_{int(size)}"


def cache_meta(cfg, ds, size) -> Path:
    return _path(cfg["cachedir"]) / f"{ds}_{int(size)}.json"


def cache_array(cfg, ds, size, split, what="images", mmap=True):
    """One cached split as a read-only memmap (`what` is images or labels)."""
    return np.load(cache_dir(cfg, ds, size) / f"{split}_{what}.npy", mmap_mode="r" if mmap else None)


# ---- the concept bank -------------------------------------------------------------------------

def bank_path(cfg, ds) -> Path:
    return _path(cfg["conceptdir"]) / f"{ds}.yaml"


def load_bank(cfg, ds) -> dict:
    return load_yaml(bank_path(cfg, ds))


def file_hash(path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def concept_ids(bank) -> list[str]:
    return [c["id"] for c in bank["concepts"]]


def scale_values(scale) -> np.ndarray:
    """An ordered scale mapped to equally spaced values on [0, 1] (WORKFLOW.md section 3). A
    two-level scale is {0, 1}; a five-level one steps by 0.25, so short scales weigh more."""
    return np.linspace(0.0, 1.0, len(scale))


def level_value(concept, level) -> float:
    """The value of one answered level; NaN for a missing answer or an `any` fingerprint cell."""
    if level is None or level == "any":
        return np.nan
    return float(scale_values(concept["scale"])[concept["scale"].index(level)])


def fingerprint_matrix(bank, names) -> np.ndarray:
    """K x C matrix of fingerprint values in label-index order; NaN where the bank says `any`."""
    F = np.full((len(names), len(bank["concepts"])), np.nan)
    for k, name in enumerate(names):
        fp = bank["classes"][name]["fingerprint"]
        for j, c in enumerate(bank["concepts"]):
            F[k, j] = level_value(c, fp[c["id"]])
    return F


def answers_matrix(bank, answers) -> np.ndarray:
    """n x C matrix from per-image answer dicts (None or a dict id -> level/None); NaN = missing."""
    X = np.full((len(answers), len(bank["concepts"])), np.nan)
    for i, a in enumerate(answers):
        if not a:
            continue
        for j, c in enumerate(bank["concepts"]):
            lv = a.get(c["id"])
            if lv in c["scale"]:
                X[i, j] = level_value(c, lv)
    return X


_ID = re.compile(r"^[a-z][a-z0-9_]*$")


def validate_bank(bank, ds, ds_info) -> list[str]:
    """Every machine-checkable rule of CONCEPT_BANK.md, as a list of problems (empty = valid)."""
    p = []
    names = [ds_info["label"][str(i)] for i in range(len(ds_info["label"]))]
    if bank.get("dataset") != ds:
        p.append(f"dataset field is {bank.get('dataset')!r}, file is {ds}")
    if bank.get("medmnist_task") != ds_info["task"]:
        p.append(f"medmnist_task {bank.get('medmnist_task')!r} != package {ds_info['task']!r}")
    if TASKS.get(bank.get("medmnist_task")) != bank.get("task"):
        p.append(f"task {bank.get('task')!r} does not map from medmnist_task {bank.get('medmnist_task')!r}")
    if not isinstance(bank.get("modality"), str) or not bank["modality"].strip():
        p.append("modality missing")
    prov = bank.get("provenance") or {}
    reviewed = str(prov.get("reviewed_by", ""))
    if not reviewed:
        p.append("provenance.reviewed_by missing")
    elif "simulated" not in reviewed:
        p.append("provenance.reviewed_by does not say the review was simulated")
    src = {}
    for s in prov.get("sources") or []:
        if not s.get("key") or not s.get("citation"):
            p.append(f"source without key or citation: {s}")
            continue
        if not (s.get("doi") or s.get("url")):
            p.append(f"source {s['key']} has neither doi nor url")
        src[s["key"]] = s

    def keys_ok(keys, where):
        if not isinstance(keys, list) or not keys:
            p.append(f"{where}: no sources")
            return
        for k in keys:
            if k not in src:
                p.append(f"{where}: unknown source key {k!r}")

    concepts = bank.get("concepts") or []
    if not 6 <= len(concepts) <= 12:
        p.append(f"{len(concepts)} concepts; the bank allows six to twelve")
    ids = []
    for c in concepts:
        cid = c.get("id")
        if not isinstance(cid, str) or not _ID.match(cid):
            p.append(f"bad concept id {cid!r}")
            continue
        ids.append(cid)
        if not isinstance(c.get("question"), str) or not c["question"].strip():
            p.append(f"{cid}: question missing")
        scale = c.get("scale")
        if not isinstance(scale, list) or not 2 <= len(scale) <= 5 or len(set(scale)) != len(scale) \
                or not all(isinstance(s, str) for s in scale) or "any" in scale:
            p.append(f"{cid}: scale must be two to five distinct level strings, not {scale!r}")
            scale = scale if isinstance(scale, list) else []
        keys_ok(c.get("sources"), cid)
        anchors = c.get("anchors")
        if not isinstance(anchors, dict):
            p.append(f"{cid}: anchors block missing")
            continue
        if set(anchors) != set(scale):
            p.append(f"{cid}: anchors {sorted(anchors)} do not match scale {scale}")
        texts = []
        for lv, a in anchors.items():
            t = (a or {}).get("text") if isinstance(a, dict) else None
            if not isinstance(t, str) or not t.strip():
                p.append(f"{cid}.{lv}: anchor text missing")
                continue
            if t.strip().lower() == str(lv).strip().lower().replace("_", " ") or t.strip().lower() == str(lv).lower():
                p.append(f"{cid}.{lv}: anchor merely restates the level token")
            texts.append(t.strip())
            keys_ok(a.get("sources"), f"{cid}.{lv} anchor")
        if len(set(texts)) != len(texts):
            p.append(f"{cid}: two anchors share the same text")
    if len(set(ids)) != len(ids):
        p.append("duplicate concept ids")
    classes = bank.get("classes") or {}
    if set(classes) != set(names):
        p.append(f"classes {sorted(classes)} != label map {sorted(names)}")
    for name, cl in classes.items():
        fp = (cl or {}).get("fingerprint")
        if not isinstance(fp, dict):
            p.append(f"class {name!r}: fingerprint missing")
            continue
        if set(fp) != set(ids):
            p.append(f"class {name!r}: fingerprint names {sorted(fp)} != concepts {sorted(ids)}")
        for c in concepts:
            lv = fp.get(c.get("id"))
            if lv is not None and lv != "any" and lv not in (c.get("scale") or []):
                p.append(f"class {name!r}.{c.get('id')}: level {lv!r} not on the scale")
        if "sources" in (cl or {}):
            keys_ok(cl["sources"], f"class {name!r}")
    return p


def retina_monotone(bank) -> list[str]:
    """retinamnist's committed levels must not decrease across grades 0..4 for any concept."""
    p = []
    grades = [str(g) for g in range(5)]
    for c in bank["concepts"]:
        idx = [c["scale"].index(bank["classes"][g]["fingerprint"][c["id"]])
               for g in grades if bank["classes"][g]["fingerprint"][c["id"]] != "any"]
        if any(b < a for a, b in zip(idx, idx[1:])):
            p.append(f"{c['id']}: committed levels are not monotone across grades: {idx}")
    return p


# ---- the shared test sample and the labelled pool ----------------------------------------------

def sample_sizes(cfg, ds) -> dict:
    s = cfg["sample"]
    return {"test": min(int(s["test_n"]), n_split(cfg, ds, "test")),
            "pool": min(int(s["pool_n"]), n_split(cfg, ds, "train"))}


def draw_sample(n_test, n_train, sample_cfg) -> tuple[np.ndarray, np.ndarray]:
    """The seeded test sample and labelled pool as sorted index arrays into the official test and
    train splits. One generator, test first, so a change to pool_n cannot move the test sample."""
    rng = np.random.default_rng(int(sample_cfg["seed"]))
    test_idx = np.sort(rng.choice(n_test, min(int(sample_cfg["test_n"]), n_test), replace=False))
    pool_idx = np.sort(rng.choice(n_train, min(int(sample_cfg["pool_n"]), n_train), replace=False))
    return test_idx.astype(np.int64), pool_idx.astype(np.int64)


def sample_path(cfg, ds) -> Path:
    return _path(cfg["cachedir"]) / f"{ds}_sample.npz"


def load_sample(cfg, ds) -> dict:
    """test_idx, pool_idx, test_images, pool_images (uint8 at 224), test_labels, pool_labels."""
    with np.load(sample_path(cfg, ds)) as z:
        return {k: z[k] for k in z.files}


def labels_1d(y, task) -> np.ndarray:
    """medmnist stores labels as (n, 1) for single-label tasks and (n, 14) for chestmnist."""
    y = np.asarray(y)
    if task == "multi-label, binary-class":
        return y.astype(np.int64)
    return y.reshape(-1).astype(np.int64)
