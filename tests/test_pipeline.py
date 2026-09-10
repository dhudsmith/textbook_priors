"""The CPU stages end to end on a synthetic world: a fake archive generated from the real bank's
fingerprints, fake features and fake arm-E results, through classify, evaluate, summary,
reconcile, tables and figures. Catches integration mistakes before any real result exists; no
number here means anything."""
import copy
import json
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("medmnist")

from priors import classify as C     # noqa: E402
from priors import data as D         # noqa: E402
from priors import evaluate as E     # noqa: E402
from priors import report as R       # noqa: E402

DATASETS = ["breastmnist", "octmnist", "pneumoniamnist", "chestmnist"]


def _world(tmp_path, cfg):
    cfg = copy.deepcopy(cfg)
    cfg.update(outdir=str(tmp_path / "results"), cachedir=str(tmp_path / "cache"), datasets=DATASETS,
               modality_order=DATASETS, sample={"test_n": 60, "pool_n": 100, "seed": 0},
               curve={"n": [10, 20, 40, 100], "seeds": [0, 1]})
    cfg["vlm"]["chunk"] = 25
    cfg["classify"]["permute"]["seeds"] = [0]
    cfg["evaluate"]["bootstrap"] = 40
    cfg["train"]["seeds"] = [0]
    rng = np.random.default_rng(0)
    for ds in DATASETS:
        task = D.task_string(cfg, ds)
        names = D.class_names(cfg, ds)
        K = len(names)
        bank = D.load_bank(cfg, ds)
        n_test, n_pool = 60, 100
        if task == "multi-label, binary-class":
            y_test = (rng.random((n_test, K)) < 0.15).astype(np.uint8)
            y_pool = (rng.random((n_pool, K)) < 0.15).astype(np.uint8)
            cls_test = rng.integers(0, K, n_test)
            cls_pool = rng.integers(0, K, n_pool)
        else:
            cls_test = np.concatenate([np.arange(K), rng.integers(0, K, n_test - K)])
            cls_pool = np.concatenate([np.arange(K), rng.integers(0, K, n_pool - K)])
            y_test, y_pool = cls_test.reshape(-1, 1).astype(np.uint8), cls_pool.reshape(-1, 1).astype(np.uint8)
        (tmp_path / "cache").mkdir(exist_ok=True)
        np.savez(tmp_path / "cache" / f"{ds}_sample.npz", test_idx=np.arange(n_test), pool_idx=np.arange(n_pool),
                 test_images=np.zeros((n_test, 8, 8), np.uint8), pool_images=np.zeros((n_pool, 8, 8), np.uint8),
                 test_labels=y_test, pool_labels=y_pool)

        def answers_for(cls, informative):
            out = []
            for i, k in enumerate(cls):
                a = {}
                for c in bank["concepts"]:
                    fp = bank["classes"][names[k]]["fingerprint"][c["id"]]
                    if informative and fp != "any" and rng.random() < 0.8:
                        a[c["id"]] = fp
                    else:
                        a[c["id"]] = c["scale"][rng.integers(0, len(c["scale"]))]
                if i == 0:                          # exactly one incomplete image per cell: under the 5% gate
                    a[bank["concepts"][0]["id"]] = None
                out.append(a)
            return out

        score_dir = tmp_path / "results" / "score"
        score_dir.mkdir(parents=True, exist_ok=True)
        in_b = ds not in cfg["arm_b_exclude"]
        for m, mc in cfg["vlm"]["models"].items():
            if not in_b and m != cfg["vlm"]["primary"]:
                continue
            for split in mc["splits"]:
                cls = cls_test if split == "test" else cls_pool
                ans = answers_for(cls, informative=in_b)
                n = len(cls)
                for k in range((n + 24) // 25):
                    lo, hi = 25 * k, min(n, 25 * k + 25)
                    images = [{"i": i, "answers": ans[i], "n_missing": sum(v is None for v in ans[i].values()),
                               "raw": [], "attempts": 1} for i in range(lo, hi)]
                    (score_dir / f"{ds}__{m}__{split}__concept__chunk{k}.json").write_text(json.dumps(
                        {"manifest": {"served_model": [f"served/{m}"]}, "lo": lo, "hi": hi, "n_images": hi - lo,
                         "calls": hi - lo, "images": images}))
        if in_b:
            for k in range((n_test + 24) // 25):
                lo, hi = 25 * k, min(n_test, 25 * k + 25)
                images = []
                for i in range(lo, hi):
                    p = rng.random(K) * 0.3
                    p[cls_test[i]] += 1.0
                    images.append({"i": i, "distribution": (p / p.sum()).tolist() if rng.random() > 0.05 else None, "n_missing": 0})
                (score_dir / f"{ds}__{cfg['vlm']['primary']}__test__zeroshot__chunk{k}.json").write_text(json.dumps(
                    {"manifest": {"served_model": ["served/p"]}, "lo": lo, "hi": hi, "n_images": hi - lo,
                     "calls": hi - lo, "images": images}))
        fdir = tmp_path / "results" / "features"
        fdir.mkdir(parents=True, exist_ok=True)
        centres = rng.normal(0, 1, (K, 16))
        np.savez(fdir / f"{ds}.npz", test=(centres[cls_test] + rng.normal(0, 1.5, (n_test, 16))).astype(np.float32),
                 pool=(centres[cls_pool] + rng.normal(0, 1.5, (n_pool, 16))).astype(np.float32),
                 test_idx=np.arange(n_test), pool_idx=np.arange(n_pool))
        (fdir / f"{ds}.json").write_text("{}")
        tdir = tmp_path / "results" / "train"
        tdir.mkdir(parents=True, exist_ok=True)
        for size in cfg["recon_sizes"]:
            (tdir / f"{ds}__s{size}__seed0.json").write_text(json.dumps(
                {"metrics": {"test_full": {"auc": 0.9, "acc": 0.8, "n": 100}, "sample": {"auc": 0.88, "acc": 0.78, "n": 60}}}))
    return cfg


def test_downstream_stages_run_end_to_end(tmp_path, cfg):
    cfg = _world(tmp_path, cfg)
    out = Path(cfg["outdir"])
    quiet = lambda *a, **k: None   # noqa: E731
    for ds in DATASETS:
        C.classify_dataset(cfg, ds, out / "classify" / f"{ds}.json", log=quiet)
        E.evaluate_dataset(cfg, ds, out / "evaluate" / f"{ds}.json", log=quiet)
    E.summary(cfg, out / "evaluate" / "summary.json", log=quiet)
    R.reconcile(cfg, out / "report" / "reconciliation.json", log=quiet)
    R.tables(cfg, tmp_path / "tables", log=quiet)
    R.figures(cfg, tmp_path / "figs", log=quiet)

    cl = json.loads((out / "classify" / "octmnist.json").read_text())
    with np.load(cl["arrays"]) as z:
        names = set(z.files)
        assert "A" in names and "B__qwen3.8-27b-fp8" in names and "Bperm__gemma-4-31b__seed0" in names
        assert "C__n10__seed1" in names and "P__n100__seed0" in names and "Cperm__n40__seed1" in names
        assert z["A"].shape == (60, 4) and np.allclose(z["A"].sum(1), 1, atol=1e-5)
    chest = json.loads((out / "classify" / "chestmnist.json").read_text())
    with np.load(chest["arrays"]) as z:
        assert "A" not in z.files and not any(k.startswith("B") for k in z.files)
        assert z["y_true"].shape == (60, 14) and z["C__n10__seed0"].shape == (60, 14)

    ev = json.loads((out / "evaluate" / "octmnist.json").read_text())
    assert ev["auc"]["B"]["qwen3.8-27b-fp8"] > 0.6            # fingerprint-generated answers are informative
    assert ev["n_b"]["label"] in {"<=10", "20", "40", "100", ">100"} and len(ev["n_b"]["ci_labels"]) == 2
    assert set(ev["bootstrap"]["C"]) == {"10", "20", "40", "100"} and len(ev["bootstrap"]["diff_B_minus_A"]) == 3
    assert ev["auc"]["E"]["224"]["sample_auc_mean"] == 0.88
    assert "perm_drop" in ev and "B" in ev["perm_drop"]
    chest_ev = json.loads((out / "evaluate" / "chestmnist.json").read_text())
    assert not chest_ev["arm_b"] and "n_b" not in chest_ev and "A" not in chest_ev["auc"]

    summ = json.loads((out / "evaluate" / "summary.json").read_text())
    assert not any(summ["flagged"].values()), summ["flagged"]
    assert summ["H1"]["n"] == 4 and summ["H2"]["n"] == 3 and len(summ["H3"]["datasets"]) == 3
    assert 0 <= summ["H1"]["p"] <= 1 and "anova" in summ["H3"] and "friedman" in summ["H3"]
    assert isinstance(summ["H3"]["supported"], bool) and isinstance(summ["H1"]["supported"], bool)

    rec = json.loads((out / "report" / "reconciliation.json").read_text())
    assert rec["n_rows"] == 8 and rec["expected_rows"] == 8

    for t in ("h1", "h2", "ladder", "ladder_anova", "reconciliation", "completeness", "numbers"):
        text = (tmp_path / "tables" / f"{t}.tex").read_text()
        assert text.strip(), t
        assert "\\\\\\\\" not in text, f"{t}: doubled row terminator"
    numbers = (tmp_path / "tables" / "numbers.tex").read_text()
    for macro in ("hOneVerdict", "hTwoVerdict", "hThreeVerdict", "nBmedian", "callsArchived", "reconAgree", "hThreeSlope"):
        assert f"\\newcommand{{\\{macro}}}" in numbers, macro
    for f in ("fig_curve", "fig_ladder", "fig_nb"):
        assert (tmp_path / "figs" / f"{f}.png").stat().st_size > 10_000, f
