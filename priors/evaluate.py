"""evaluate: every arm through the medmnist evaluator; the paired bootstrap; n_B; the sign tests;
the H3 ladder analysis (WORKFLOW.md section 2).

Per dataset, one job reads the classify arrays and arm E's results and writes every AUC and ACC,
the bootstrap intervals, and n_B with its interval. Across datasets, `summary` applies the decision
rules fixed in section 2: the one-sided sign tests for H1 and H2, and for H3 the blocked two-way
ANOVA of AUC(B) on family x size tier with dataset as block, the planned linear contrast on log10
parameters, and the Friedman test with Nemenyi post-hoc.

AUC and ACC come from medmnist.evaluator.getAUC/getACC, the package's own conventions (macro
one-vs-rest for multi-class and ordinal; the last column for binary; the mean over findings for
multi-label). `macro_auc` reproduces those conventions rank-wise, tolerating a class absent from a
bootstrap resample; tests/test_metrics.py holds it equal to getAUC where both are defined.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
from scipy import stats

from . import data as D
from .manifest import Run

MULTILABEL = "multi-label, binary-class"
# Demsar (2006), Table 5: critical values of the two-tailed Nemenyi test at alpha = 0.05.
NEMENYI_Q05 = {2: 1.960, 3: 2.343, 4: 2.569, 5: 2.728, 6: 2.850, 7: 2.949, 8: 3.031}


def getAUC(y, S, task):
    from medmnist.evaluator import getAUC as f
    return float(f(np.asarray(y), np.asarray(S), task))


def getACC(y, S, task):
    from medmnist.evaluator import getACC as f
    return float(f(np.asarray(y), np.asarray(S), task))


def _rank_auc(y_bin: np.ndarray, s: np.ndarray) -> float:
    n1 = int(y_bin.sum())
    n0 = len(y_bin) - n1
    if n1 == 0 or n0 == 0:
        return float("nan")
    r = stats.rankdata(s)
    return float((r[y_bin == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def macro_auc(y, S, task=None, present_only=False) -> float:
    """getAUC's conventions via the Mann-Whitney identity. With present_only, classes absent from
    y (a bootstrap resample) are skipped instead of making the value undefined."""
    y = np.asarray(y).squeeze()
    S = np.asarray(S).squeeze()
    if task == MULTILABEL or (task is None and y.ndim == 2):
        vals = [_rank_auc(y[:, j].astype(int), S[:, j]) for j in range(S.shape[1])]
    elif task == "binary-class":
        return _rank_auc(y.astype(int), S[:, -1] if S.ndim == 2 else S)
    else:
        vals = [_rank_auc((y == i).astype(int), S[:, i]) for i in range(S.shape[1])]
    vals = np.asarray(vals)
    if present_only:
        vals = vals[np.isfinite(vals)]
    return float(vals.mean()) if len(vals) else float("nan")


def safe_auc(y, S, task) -> tuple[float, bool]:
    """getAUC where every class is present in y, else the present-only macro AUC (flagged). An
    absent class makes sklearn raise in older versions and return NaN with a warning in newer ones;
    both are the same case here."""
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            v = getAUC(y, S, task)
        if math.isfinite(v):
            return v, False
    except ValueError:
        pass
    return macro_auc(y, S, task, present_only=True), True


# ---- n_B and the sign test ----------------------------------------------------------------------

def crossing(auc_b: float, auc_p_by_n: dict, grid: list) -> tuple[str, int]:
    """The smallest grid n at which arm P reaches AUC(B): (label, position). Position j indexes the
    grid; len(grid) means never. Labels: "<=50" at the first point, ">n_max" when never."""
    for j, n in enumerate(grid):
        if auc_p_by_n[n] >= auc_b:
            return (f"<={grid[0]}" if j == 0 else str(n)), j
    return f">{grid[-1]}", len(grid)


def position_label(j: int, grid: list) -> str:
    if j >= len(grid):
        return f">{grid[-1]}"
    return f"<={grid[0]}" if j == 0 else str(grid[j])


def label_value(label: str) -> float:
    """A crossing label as a number for medians: "<=50" -> 50, "200" -> 200, ">2000" -> inf."""
    if label.startswith("<="):
        return float(label[2:])
    if label.startswith(">"):
        return math.inf
    return float(label)


def sign_test(wins: int, n: int) -> float:
    """One-sided exact sign test: P(X >= wins) under a fair coin over n datasets."""
    return float(stats.binomtest(int(wins), int(n), 0.5, alternative="greater").pvalue) if n > 0 else float("nan")


# ---- the H3 ladder ------------------------------------------------------------------------------

def ladder_anova(Y: np.ndarray, models: list[str], meta: dict, alpha: float = 0.05) -> dict:
    """Blocked two-way ANOVA of AUC(B) (datasets x models) on family x size tier, dataset as block,
    with the three orthogonal 1-df contrasts of the 2x2 and the planned linear trend on log10
    parameters, tested against the blocked error term. Y is N datasets x M models."""
    N, M = Y.shape
    ybar = Y.mean()
    ym = Y.mean(0)
    yd = Y.mean(1)
    ss_model = N * ((ym - ybar) ** 2).sum()
    ss_block = M * ((yd - ybar) ** 2).sum()
    resid = Y - ym[None, :] - yd[:, None] + ybar
    ss_err = (resid ** 2).sum()
    df_model, df_block, df_err = M - 1, N - 1, (M - 1) * (N - 1)
    mse = ss_err / df_err
    fam = np.array([1.0 if meta[m]["family"] == meta[models[0]]["family"] else -1.0 for m in models])
    params = np.array([float(meta[m]["params_b"]) for m in models])
    tier = np.where(params > np.median(params), 1.0, -1.0)     # the larger two vs the smaller two
    inter = fam * tier

    def contrast(c, one_sided=False):
        est = float((c * ym).sum() / (c ** 2).sum())           # the slope per unit of c
        ss = N * (c * ym).sum() ** 2 / (c ** 2).sum()
        F = ss / mse
        p_two = float(stats.f.sf(F, 1, df_err))
        se = math.sqrt(mse / (N * (c ** 2).sum()))
        t = est / se
        out = {"estimate": est, "se": se, "t": float(t), "F": float(F), "df": [1, df_err], "p": p_two}
        if one_sided:
            out["p_one_sided_positive"] = float(stats.t.sf(t, df_err))
        return out

    lp = np.log10(params)
    trend = contrast(lp - lp.mean(), one_sided=True)
    fam_means = {}
    for f in sorted({meta[m]["family"] for m in models}):
        idx = [i for i, m in enumerate(models) if meta[m]["family"] == f]
        small, large = sorted(idx, key=lambda i: params[i])[0], sorted(idx, key=lambda i: params[i])[-1]
        fam_means[f] = {"small": models[small], "large": models[large], "gain_large_minus_small": float(ym[large] - ym[small])}
    F_model = (ss_model / df_model) / mse
    F_block = (ss_block / df_block) / mse
    inter_c = contrast(inter)
    out = {
        "n_datasets": int(N), "models": models, "model_means": dict(zip(models, ym.tolist())),
        "anova": {
            "model": {"ss": float(ss_model), "df": df_model, "F": float(F_model), "p": float(stats.f.sf(F_model, df_model, df_err))},
            "block": {"ss": float(ss_block), "df": df_block, "F": float(F_block), "p": float(stats.f.sf(F_block, df_block, df_err))},
            "error": {"ss": float(ss_err), "df": df_err, "mse": float(mse)},
            "family": contrast(fam), "size_tier": contrast(tier), "interaction": inter_c,
        },
        "trend_log10_params": trend,
        "within_family": fam_means,
        "alpha": alpha,
    }
    gains_positive = all(v["gain_large_minus_small"] > 0 for v in fam_means.values())
    out["supported"] = bool(trend["estimate"] > 0 and trend["p_one_sided_positive"] < alpha and gains_positive)
    out["rule"] = ("positive linear trend on log10 parameters at p < alpha (one-sided, blocked error term) and the "
                   "large-minus-small gain positive within every family, so the trend is not carried by one family alone")
    return out


def friedman_nemenyi(Y: np.ndarray, models: list[str], alpha: float = 0.05) -> dict:
    """Friedman over the models with datasets as blocks; Nemenyi critical difference on the average
    ranks (rank 1 = best AUC within a dataset)."""
    N, M = Y.shape
    chi2, p = stats.friedmanchisquare(*[Y[:, j] for j in range(M)])
    ranks = np.array([stats.rankdata(-row) for row in Y])     # higher AUC -> smaller rank
    avg = ranks.mean(0)
    q = NEMENYI_Q05.get(M)
    cd = q * math.sqrt(M * (M + 1) / (6 * N)) if q else float("nan")
    pairs = []
    for i in range(M):
        for j in range(i + 1, M):
            pairs.append({"a": models[i], "b": models[j], "rank_diff": float(avg[i] - avg[j]),
                          "significant": bool(abs(avg[i] - avg[j]) > cd) if q else None})
    return {"chi2": float(chi2), "p": float(p), "average_ranks": dict(zip(models, avg.tolist())),
            "critical_difference": float(cd), "q_alpha": q, "alpha": alpha, "pairs": pairs}


# ---- per dataset ---------------------------------------------------------------------------------

def _load_classify(cfg, ds):
    j = json.loads((D._path(cfg["outdir"]) / "classify" / f"{ds}.json").read_text())
    with np.load(j["arrays"]) as z:
        arrays = {k: z[k] for k in z.files}
    return j, arrays


def _train_metrics(cfg, ds):
    out = {}
    for size in cfg["recon_sizes"]:
        rows = []
        for seed in cfg["train"]["seeds"]:
            p = D._path(cfg["outdir"]) / "train" / f"{ds}__s{size}__seed{seed}.json"
            if p.exists():
                rows.append(json.loads(p.read_text())["metrics"])
        if rows:
            out[str(size)] = {
                "sample_auc": [r["sample"]["auc"] for r in rows], "sample_acc": [r["sample"]["acc"] for r in rows],
                "full_auc": [r["test_full"]["auc"] for r in rows], "full_acc": [r["test_full"]["acc"] for r in rows],
                "sample_auc_mean": float(np.mean([r["sample"]["auc"] for r in rows])),
                "full_auc_mean": float(np.mean([r["test_full"]["auc"] for r in rows])),
                "full_acc_mean": float(np.mean([r["test_full"]["acc"] for r in rows])),
                "n_seeds": len(rows)}
    return out


def evaluate_dataset(cfg: dict, ds: str, out, log=print) -> None:
    ecfg = cfg["evaluate"]
    meta, arrays = _load_classify(cfg, ds)
    task = meta["task"]
    y = arrays.pop("y_true")
    in_b = ds not in cfg["arm_b_exclude"]
    primary = cfg["vlm"]["primary"]
    models = list(cfg["vlm"]["models"])
    grid = list(meta["curve"]["n"])
    seeds = list(meta["curve"]["seeds"])
    pseeds = list(cfg["classify"]["permute"]["seeds"])

    auc, acc, flags = {}, {}, {}
    for k, S in arrays.items():
        auc[k], flags[k] = safe_auc(y, S, task)
        acc[k] = getACC(y, S, task)

    def seed_mean(prefix, n, keys=seeds):
        return float(np.mean([auc[f"{prefix}__n{n}__seed{s}"] for s in keys]))

    result = {"dataset": ds, "task": task, "n_test": int(len(y)), "arm_b": in_b, "grid": grid, "seeds": seeds,
              "auc": {"C": {str(n): {"seeds": [auc[f"C__n{n}__seed{s}"] for s in seeds], "mean": seed_mean("C", n)} for n in grid},
                      "P": {str(n): {"seeds": [auc[f"P__n{n}__seed{s}"] for s in seeds], "mean": seed_mean("P", n)} for n in grid},
                      "Cperm": {str(n): {"seeds": [auc[f"Cperm__n{n}__seed{s}"] for s in seeds], "mean": seed_mean("Cperm", n)} for n in grid},
                      "E": _train_metrics(cfg, ds)},
              "acc": {"C": {str(n): float(np.mean([acc[f"C__n{n}__seed{s}"] for s in seeds])) for n in grid},
                      "P": {str(n): float(np.mean([acc[f"P__n{n}__seed{s}"] for s in seeds])) for n in grid}},
              "auc_classes_missing_in_sample": bool(any(flags.values())),
              "completeness": meta["completeness"]}
    if in_b:
        result["auc"]["A"] = auc["A"]
        result["acc"]["A"] = acc["A"]
        result["auc"]["B"] = {m: auc[f"B__{m}"] for m in models}
        result["acc"]["B"] = {m: acc[f"B__{m}"] for m in models}
        result["auc"]["Bperm"] = {m: [auc[f"Bperm__{m}__seed{s}"] for s in pseeds] for m in models}
        result["perm_drop"] = {"B": {m: auc[f"B__{m}"] - float(np.mean(result["auc"]["Bperm"][m])) for m in models},
                               "C": {str(n): seed_mean("C", n) - seed_mean("Cperm", n) for n in grid}}
        label, pos = crossing(auc[f"B__{primary}"], {n: seed_mean("P", n) for n in grid}, grid)
        result["n_b"] = {"label": label, "position": pos, "value": label_value(label)}
    else:
        result["perm_drop"] = {"C": {str(n): seed_mean("C", n) - seed_mean("Cperm", n) for n in grid}}

    # the paired bootstrap: the predictions are fixed, so every quantity is a function of the resample
    B, ci = int(ecfg["bootstrap"]), float(ecfg["ci"])
    rng = np.random.default_rng(int(cfg["sample"]["seed"]) * 1000 + 7)
    keys = [f"{a}__n{n}__seed{s}" for a in ("C", "P") for n in grid for s in seeds]
    if in_b:
        keys += ["A"] + [f"B__{m}" for m in models]
    boot = {k: np.empty(B) for k in keys}
    positions = np.empty(B, dtype=int)
    for b in range(B):
        idx = rng.integers(0, len(y), len(y))
        yb = y[idx]
        for k in keys:
            boot[k][b] = macro_auc(yb, arrays[k][idx], task, present_only=True)
        if in_b:
            pb = {n: np.mean([boot[f"P__n{n}__seed{s}"][b] for s in seeds]) for n in grid}
            positions[b] = crossing(boot[f"B__{primary}"][b], pb, grid)[1]
        if (b + 1) % 1000 == 0:
            log(f"{ds}: bootstrap {b + 1}/{B}", flush=True)
    lo, hi = 100 * (1 - ci) / 2, 100 * (1 + ci) / 2

    def pct(v):
        return [float(x) for x in np.nanpercentile(v, [lo, 50, hi])]

    cm = {n: np.mean([boot[f"C__n{n}__seed{s}"] for s in seeds], axis=0) for n in grid}
    pm = {n: np.mean([boot[f"P__n{n}__seed{s}"] for s in seeds], axis=0) for n in grid}
    bs = {"B": B, "ci": ci, "C": {str(n): pct(cm[n]) for n in grid}, "P": {str(n): pct(pm[n]) for n in grid},
          "diff_C_minus_P": {str(n): pct(cm[n] - pm[n]) for n in grid}}
    if in_b:
        bs["A"] = pct(boot["A"])
        bs["B"] = {m: pct(boot[f"B__{m}"]) for m in models}
        bs["diff_B_minus_A"] = pct(boot[f"B__{primary}"] - boot["A"])
        counts = np.bincount(positions, minlength=len(grid) + 1)
        plo, phi = (int(x) for x in np.percentile(positions, [lo, hi], method="nearest"))
        result["n_b"].update({"ci_labels": [position_label(plo, grid), position_label(phi, grid)],
                              "ci_positions": [plo, phi],
                              "distribution": {position_label(j, grid): int(c) for j, c in enumerate(counts)}})
    result["bootstrap"] = bs

    with Run("evaluate", dict(dataset=ds, bootstrap=B, ci=ci, primary=primary, grid=grid, seeds=seeds),
             seeds=[int(cfg["sample"]["seed"]) * 1000 + 7]) as run:
        run.write(out, result)
    log(f"wrote {out}" + (f": AUC(B)={auc[f'B__{primary}']:.3f} n_B={result['n_b']['label']}" if in_b else ""))


# ---- across datasets --------------------------------------------------------------------------------

def summary(cfg: dict, out, log=print) -> None:
    primary = cfg["vlm"]["primary"]
    models = list(cfg["vlm"]["models"])
    mcfg = cfg["vlm"]["models"]
    alpha = float(cfg["ladder"].get("alpha", 0.05))
    per = {ds: json.loads((D._path(cfg["outdir"]) / "evaluate" / f"{ds}.json").read_text()) for ds in cfg["datasets"]}
    n50 = str(cfg["curve"]["n"][0])
    flagged = {ds: sorted(k for k, v in r["completeness"].items() if v.get("flagged")) for ds, r in per.items()}
    # H1: n_B and C vs P at the first grid point, over every dataset (12) not flagged
    h1_ds = [ds for ds in cfg["datasets"] if not flagged[ds]]
    wins1 = [ds for ds in h1_ds if per[ds]["auc"]["C"][n50]["mean"] > per[ds]["auc"]["P"][n50]["mean"]]
    b_ds = [ds for ds in h1_ds if per[ds]["arm_b"]]
    nb_values = {ds: per[ds]["n_b"]["value"] for ds in b_ds}
    med = float(np.median(list(nb_values.values()))) if nb_values else float("nan")
    p1 = sign_test(len(wins1), len(h1_ds))
    h1 = {"datasets": h1_ds, "n": len(h1_ds), "wins_C_gt_P_at_first_n": wins1, "wins": len(wins1), "p": p1,
          "n_b": {ds: per[ds]["n_b"] for ds in b_ds}, "median_n_b": med,
          "median_n_b_label": (">n_max" if math.isinf(med) else f"{med:g}"),
          "rule": f"median n_B >= 100 and AUC(C) > AUC(P) at n = {n50} with one-sided sign test p < 0.05 (10 of 12 at the nominal count)",
          "supported": bool(med >= 100 and p1 < 0.05)}
    # H2: B vs A over the arm-B datasets (11) not flagged
    h2_ds = [ds for ds in cfg["datasets"] if per[ds]["arm_b"] and not flagged[ds]]
    wins2 = [ds for ds in h2_ds if per[ds]["auc"]["B"][primary] > per[ds]["auc"]["A"]]
    p2 = sign_test(len(wins2), len(h2_ds))
    drops_b = {ds: per[ds]["perm_drop"]["B"][primary] for ds in h2_ds}
    drops_c = {ds: per[ds]["perm_drop"]["C"][n50] for ds in h2_ds}
    h2 = {"datasets": h2_ds, "n": len(h2_ds), "wins_B_gt_A": wins2, "wins": len(wins2), "p": p2,
          "diff_B_minus_A": {ds: per[ds]["bootstrap"]["diff_B_minus_A"] for ds in h2_ds},
          "perm_drop_B": drops_b, "perm_drop_C_at_first_n": drops_c,
          "controls_lose": bool(all(v > 0 for v in drops_b.values()) and all(v > 0 for v in drops_c.values())),
          "rule": "AUC(B) > AUC(A) with one-sided sign test p < 0.05 (9 of 11 at the nominal count), and both B and C lose AUC under the permutation controls",
          "supported": bool(p2 < 0.05 and all(v > 0 for v in drops_b.values()) and all(v > 0 for v in drops_c.values()))}
    # H3: the ladder over every arm-B dataset with all four models present
    h3_ds = [ds for ds in cfg["datasets"] if per[ds]["arm_b"] and not any(k.endswith("__test") and v.get("flagged") for k, v in per[ds]["completeness"].items())]
    Y = np.array([[per[ds]["auc"]["B"][m] for m in models] for ds in h3_ds])
    h3 = {"datasets": h3_ds, "table": {ds: dict(zip(models, row.tolist())) for ds, row in zip(h3_ds, Y)},
          "centred": {ds: dict(zip(models, (row - row.mean()).tolist())) for ds, row in zip(h3_ds, Y)}}
    if len(h3_ds) >= 3:
        h3["anova"] = ladder_anova(Y, models, mcfg, alpha)
        h3["friedman"] = friedman_nemenyi(Y, models, alpha) if cfg["ladder"].get("friedman", True) else None
        h3["supported"] = h3["anova"]["supported"]
        h3["agree"] = None if not h3["friedman"] else bool((h3["friedman"]["p"] < alpha) == (h3["anova"]["anova"]["model"]["p"] < alpha))
    with Run("summary", dict(primary=primary, models=models, alpha=alpha, datasets=cfg["datasets"])) as run:
        run.write(out, {"flagged": flagged, "H1": h1, "H2": h2, "H3": h3})
    log(f"H1 {'supported' if h1['supported'] else 'not supported'} (wins {h1['wins']}/{h1['n']}, median n_B {h1['median_n_b_label']}); "
        f"H2 {'supported' if h2['supported'] else 'not supported'} (wins {h2['wins']}/{h2['n']}); "
        f"H3 {'supported' if h3.get('supported') else 'not supported'}")
