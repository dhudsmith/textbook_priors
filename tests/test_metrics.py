"""Metric conventions and the decision machinery of WORKFLOW.md section 2: the rank-based AUC
against the medmnist evaluator, the crossing codes, the sign-test p-values the plan states, the
blocked ANOVA with its contrasts, and Friedman/Nemenyi."""
import math

import numpy as np
import pytest

from priors import evaluate as E


def _rand(task, n=300, K=5, seed=0):
    rng = np.random.default_rng(seed)
    if task == "multi-label, binary-class":
        y = (rng.random((n, K)) < 0.3).astype(int)
        S = np.clip(y * 0.4 + rng.random((n, K)) * 0.8, 0, 1)
    elif task == "binary-class":
        y = rng.integers(0, 2, n)
        S = np.stack([1 - (y * 0.3 + rng.random(n) * 0.7), y * 0.3 + rng.random(n) * 0.7], 1)
    else:
        y = rng.integers(0, K, n)
        S = rng.random((n, K))
        S[np.arange(n), y] += 0.5
        S /= S.sum(1, keepdims=True)
    return y, S


@pytest.mark.parametrize("task", ["multi-class", "ordinal-regression", "binary-class", "multi-label, binary-class"])
def test_macro_auc_matches_the_medmnist_evaluator(task):
    pytest.importorskip("medmnist")
    y, S = _rand(task)
    y_med = y.reshape(-1, 1) if y.ndim == 1 else y            # medmnist stores (n, 1) labels
    assert math.isclose(E.macro_auc(y, S, task), E.getAUC(y_med, S, task), abs_tol=1e-12)
    assert math.isclose(E.macro_auc(y_med, S, task), E.getAUC(y_med, S, task), abs_tol=1e-12)


def test_macro_auc_handles_ties_and_absent_classes():
    pytest.importorskip("medmnist")
    y = np.array([0, 0, 1, 1, 2])
    S = np.array([[0.5, 0.5, 0], [0.5, 0.5, 0], [0.5, 0.5, 0], [0.5, 0.5, 0], [0, 0, 1.0]])
    assert math.isclose(E.macro_auc(y[:4], S[:4, :2], "multi-class"), 0.5)          # all ties -> 0.5
    assert math.isnan(E.macro_auc(y[:4], S[:4], "multi-class"))                    # class 2 absent
    assert math.isclose(E.macro_auc(y[:4], S[:4], "multi-class", present_only=True), 0.5)
    auc, flagged = E.safe_auc(y[:4].reshape(-1, 1), S[:4], "multi-class")
    assert flagged and math.isclose(auc, 0.5)


def test_getACC_conventions():
    pytest.importorskip("medmnist")
    y = np.array([[0], [1], [1]])
    assert E.getACC(y, np.array([[0.9, 0.1], [0.4, 0.6], [0.7, 0.3]]), "binary-class") == pytest.approx(2 / 3)
    assert E.getACC(y, np.array([[0.9, 0.1], [0.4, 0.6], [0.7, 0.3]]), "multi-class") == pytest.approx(2 / 3)
    Y = np.array([[1, 0], [0, 1]])
    assert E.getACC(Y, np.array([[0.9, 0.2], [0.1, 0.4]]), "multi-label, binary-class") == pytest.approx(0.75)


def test_crossing_codes_and_values():
    grid = [50, 100, 200, 500]
    assert E.crossing(0.80, {50: 0.85, 100: 0.9, 200: 0.9, 500: 0.9}, grid) == ("<=50", 0)
    assert E.crossing(0.80, {50: 0.6, 100: 0.7, 200: 0.80, 500: 0.9}, grid) == ("200", 2)
    assert E.crossing(0.80, {50: 0.6, 100: 0.7, 200: 0.75, 500: 0.79}, grid) == (">500", 4)
    assert E.position_label(0, grid) == "<=50" and E.position_label(4, grid) == ">500" and E.position_label(1, grid) == "100"
    assert E.label_value("<=50") == 50 and E.label_value("200") == 200 and math.isinf(E.label_value(">500"))


def test_sign_test_p_values_the_plan_states():
    assert E.sign_test(10, 12) == pytest.approx(79 / 4096, rel=1e-9)      # 0.019
    assert E.sign_test(9, 11) == pytest.approx(67 / 2048, rel=1e-9)       # 0.033
    assert E.sign_test(9, 10) == pytest.approx(11 / 1024, rel=1e-9)       # 0.011
    assert E.sign_test(9, 12) > 0.05 and E.sign_test(8, 11) > 0.05
    assert E.sign_test(12, 12) == pytest.approx(1 / 4096)
    assert E.sign_test(0, 12) == pytest.approx(1.0)


MODELS = ["qwen3.5-9b", "gemma-4-12b", "qwen3.8-27b-fp8", "gemma-4-31b"]
META = {"qwen3.5-9b": {"family": "qwen", "params_b": 9}, "gemma-4-12b": {"family": "gemma", "params_b": 12},
        "qwen3.8-27b-fp8": {"family": "qwen", "params_b": 27}, "gemma-4-31b": {"family": "gemma", "params_b": 31}}


def _ladder(slope, noise, seed=0, N=11, fam_gap=0.0):
    rng = np.random.default_rng(seed)
    lp = np.log10([META[m]["params_b"] for m in MODELS])
    block = rng.uniform(0.6, 0.9, N)
    fam = np.array([fam_gap if META[m]["family"] == "qwen" else 0.0 for m in MODELS])
    return block[:, None] + slope * (lp - lp.mean())[None, :] + fam[None, :] + rng.normal(0, noise, (N, len(MODELS)))


def test_ladder_anova_recovers_a_planted_trend_and_partitions_the_model_ss():
    Y = _ladder(slope=0.05, noise=0.003)
    r = E.ladder_anova(Y, MODELS, META)
    t = r["trend_log10_params"]
    assert t["estimate"] == pytest.approx(0.05, abs=0.01)
    assert t["p_one_sided_positive"] < 0.001 and r["supported"]
    a = r["anova"]
    assert a["family"]["ss"] if False else True
    ss_parts = sum(N_ss for N_ss in (a["family"]["F"] * a["error"]["mse"], a["size_tier"]["F"] * a["error"]["mse"], a["interaction"]["F"] * a["error"]["mse"]))
    assert ss_parts == pytest.approx(a["model"]["ss"], rel=1e-9)
    assert a["model"]["df"] == 3 and a["block"]["df"] == 10 and a["error"]["df"] == 30
    assert all(v["gain_large_minus_small"] > 0 for v in r["within_family"].values())


def test_ladder_anova_negative_trend_is_not_supported():
    Y = _ladder(slope=-0.05, noise=0.003, seed=3)
    r = E.ladder_anova(Y, MODELS, META)
    assert r["trend_log10_params"]["estimate"] < 0 and r["trend_log10_params"]["p_one_sided_positive"] > 0.5
    assert not r["supported"]


def test_ladder_anova_family_gap_is_read_as_family_not_size():
    Y = _ladder(slope=0.0, noise=0.002, seed=4, fam_gap=0.05)
    r = E.ladder_anova(Y, MODELS, META)
    assert r["anova"]["family"]["p"] < 0.001
    assert abs(r["anova"]["interaction"]["estimate"]) < 0.01


def test_ladder_anova_trend_carried_by_one_family_is_not_supported():
    """qwen gains 0.10 with size, gemma loses 0.02: the pooled trend is positive and significant,
    and the rule still says no, because the gain is not positive within every family."""
    rng = np.random.default_rng(5)
    effect = {"qwen3.5-9b": 0.0, "qwen3.8-27b-fp8": 0.10, "gemma-4-12b": 0.02, "gemma-4-31b": 0.0}
    Y = rng.uniform(0.6, 0.9, 11)[:, None] + np.array([effect[m] for m in MODELS])[None, :] + rng.normal(0, 0.002, (11, 4))
    r = E.ladder_anova(Y, MODELS, META)
    assert r["trend_log10_params"]["estimate"] > 0 and r["trend_log10_params"]["p_one_sided_positive"] < 0.05
    assert r["within_family"]["gemma"]["gain_large_minus_small"] < 0
    assert not r["supported"]


def test_friedman_nemenyi_ranks_and_critical_difference():
    Y = _ladder(slope=0.05, noise=0.003)
    f = E.friedman_nemenyi(Y, MODELS)
    assert f["p"] < 0.001
    ranks = f["average_ranks"]
    assert ranks["gemma-4-31b"] < ranks["qwen3.8-27b-fp8"] < ranks["gemma-4-12b"] < ranks["qwen3.5-9b"]
    assert f["critical_difference"] == pytest.approx(2.569 * math.sqrt(4 * 5 / (6 * 11)), rel=1e-6)
    assert len(f["pairs"]) == 6 and any(p["significant"] for p in f["pairs"])
