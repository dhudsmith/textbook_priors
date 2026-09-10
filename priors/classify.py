"""classify: arms A, B, C and P and the permutation controls on the shared test sample (WORKFLOW.md section 3).

One job per dataset. It reads the response archive (the primary model's concept answers for the
test sample and labelled pool, the ladder models' for the test sample, the zero-shot distributions),
the ImageNet features, and the sample labels, and writes every arm's class scores on the same
test images, so EVALUATE is uniform over arms.

Estimators, as fixed in section 3:
  concept vector  each concept's ordered scale mapped to equally spaced values on [0, 1]; a missing
                  answer becomes the labelled-pool median plus a missing-indicator column, dropped
                  where constant in the fitting subset
  arm B           negative mean absolute difference over the concepts the fingerprint commits to
                  and the image answered; `any` masked; AUC reads the score directly
  arms C and P    the same L2 logistic regression (one-vs-rest per finding for chestmnist), L2
                  strength by CV inside the n labelled images, features standardised on those n;
                  class-stratified nested subsets shared by C and P, a floor of one per class
  controls        B with fingerprint rows permuted across classes; C with concept columns permuted
                  across images; both seeded per cell
"""
from __future__ import annotations

import json
import warnings
from pathlib import Path

import numpy as np

from . import data as D
from . import evaluate as E
from .manifest import Run


# ---- the response archive -----------------------------------------------------------------------

def archive_path(cfg, ds, model, split, prompt, k) -> Path:
    return D._path(cfg["outdir"]) / "score" / f"{ds}__{model}__{split}__{prompt}__chunk{k}.json"


def read_archive(cfg, ds, model, split, prompt) -> dict:
    """All chunks of one cell, checked contiguous over the split sample. answers: list (concept) of
    id -> level dicts; distributions: n x K array with NaN rows where unusable (zero-shot)."""
    n = D.sample_sizes(cfg, ds)[split]
    chunk = int(cfg["vlm"]["chunk"])
    rows, served, calls = [], set(), 0
    for k in range((n + chunk - 1) // chunk):
        j = json.loads(archive_path(cfg, ds, model, split, prompt, k).read_text())
        if j["lo"] != k * chunk or j["hi"] != min(n, (k + 1) * chunk) or j["n_images"] != j["hi"] - j["lo"]:
            raise ValueError(f"archive chunk {k} of {ds}/{model}/{split}/{prompt} does not cover [{k * chunk}, {min(n, (k + 1) * chunk)})")
        rows += j["images"]
        served |= set(j["manifest"].get("served_model") or [])
        calls += j["calls"]
    if [r["i"] for r in rows] != list(range(n)):
        raise ValueError(f"archive of {ds}/{model}/{split}/{prompt} is not the contiguous sample")
    out = {"n": n, "served": sorted(served), "calls": calls,
           "n_incomplete": int(sum(r["n_missing"] > 0 for r in rows)),
           "frac_incomplete": float(np.mean([r["n_missing"] > 0 for r in rows]))}
    if prompt == "concept":
        out["answers"] = [r["answers"] for r in rows]
    else:
        K = D.n_classes(cfg, ds)
        P = np.full((n, K), np.nan)
        for i, r in enumerate(rows):
            if r.get("distribution") is not None:
                P[i] = r["distribution"]
        out["distributions"] = P
    return out


# ---- features from concept answers ---------------------------------------------------------------

def impute(X_fit: np.ndarray, X_apply: np.ndarray):
    """Pool medians for missing values, plus a missing indicator per concept that is not constant
    over the fitting rows. Returns (Z_fit, Z_apply, info)."""
    med = np.nanmedian(X_fit, axis=0)
    med = np.where(np.isnan(med), 0.5, med)          # a concept nobody answered in the subset
    miss_fit, miss_apply = np.isnan(X_fit), np.isnan(X_apply)
    keep = miss_fit.any(0) & ~miss_fit.all(0)        # informative indicators only
    Zf = np.where(miss_fit, med, X_fit)
    Za = np.where(miss_apply, med, X_apply)
    if keep.any():
        Zf = np.hstack([Zf, miss_fit[:, keep].astype(float)])
        Za = np.hstack([Za, miss_apply[:, keep].astype(float)])
    return Zf, Za, {"indicators": int(keep.sum()), "medians": med.tolist()}


def standardise(Z_fit: np.ndarray, Z_apply: np.ndarray):
    mu = Z_fit.mean(0)
    sd = Z_fit.std(0)
    sd = np.where(sd < 1e-8, 1.0, sd)                # constant columns stay constant (zero)
    return (Z_fit - mu) / sd, (Z_apply - mu) / sd


# ---- arm B ---------------------------------------------------------------------------------------

def arm_b(X: np.ndarray, F: np.ndarray) -> np.ndarray:
    """n x K scores: minus the mean |x - f| over concepts where both the fingerprint commits and the
    image answered. No overlap at all scores -1 (the worst possible distance)."""
    diff = np.abs(X[:, None, :] - F[None, :, :])      # n x K x C, NaN where either is missing
    valid = ~np.isnan(diff)
    cnt = valid.sum(2)
    s = -np.where(valid, diff, 0.0).sum(2) / np.maximum(cnt, 1)
    return np.where(cnt > 0, s, -1.0)


def permute_rows(F: np.ndarray, seed: int) -> np.ndarray:
    """The fingerprints reassigned to the wrong classes: a seeded non-identity permutation."""
    rng = np.random.default_rng(seed)
    K = len(F)
    perm = rng.permutation(K)
    while K > 1 and np.array_equal(perm, np.arange(K)):
        perm = rng.permutation(K)
    return F[perm]


def permute_columns(X: np.ndarray, seed: int) -> np.ndarray:
    """Each concept column shuffled independently across images: the image-feature link destroyed,
    the marginal distribution of every concept kept."""
    rng = np.random.default_rng(seed)
    Xp = X.copy()
    for j in range(X.shape[1]):
        Xp[:, j] = X[rng.permutation(len(X)), j]
    return Xp


# ---- nested, stratified subsets --------------------------------------------------------------------

def strata(y: np.ndarray, task: str) -> np.ndarray:
    """The class for single-label tasks; any-finding vs no-finding for chestmnist."""
    if task == "multi-label, binary-class":
        return (np.asarray(y).sum(1) > 0).astype(int)
    return np.asarray(y).reshape(-1)


def stratified_order(s: np.ndarray, seed: int) -> np.ndarray:
    """A permutation whose every prefix is class-stratified: one of each class first, then the class
    whose share in the prefix falls furthest below its share in the pool (largest remainder)."""
    rng = np.random.default_rng(seed)
    classes = np.unique(s)
    members = {c: list(rng.permutation(np.flatnonzero(s == c))) for c in classes}
    share = {c: len(members[c]) / len(s) for c in classes}
    taken = {c: 0 for c in classes}
    order = []
    for c in rng.permutation(classes):
        order.append(members[c].pop()); taken[c] += 1
    while len(order) < len(s):
        t = len(order) + 1
        c = max((c for c in classes if members[c]), key=lambda c: (share[c] * t - taken[c], rng.random()))
        order.append(members[c].pop()); taken[c] += 1
    return np.asarray(order, dtype=np.int64)


def nested_subsets(y: np.ndarray, task: str, sizes, seed: int) -> dict:
    order = stratified_order(strata(y, task), seed)
    return {int(n): order[:int(n)] for n in sizes if int(n) <= len(order)}


# ---- the shared logistic regression -----------------------------------------------------------------

def _lr(C, seed):
    from sklearn.linear_model import LogisticRegression
    return LogisticRegression(C=C, max_iter=5000, tol=1e-6, random_state=seed)


def _proba_full(model, X, K):
    p = np.zeros((len(X), K))
    p[:, model.classes_.astype(int)] = model.predict_proba(X)
    return p


def _cv_pick(Xf, yf, K, l2_grid, folds_cfg, l2_default, seed, task):
    """The L2 strength by stratified CV inside the fitting rows, scored by macro AUC on the pooled
    out-of-fold probabilities. Folds = min(cfg, smallest class count); below two, no CV."""
    from sklearn.model_selection import StratifiedKFold
    present, counts = np.unique(yf, return_counts=True)
    folds = int(min(int(folds_cfg), counts.min()))
    if folds < 2 or len(present) < 2:
        return float(l2_default), folds, None
    skf = StratifiedKFold(folds, shuffle=True, random_state=seed)
    best, best_auc = None, -np.inf
    for lam in l2_grid:
        oof = np.zeros((len(Xf), K))
        for tr, te in skf.split(Xf, yf):
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = _lr(1.0 / float(lam), seed).fit(Xf[tr], yf[tr])
            oof[te] = _proba_full(m, Xf[te], K)
        auc = E.macro_auc(yf, oof, present_only=True)
        if auc > best_auc or (auc == best_auc and float(lam) > best):
            best, best_auc = float(lam), auc
    return best, folds, float(best_auc)


def fit_predict(X_fit, y_fit, X_apply, *, task, K, ccfg, seed):
    """Standardise on the fitting rows, pick L2 by CV, fit, and score the apply rows: n_apply x K
    probabilities (a class absent from the subset gets zero). Returns (P, meta)."""
    Zf, Za = standardise(X_fit, X_apply)
    grid, folds, default = ccfg["l2_grid"], ccfg["cv_folds"], ccfg["l2_default"]
    if task == "multi-label, binary-class":
        P = np.zeros((len(Za), K))
        meta = {"lambda": [], "folds": []}
        for j in range(K):
            yj = np.asarray(y_fit)[:, j].astype(int)
            if yj.min() == yj.max():                          # no positives (or no negatives) in the subset
                P[:, j] = float(yj.min()); meta["lambda"].append(None); meta["folds"].append(0); continue
            lam, folds_j, _ = _cv_pick(Zf, yj, 2, grid, folds, default, seed, task)
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                m = _lr(1.0 / lam, seed).fit(Zf, yj)
            P[:, j] = _proba_full(m, Za, 2)[:, 1]
            meta["lambda"].append(lam); meta["folds"].append(folds_j)
        return P, meta
    yf = np.asarray(y_fit).reshape(-1).astype(int)
    lam, folds_used, cv_auc = _cv_pick(Zf, yf, K, grid, folds, default, seed, task)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        m = _lr(1.0 / lam, seed).fit(Zf, yf)
    return _proba_full(m, Za, K), {"lambda": lam, "folds": folds_used, "cv_auc": cv_auc,
                                   "classes_present": int(len(np.unique(yf)))}


# ---- the job -----------------------------------------------------------------------------------------

def classify_dataset(cfg: dict, ds: str, out, log=print) -> None:
    vcfg, ccfg = cfg["vlm"], cfg["classify"]
    task = D.task_string(cfg, ds)
    names = D.class_names(cfg, ds)
    K = len(names)
    bank = D.load_bank(cfg, ds)
    sample = D.load_sample(cfg, ds)
    y_test = D.labels_1d(sample["test_labels"], task)
    y_pool = D.labels_1d(sample["pool_labels"], task)
    in_b = ds not in cfg["arm_b_exclude"]
    primary = vcfg["primary"]
    arrays, meta = {"y_true": y_test}, {"dataset": ds, "task": task, "classes": names, "arms": {}, "completeness": {}}

    # the archive, and the completeness gate per (model, split)
    arch = {}
    for m, mc in vcfg["models"].items():
        if not in_b and m != primary:
            continue
        for split in mc["splits"]:
            a = read_archive(cfg, ds, m, split, "concept")
            arch[(m, split)] = a
            meta["completeness"][f"{m}__{split}"] = {"frac_incomplete": a["frac_incomplete"], "n_incomplete": a["n_incomplete"],
                                                     "n": a["n"], "served": a["served"], "calls": a["calls"],
                                                     "flagged": a["frac_incomplete"] > float(ccfg["missing_max_frac"])}
    X_test = D.answers_matrix(bank, arch[(primary, "test")]["answers"])
    X_pool = D.answers_matrix(bank, arch[(primary, "pool")]["answers"])

    if in_b:
        # arm A: the zero-shot distribution; an unusable reply becomes uniform, and is counted
        z = read_archive(cfg, ds, primary, "test", "zeroshot")
        Pz = z["distributions"]
        bad = np.isnan(Pz).any(1)
        Pz[bad] = 1.0 / K
        arrays["A"] = Pz
        meta["arms"]["A"] = {"n_unusable": int(bad.sum()), "served": z["served"]}
        meta["completeness"][f"{primary}__test__zeroshot"] = {"frac_incomplete": z["frac_incomplete"], "n": z["n"],
                                                              "flagged": z["frac_incomplete"] > float(ccfg["missing_max_frac"])}
        # arm B per model, and its fingerprint-permutation control
        F = D.fingerprint_matrix(bank, names)
        for m in vcfg["models"]:
            Xm = D.answers_matrix(bank, arch[(m, "test")]["answers"])
            arrays[f"B__{m}"] = arm_b(Xm, F)
            for s in ccfg["permute"]["seeds"]:
                arrays[f"Bperm__{m}__seed{s}"] = arm_b(Xm, permute_rows(F, int(s)))
        meta["arms"]["B"] = {"committed_cells": int((~np.isnan(F)).sum()), "cells": int(F.size)}

    # arms C and P on nested subsets of the pool, and the column-permutation control of C
    feats = np.load(str(D._path(cfg["outdir"]) / "features" / f"{ds}.npz"))
    if not np.array_equal(feats["pool_idx"], sample["pool_idx"]) or not np.array_equal(feats["test_idx"], sample["test_idx"]):
        raise ValueError("feature arrays were computed on a different sample")
    Ftest, Fpool = feats["test"], feats["pool"]
    sizes = [int(n) for n in cfg["curve"]["n"] if int(n) <= len(y_pool)]
    meta["curve"] = {"n": sizes, "seeds": list(cfg["curve"]["seeds"])}
    meta["cells"] = {}
    for seed in cfg["curve"]["seeds"]:
        subsets = nested_subsets(y_pool, task, sizes, int(seed))
        for n, idx in subsets.items():
            Zf, Zt, imp = impute(X_pool[idx], X_test)
            PC, mC = fit_predict(Zf, y_pool[idx], Zt, task=task, K=K, ccfg=ccfg, seed=int(seed))
            PP, mP = fit_predict(Fpool[idx], y_pool[idx], Ftest, task=task, K=K, ccfg=ccfg, seed=int(seed))
            arrays[f"C__n{n}__seed{seed}"] = PC
            arrays[f"P__n{n}__seed{seed}"] = PP
            Xperm = permute_columns(X_pool, int(seed))
            Zf2, Zt2, _ = impute(Xperm[idx], X_test)
            PCp, _ = fit_predict(Zf2, y_pool[idx], Zt2, task=task, K=K, ccfg=ccfg, seed=int(seed))
            arrays[f"Cperm__n{n}__seed{seed}"] = PCp
            counts = np.bincount(strata(y_pool[idx], task), minlength=2).tolist()
            meta["cells"][f"n{n}__seed{seed}"] = {"C": mC, "P": mP, "indicators": imp["indicators"], "strata_counts": counts}
            log(f"{ds} n={n} seed={seed}: C lambda={mC.get('lambda')} P lambda={mP.get('lambda')} folds={mC.get('folds')}", flush=True)

    with Run("classify", dict(dataset=ds, primary=primary, models=list(vcfg["models"]), l2_grid=ccfg["l2_grid"],
                              cv_folds=ccfg["cv_folds"], l2_default=ccfg["l2_default"], curve_n=cfg["curve"]["n"],
                              curve_seeds=cfg["curve"]["seeds"], permute_seeds=ccfg["permute"]["seeds"],
                              missing_max_frac=ccfg["missing_max_frac"], anchors=vcfg["prompt"]["anchors"]),
             seeds=list(cfg["curve"]["seeds"]) + list(ccfg["permute"]["seeds"])) as run:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        npz = str(out)[:-5] + ".npz"
        np.savez(npz, **{k: np.asarray(v, dtype=np.float32 if k != "y_true" else np.int64) for k, v in arrays.items()})
        meta["arrays"] = npz
        meta["array_names"] = sorted(arrays)
        run.write(out, meta, extra={"bank_hash": D.file_hash(D.bank_path(cfg, ds))})
    log(f"wrote {out} with {len(arrays)} score matrices")
