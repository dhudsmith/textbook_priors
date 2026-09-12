"""evaluate: AUC, the paired bootstrap, n_B, and the tests the hypotheses are decided by.

The metric is `medmnist.evaluator.getAUC` — the benchmark's own convention, macro one-vs-rest for a
multi-class task and the positive column for a binary one (WORKFLOW.md section 3). It is used here
through a rank formula rather than by calling the package ten thousand times: the smoke tier holds
the two to equality, and the rank version is what makes a 10,000-replicate paired bootstrap over
fifty arms finish in seconds instead of hours.

Everything is **paired**. Every arm predicts on the same 500 images, so a bootstrap replicate
resamples the images once and recomputes every arm on that same resample. The interval that matters
is therefore the interval on a difference, where the shared noise cancels — which is also why the
thin rare classes of WORKFLOW.md section 3 hurt the absolute AUCs more than the comparisons.
"""
from __future__ import annotations

import numpy as np
from scipy import stats


def rank_auc(labels: np.ndarray, scores: np.ndarray, n_classes: int) -> np.ndarray:
    """One-vs-rest AUC per class, from average ranks (the Mann-Whitney form).

    Ties get average ranks, which is what makes this exact for arm B, whose scores are coarse and
    tie constantly. A class with no positives or no negatives in the sample has no AUC and comes
    back NaN rather than 0.5: it is undefined, not a coin flip.
    """
    ranks = stats.rankdata(scores, axis=0)
    out = np.full(n_classes, np.nan)
    for c in range(n_classes):
        positive = labels == c
        n_pos = int(positive.sum())
        n_neg = len(labels) - n_pos
        if n_pos == 0 or n_neg == 0:
            continue
        out[c] = (ranks[positive, c].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
    return out


def reduce_auc(per_class: np.ndarray, task: str) -> float:
    """The package's convention: the positive column for a binary task, the unweighted mean of the
    one-vs-rest columns otherwise. Unweighted, so a rare class counts as much as a common one."""
    if task == "binary-class":
        return float(per_class[-1])
    return float(np.nanmean(per_class))


def auc(labels: np.ndarray, scores: np.ndarray, task: str, n_classes: int) -> float:
    return reduce_auc(rank_auc(labels, scores, n_classes), task)


def bootstrap_aucs(labels, arm_scores: dict, task: str, n_classes: int, n_boot: int, seed: int):
    """AUC for every arm on every bootstrap replicate of the test images.

    Returns (keys, matrix) with one row per replicate and one column per arm, so any difference
    between two arms is a difference of two columns and its interval is a percentile of that.

    All arms share each replicate: that is what paired means here, and it is the whole reason the
    comparisons are tighter than the absolute numbers.
    """
    keys = sorted(arm_scores)
    stacked = np.concatenate([arm_scores[k] for k in keys], axis=1)   # images x (arms * classes)
    rng = np.random.default_rng(seed)
    n = len(labels)
    out = np.full((n_boot, len(keys)), np.nan)

    for b in range(n_boot):
        idx = rng.integers(0, n, size=n)
        y = labels[idx]
        ranks = stats.rankdata(stacked[idx], axis=0)
        masks = np.stack([(y == c).astype(float) for c in range(n_classes)])     # classes x images
        sums = masks @ ranks                                                     # classes x columns
        counts = masks.sum(axis=1)
        for a, _ in enumerate(keys):
            per_class = np.full(n_classes, np.nan)
            for c in range(n_classes):
                n_pos, n_neg = counts[c], n - counts[c]
                if n_pos == 0 or n_neg == 0:
                    continue
                per_class[c] = (sums[c, a * n_classes + c] - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
            out[b, a] = reduce_auc(per_class, task)
    return keys, out


def interval(values, ci: float = 0.95) -> dict:
    """A percentile interval, and the median beside it."""
    values = np.asarray(values, dtype=float)
    values = values[np.isfinite(values)]
    if len(values) == 0:
        return {"median": None, "lo": None, "hi": None}
    half = (1 - ci) / 2
    return {"median": float(np.median(values)),
            "lo": float(np.quantile(values, half)),
            "hi": float(np.quantile(values, 1 - half))}


# n_B is coded rather than clipped: "already there at the first grid point" and "never gets there"
# are different facts from a number, and averaging them into one would hide both.
BELOW = "<=first"
ABOVE = ">last"


def crossing(curve: dict, target: float, grid) -> float:
    """The smallest grid n whose curve value reaches `target`.

    Returns the n itself, or -inf when the curve is already above at the first point, or +inf when
    it never gets there. Those two are the codes `<=50` and `>2000` of WORKFLOW.md section 2: the
    headline number n_B is "this many labels is what the textbook was worth", and a study that
    printed 50 for both cases would be claiming something it did not measure.
    """
    ordered = sorted(grid)
    if curve[ordered[0]] >= target:
        return -np.inf
    for n in ordered:
        if curve[n] >= target:
            return float(n)
    return np.inf


def code_crossing(value: float, grid) -> str:
    ordered = sorted(grid)
    if value == -np.inf:
        return f"<={ordered[0]}"
    if value == np.inf:
        return f">{ordered[-1]}"
    return str(int(value))


def sign_test(wins: int, n: int) -> float:
    """One-sided exact binomial test that an arm wins more often than chance across datasets.

    With six datasets this is coarse on purpose: 6 of 6 is p = 0.016 and 5 of 6 is p = 0.11, so a
    hypothesis is supported only when it wins everywhere (WORKFLOW.md section 2). The per-dataset
    differences with their intervals are what a reader should look at.
    """
    return float(stats.binomtest(wins, n, 0.5, alternative="greater").pvalue)


def friedman(table: np.ndarray) -> dict:
    """Friedman test over the model ladder: datasets are blocks, models are treatments."""
    if table.shape[0] < 3 or table.shape[1] < 3:
        return {"statistic": None, "p": None, "note": "needs at least three blocks and treatments"}
    statistic, p = stats.friedmanchisquare(*[table[:, j] for j in range(table.shape[1])])
    return {"statistic": float(statistic), "p": float(p)}
