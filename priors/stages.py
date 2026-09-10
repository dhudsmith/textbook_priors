"""The workflow's computations, one entry point per unit of parallel work.

Each stage is a pure function of config/config.yaml, its command-line cell and the seed it derives
from them, and writes ONE JSON file: {"manifest": {...}, ...payload}, with large arrays beside it
under the same stem. Nothing here prints a table; tables and figures are drawn from the files by
the report stage.

    cache DATASET SIZE --out FILE          npz -> memory-mappable uint8 .npy per split (stage 2)
    sample DATASET --out FILE              the seeded test sample and labelled pool at 224 (stage 2)
    score DATASET MODEL SPLIT PROMPT K --out FILE   one chunk of the response archive (stage 3)
    probe --out FILE                       the opt-in ten-image probe, outside the archive
    features DATASET --out FILE            ImageNet ResNet-18 features of the sample (stage 4)
    train DATASET SIZE SEED --out FILE     arm E, ResNet-18 from scratch (stage 5)
    classify DATASET --out FILE            arms A, B, C, P and the permutation controls (stage 6)
    evaluate DATASET --out FILE            AUC/ACC, the paired bootstrap, n_B (stage 7)
    summary --out FILE                     the sign tests and the H3 ladder analysis (stage 7)
    reconcile --out FILE                   arm E against the published table (stage 8)
    tables --dest DIR                      every table and number macro the report states
    figures --dest DIR                     the three figures

Run with  python -m priors.stages <stage> [args]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import data as D
from .manifest import Run

CONFIG = D.load_config()


def cache(ds: str, size: int, out: str) -> None:
    from . import cache as C
    ds_info = D.info(CONFIG, ds)
    raw = D.raw_path(CONFIG, ds, size)
    out_dir = D.cache_dir(CONFIG, ds, size)
    with Run("cache", dict(dataset=ds, size=int(size), source=ds_info["files"][int(size)])) as run:
        meta = C.build(raw, out_dir, ds_info["n_samples"], int(size), int(ds_info["n_channels"]))
        if meta["source_md5"] != ds_info["files"][int(size)]["md5"]:
            raise SystemExit(f"{raw}: md5 {meta['source_md5']} != pinned {ds_info['files'][int(size)]['md5']}")
        run.write(out, dict(dataset=ds, size=int(size), task=ds_info["task"], n_channels=ds_info["n_channels"],
                            cache_dir=str(out_dir), **meta))
    print(f"cached {ds} at {size}: " + ", ".join(f"{s} {meta['splits'][s]['images']['shape'][0]}" for s in D.SPLITS))


def sample(ds: str, out: str) -> None:
    from . import cache as C
    npz = D.sample_path(CONFIG, ds)
    with Run("sample", dict(dataset=ds, **CONFIG["sample"]), seeds=[int(CONFIG["sample"]["seed"])]) as run:
        meta = C.write_sample(D.cache_dir(CONFIG, ds, CONFIG["size"]), ds, CONFIG, npz)
        run.write(out, dict(dataset=ds, arrays=str(npz), **meta))
    print(f"sample {ds}: {meta['test_n']} test, {meta['pool_n']} pool")


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("cache"); p.add_argument("dataset"); p.add_argument("size", type=int); p.add_argument("--out", required=True)
    p = sub.add_parser("sample"); p.add_argument("dataset"); p.add_argument("--out", required=True)
    p = sub.add_parser("score"); p.add_argument("dataset"); p.add_argument("model"); p.add_argument("split"); p.add_argument("prompt")
    p.add_argument("chunk", type=int); p.add_argument("--out", required=True)
    p = sub.add_parser("probe"); p.add_argument("--out", required=True)
    p = sub.add_parser("features"); p.add_argument("dataset"); p.add_argument("--out", required=True)
    p = sub.add_parser("train"); p.add_argument("dataset"); p.add_argument("size", type=int); p.add_argument("seed", type=int); p.add_argument("--out", required=True)
    for name in ("classify", "evaluate"):
        q = sub.add_parser(name); q.add_argument("dataset"); q.add_argument("--out", required=True)
    for name in ("summary", "reconcile"):
        q = sub.add_parser(name); q.add_argument("--out", required=True)
    for name in ("tables", "figures"):
        q = sub.add_parser(name); q.add_argument("--dest", required=True)
    a = ap.parse_args(argv)
    if a.stage == "cache":
        cache(a.dataset, a.size, a.out)
    elif a.stage == "sample":
        sample(a.dataset, a.out)
    elif a.stage == "score":
        from . import score as S
        S.score_chunk(CONFIG, a.dataset, a.model, a.split, a.prompt, a.chunk, a.out)
    elif a.stage == "probe":
        from . import score as S
        S.probe(CONFIG, a.out)
    elif a.stage == "features":
        from . import features as F
        F.features_dataset(CONFIG, a.dataset, a.out)
    elif a.stage == "train":
        from . import train as T
        T.train_dataset(CONFIG, a.dataset, a.size, a.seed, a.out)
    elif a.stage == "classify":
        from . import classify as C
        C.classify_dataset(CONFIG, a.dataset, a.out)
    elif a.stage == "evaluate":
        from . import evaluate as E
        E.evaluate_dataset(CONFIG, a.dataset, a.out)
    elif a.stage == "summary":
        from . import evaluate as E
        E.summary(CONFIG, a.out)
    elif a.stage == "reconcile":
        from . import report as R
        R.reconcile(CONFIG, a.out)
    elif a.stage == "tables":
        from . import report as R
        R.tables(CONFIG, a.dest)
    elif a.stage == "figures":
        from . import report as R
        R.figures(CONFIG, a.dest)


if __name__ == "__main__":
    main()
