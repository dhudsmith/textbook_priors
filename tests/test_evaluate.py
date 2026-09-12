"""The metric and the tests the hypotheses are decided by.

The AUC here is a rank formula rather than a call into `medmnist`, because a 10,000-replicate
paired bootstrap over fifty arms cannot afford ten thousand calls into anything. The first test is
therefore the load-bearing one: the fast version and the package's own evaluator must agree
exactly, on both task types, on scores that tie and scores that do not.
"""
import numpy as np
import pytest

from priors import evaluate as metrics

from .conftest import RUN_DATASETS


@pytest.fixture
def multiclass():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 4, size=200)
    scores = rng.random((200, 4))
    scores[np.arange(200), y] += 0.7
    return y, scores


def test_the_fast_auc_equals_the_package_evaluator(evaluator, multiclass):
    y, scores = multiclass
    assert metrics.auc(y, scores, "multi-class", 4) == pytest.approx(
        evaluator.getAUC(y, scores, "multi-class"), abs=1e-12)


def test_it_agrees_on_coarse_tied_scores_too(evaluator):
    """Arm B's scores are negative mean absolute differences over a handful of coarse levels, so
    they tie constantly; average ranks are what makes the rank form exact rather than approximate."""
    rng = np.random.default_rng(1)
    y = rng.integers(0, 3, size=120)
    scores = np.round(rng.random((120, 3)) * 4) / 4          # only five distinct values
    assert metrics.auc(y, scores, "multi-class", 3) == pytest.approx(
        evaluator.getAUC(y, scores, "multi-class"), abs=1e-12)


def test_it_agrees_on_a_binary_task_and_reads_the_positive_column(evaluator):
    rng = np.random.default_rng(2)
    y = rng.integers(0, 2, size=150)
    p = rng.random(150) * 0.6 + 0.2 * y
    scores = np.stack([1 - p, p], axis=1)
    assert metrics.auc(y, scores, "binary-class", 2) == pytest.approx(
        evaluator.getAUC(y, scores, "binary-class"), abs=1e-12)


def test_a_class_with_no_positives_is_undefined_rather_than_half():
    """It happens in bootstrap replicates of a thin class - dermamnist has five vascular lesions in
    the whole test sample - and calling it 0.5 would quietly drag the macro average toward chance."""
    y = np.array([0, 0, 1, 1])
    per_class = metrics.rank_auc(y, np.random.default_rng(0).random((4, 3)), 3)
    assert np.isnan(per_class[2])
    assert not np.isnan(per_class[0]) and not np.isnan(per_class[1])
    assert np.isfinite(metrics.reduce_auc(per_class, "multi-class")), "the defined classes still average"


def test_a_perfect_and_a_reversed_ranking_are_one_and_zero():
    y = np.array([0, 0, 1, 1])
    perfect = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0], [0.0, 1.0]])
    assert metrics.auc(y, perfect, "multi-class", 2) == 1.0
    assert metrics.auc(y, perfect[:, ::-1], "multi-class", 2) == 0.0


# ---- the bootstrap, which has to be paired ------------------------------------------------------

def test_every_arm_sees_the_same_resample():
    """If two arms were resampled independently, the interval on their difference would be the sum
    of two noises instead of the noise that does not cancel, and every comparison would be wrong."""
    rng = np.random.default_rng(0)
    y = rng.integers(0, 2, size=80)
    scores = rng.random((80, 2))
    keys, reps = metrics.bootstrap_aucs(y, {"one": scores, "two": scores.copy()},
                                        "multi-class", 2, n_boot=50, seed=0)
    assert keys == ["one", "two"]
    assert np.allclose(reps[:, 0], reps[:, 1]), "identical arms must differ by exactly zero"


def test_the_bootstrap_brackets_the_point_estimate():
    rng = np.random.default_rng(0)
    y = rng.integers(0, 3, size=150)
    scores = rng.random((150, 3)); scores[np.arange(150), y] += 0.5
    point = metrics.auc(y, scores, "multi-class", 3)
    _, reps = metrics.bootstrap_aucs(y, {"arm": scores}, "multi-class", 3, n_boot=200, seed=0)
    ci = metrics.interval(reps[:, 0], 0.95)
    assert ci["lo"] <= point <= ci["hi"]


# ---- n_B, the headline number -------------------------------------------------------------------

def test_the_crossing_is_the_first_grid_point_that_reaches_the_target():
    grid = [50, 100, 200]
    assert metrics.crossing({50: 0.6, 100: 0.7, 200: 0.8}, 0.65, grid) == 100
    assert metrics.crossing({50: 0.6, 100: 0.7, 200: 0.8}, 0.70, grid) == 100, "reaching counts"


def test_already_above_and_never_reaching_are_coded_not_clipped():
    """`<=50` and `>2000` are different facts from a number. A study that printed 50 for both would
    be claiming something it did not measure (WORKFLOW.md section 2)."""
    grid = [50, 100, 200]
    below = metrics.crossing({50: 0.9, 100: 0.9, 200: 0.9}, 0.5, grid)
    above = metrics.crossing({50: 0.1, 100: 0.2, 200: 0.3}, 0.9, grid)
    assert below == -np.inf and metrics.code_crossing(below, grid) == "<=50"
    assert above == np.inf and metrics.code_crossing(above, grid) == ">200"
    assert metrics.code_crossing(100.0, grid) == "100"


# ---- the across-dataset tests --------------------------------------------------------------------

def test_the_sign_test_is_the_one_the_plan_quotes():
    """WORKFLOW.md section 2 fixes the reading: six of six is p = 0.016, five of six is p = 0.11."""
    assert metrics.sign_test(6, 6) == pytest.approx(0.0156, abs=5e-4)
    assert metrics.sign_test(5, 6) == pytest.approx(0.1094, abs=5e-4)
    assert metrics.sign_test(3, 6) > 0.5


def test_the_friedman_test_runs_over_the_model_ladder(config):
    table = np.array([[0.60, 0.62, 0.65, 0.70]] * len(RUN_DATASETS))
    table += np.linspace(0, 0.02, table.shape[0])[:, None]
    got = metrics.friedman(table)
    assert got["p"] is not None and 0 <= got["p"] <= 1


def test_friedman_says_so_rather_than_failing_on_too_few_models():
    assert metrics.friedman(np.zeros((6, 2)))["p"] is None
