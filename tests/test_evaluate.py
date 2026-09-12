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


@pytest.mark.parametrize("values, expect", [
    ([-np.inf, -np.inf, 100.0], "<=50"),
    ([50.0, 100.0, 200.0], "100"),
    ([np.inf, np.inf, 200.0], ">200"),
    ([-np.inf, np.inf], "<=50"),
])
def test_an_n_b_quantile_mixes_codes_and_numbers_without_producing_nan(values, expect):
    """Caught by the pipeline test before the real run: a bootstrap distribution that contains both
    "already above at the first grid point" and "never reaches" makes an interpolated quantile NaN,
    and NaN is not a crossing. The quantile is taken on the ordinal ranks instead."""
    grid = [50, 100, 200]
    assert metrics.quantile_code(values, 0.5, grid) == expect


def test_the_ordinal_positions_are_the_ones_the_codes_mean():
    grid = [50, 100, 200]
    assert metrics.rank_of(-np.inf, grid) == 0 and metrics.code_of_rank(0, grid) == "<=50"
    assert metrics.rank_of(100.0, grid) == 2 and metrics.code_of_rank(2, grid) == "100"
    assert metrics.rank_of(np.inf, grid) == 4 and metrics.code_of_rank(4, grid) == ">200"


def test_the_h1_median_keeps_the_coded_datasets_in_the_ordering():
    """WORKFLOW.md section 2 asks for the median n_B to be at least 100. Taken over the numeric
    values alone that would silently drop every `<=50` and `>2000` - the two most informative
    outcomes - and let a minority of datasets decide a six-dataset rule. On the ordinal scale a
    `>2000` sits above every grid point and a `<=50` below every one, which is what they mean."""
    grid = [50, 100, 200, 500, 1000, 2000]
    codes = ["<=50", "100", ">2000", "500", ">2000", "50"]
    ranks = [metrics.rank_of(-np.inf if c.startswith("<=") else np.inf if c.startswith(">")
                             else float(c), grid) for c in codes]
    assert ranks == [0, 2, 7, 4, 7, 1]
    assert float(np.median(ranks)) >= metrics.rank_of(100.0, grid), "three of six are at or above 100"


def test_a_decision_threshold_need_not_be_a_grid_point():
    """"Median n_B at least 100" is a round number in a rule, not a crossing, so it cannot be
    looked up like one. On a grid that cannot resolve it, only ">last" qualifies."""
    assert metrics.rank_at_least(100, [50, 100, 200]) == 2
    assert metrics.rank_at_least(100, [20, 50]) == 3, "no grid point reaches it"
    assert metrics.rank_at_least(10, [50, 100]) == 1
    with pytest.raises(ValueError):
        metrics.rank_of(75.0, [50, 100])


# ---- the report's own median, which is not the estimators' -----------------------------------

def test_the_reports_median_is_the_mean_of_the_two_middle_values():
    """An even-length median is the mean of the middle pair.

    Stated as a test because the first version of the literature macros used
    `sorted(v)[len(v) // 2]`, which on six datasets is the fourth smallest: it put 0.115 into a
    sentence whose answer was 0.094, and nothing in the report would have contradicted it."""
    from priors import report
    assert report.median([1, 2, 3, 4]) == 2.5
    assert report.median([3, 1, 4, 2]) == 2.5, "it sorts first"
    assert report.median([1, 2, 3]) == 2
    assert report.median([0.022, 0.062, 0.073, 0.115, 0.130, 0.232]) == (0.073 + 0.115) / 2
