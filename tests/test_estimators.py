"""The arm-B estimator, the permutation controls, the nested stratified subsets and the shared
logistic regression, on fixtures with known answers (WORKFLOW.md section 3)."""
import numpy as np
import pytest

from priors import classify as C
from priors import data as D

BANK = {
    "concepts": [
        {"id": "size", "scale": ["small", "medium", "large"]},
        {"id": "edge", "scale": ["smooth", "jagged"]},
        {"id": "hue", "scale": ["a", "b", "c", "d"]},
    ],
    "classes": {
        "pos": {"fingerprint": {"size": "large", "edge": "jagged", "hue": "any"}},
        "neg": {"fingerprint": {"size": "small", "edge": "smooth", "hue": "a"}},
    },
}
NAMES = ["pos", "neg"]


def test_arm_b_scores_distance_over_committed_and_answered_concepts():
    F = D.fingerprint_matrix(BANK, NAMES)
    X = D.answers_matrix(BANK, [{"size": "large", "edge": "jagged", "hue": "d"},
                               {"size": "medium", "edge": "smooth", "hue": "a"}])
    S = C.arm_b(X, F)
    assert S.shape == (2, 2)
    assert S[0, 0] == 0.0                                    # exact match on the two committed concepts
    assert np.isclose(S[0, 1], -(1.0 + 1.0 + 1.0) / 3)       # size 1.0, edge 1.0, hue |1 - 0| = 1
    assert np.isclose(S[1, 0], -(0.5 + 1.0) / 2)             # hue is `any` for pos: masked
    assert np.isclose(S[1, 1], -(0.5 + 0.0 + 0.0) / 3)
    assert S[1, 1] > S[1, 0]


def test_arm_b_skips_missing_answers_and_scores_no_overlap_worst():
    F = D.fingerprint_matrix(BANK, NAMES)
    X = D.answers_matrix(BANK, [{"size": None, "edge": "jagged", "hue": "b"}, {"size": None, "edge": None, "hue": "b"}])
    S = C.arm_b(X, F)
    assert S[0, 0] == 0.0 and np.isclose(S[0, 1], -(1.0 + 1 / 3) / 2)
    assert S[1, 0] == -1.0 and np.isclose(S[1, 1], -1 / 3)


def test_short_scales_weigh_more():
    """An adjacent miss costs 1.0 on a two-level scale and 1/3 on a four-level one."""
    F = D.fingerprint_matrix(BANK, ["neg"])
    x_edge = D.answers_matrix(BANK, [{"size": "small", "edge": "jagged", "hue": "a"}])
    x_hue = D.answers_matrix(BANK, [{"size": "small", "edge": "smooth", "hue": "b"}])
    assert C.arm_b(x_edge, F)[0, 0] < C.arm_b(x_hue, F)[0, 0]


def test_permute_rows_is_seeded_and_never_identity():
    F = np.arange(12.0).reshape(4, 3)
    P1, P2 = C.permute_rows(F, 0), C.permute_rows(F, 0)
    assert np.array_equal(P1, P2) and not np.array_equal(P1, F)
    assert sorted(P1[:, 0].tolist()) == sorted(F[:, 0].tolist())
    for s in range(20):
        assert not np.array_equal(C.permute_rows(F, s), F)


def test_permute_columns_keeps_each_marginal():
    rng = np.random.default_rng(0)
    X = rng.normal(size=(50, 4))
    X[3, 1] = np.nan
    Xp = C.permute_columns(X, 1)
    for j in range(4):
        assert sorted(np.nan_to_num(X[:, j], nan=-9).tolist()) == sorted(np.nan_to_num(Xp[:, j], nan=-9).tolist())
    assert not np.array_equal(np.nan_to_num(X), np.nan_to_num(Xp))
    assert np.array_equal(np.nan_to_num(C.permute_columns(X, 1)), np.nan_to_num(Xp))


def test_nested_subsets_are_nested_stratified_and_seeded():
    y = np.repeat([0, 1, 2], [120, 60, 20])
    sub = C.nested_subsets(y, "multi-class", [3, 10, 50, 200, 500], seed=0)
    assert list(sub) == [3, 10, 50, 200]                     # 500 > pool: dropped, not repeated
    assert set(sub[3].tolist()) <= set(sub[10].tolist()) <= set(sub[50].tolist()) <= set(sub[200].tolist())
    assert sorted(y[sub[3]].tolist()) == [0, 1, 2]           # the floor: one of each class
    counts = np.bincount(y[sub[50]], minlength=3)
    assert abs(counts[0] - 30) <= 1 and abs(counts[1] - 15) <= 1 and abs(counts[2] - 5) <= 1
    assert len(set(sub[200].tolist())) == 200
    assert np.array_equal(sub[50], C.nested_subsets(y, "multi-class", [50], 0)[50])
    assert not np.array_equal(sub[50], C.nested_subsets(y, "multi-class", [50], 1)[50])


def test_multilabel_strata_are_any_finding_versus_none():
    Y = np.zeros((6, 14), int)
    Y[1, 3] = Y[4, 0] = Y[4, 9] = 1
    assert C.strata(Y, "multi-label, binary-class").tolist() == [0, 1, 0, 0, 1, 0]
    sub = C.nested_subsets(Y, "multi-label, binary-class", [2, 6], 0)
    assert sorted(C.strata(Y[sub[2]], "multi-label, binary-class").tolist()) == [0, 1]


def test_impute_adds_informative_indicators_only():
    Xf = np.array([[0.0, 1.0], [np.nan, 1.0], [1.0, 1.0]])
    Xa = np.array([[np.nan, np.nan]])
    Zf, Za, info = C.impute(Xf, Xa)
    assert info["indicators"] == 1 and Zf.shape == (3, 3) and Za.shape == (1, 3)
    assert Zf[1, 0] == 0.5 and Za[0, 0] == 0.5 and Za[0, 1] == 1.0     # medians
    assert Zf[:, 2].tolist() == [0.0, 1.0, 0.0] and Za[0, 2] == 1.0
    Zf2, Za2, info2 = C.impute(np.array([[0.0, 1.0], [1.0, 0.0]]), Xa)
    assert info2["indicators"] == 0 and Zf2.shape == (2, 2)


def test_standardise_zeroes_constant_columns():
    Zf, Za = C.standardise(np.array([[1.0, 5.0], [3.0, 5.0]]), np.array([[2.0, 5.0]]))
    assert np.allclose(Zf[:, 0], [-1, 1]) and np.allclose(Zf[:, 1], 0) and np.allclose(Za, [[0, 0]])


def test_fit_predict_gives_absent_classes_zero_and_learns_separable_data(cfg):
    rng = np.random.default_rng(0)
    ccfg = cfg["classify"]
    Xtr = np.vstack([rng.normal(-2, 0.5, (30, 2)), rng.normal(2, 0.5, (30, 2))])
    ytr = np.repeat([0, 2], 30)                              # class 1 absent from the subset
    Xte = np.vstack([rng.normal(-2, 0.5, (20, 2)), rng.normal(2, 0.5, (20, 2))])
    P, meta = C.fit_predict(Xtr, ytr, Xte, task="multi-class", K=3, ccfg=ccfg, seed=0)
    assert P.shape == (40, 3) and np.allclose(P[:, 1], 0) and np.allclose(P.sum(1), 1)
    assert (P[:20, 0] > 0.5).all() and (P[20:, 2] > 0.5).all()
    assert meta["lambda"] in ccfg["l2_grid"] and meta["folds"] == 5 and meta["classes_present"] == 2


def test_fit_predict_without_cv_uses_the_default_strength(cfg):
    rng = np.random.default_rng(0)
    Xtr = rng.normal(size=(4, 3))
    ytr = np.array([0, 0, 0, 1])                             # a class of one: no CV possible
    P, meta = C.fit_predict(Xtr, ytr, rng.normal(size=(2, 3)), task="binary-class", K=2, ccfg=cfg["classify"], seed=0)
    assert meta["folds"] == 1 and meta["lambda"] == float(cfg["classify"]["l2_default"]) and P.shape == (2, 2)


def test_fit_predict_multilabel_constant_when_a_finding_has_no_positives(cfg):
    rng = np.random.default_rng(0)
    Xtr = rng.normal(size=(40, 3))
    Y = np.zeros((40, 3), int)
    Y[:, 0] = (Xtr[:, 0] > 0).astype(int)                    # learnable finding
    Y[:, 2] = 1                                              # all positive: constant one
    P, meta = C.fit_predict(Xtr, Y, Xtr, task="multi-label, binary-class", K=3, ccfg=cfg["classify"], seed=0)
    assert P.shape == (40, 3)
    assert np.allclose(P[:, 1], 0) and np.allclose(P[:, 2], 1)
    assert ((P[:, 0] > 0.5) == (Y[:, 0] == 1)).mean() > 0.9
    assert meta["lambda"][1] is None and meta["lambda"][2] is None and meta["lambda"][0] in cfg["classify"]["l2_grid"]
