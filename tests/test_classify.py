"""The estimators, on fixtures small enough to check by hand.

This is the tier WORKFLOW.md section 6 calls "the arm-B estimator on a fixture", and it exists
because arm B is the project's only label-free predictor: if its arithmetic is wrong, H1's headline
number and H2's comparison are both wrong in a way no downstream stage can see. The other checks
here guard the three decisions the estimators rest on - equal spacing, imputation with a flag, and
nested class-floored subsets.
"""
import numpy as np
import pytest

from priors import classify

CONCEPTS = [
    {"id": "opacity", "scale": ["absent", "mild", "marked"]},          # 0, 0.5, 1
    {"id": "edge", "scale": ["sharp", "blurred"]},                     # 0, 1
]


def rows(*answers):
    return [{"answers": dict(a)} for a in answers]


def test_a_scale_maps_to_equally_spaced_values():
    assert classify.level_values(["a", "b", "c"]) == {"a": 0.0, "b": 0.5, "c": 1.0}
    assert classify.level_values(["a", "b"]) == {"a": 0.0, "b": 1.0}


def test_equal_spacing_weights_a_short_scale_more_than_a_long_one():
    """Stated in WORKFLOW.md section 3 as a consequence of the mapping: an adjacent miss costs 1.0
    on a two-level scale and 0.25 on a five-level one. Pinned so nobody reads a per-concept
    contribution as an importance."""
    two, five = classify.level_values(["a", "b"]), classify.level_values(list("abcde"))
    assert two["b"] - two["a"] == 1.0
    assert five["b"] - five["a"] == 0.25


def test_an_unanswered_concept_is_nan_not_a_value():
    m = classify.concept_matrix(rows([("opacity", "mild")], [("edge", "blurred")]), CONCEPTS)
    assert np.allclose(m[0, 0], 0.5) and np.isnan(m[0, 1])
    assert np.isnan(m[1, 0]) and np.allclose(m[1, 1], 1.0)


def test_a_fingerprint_masks_the_concepts_it_does_not_commit_to():
    fp = classify.fingerprint_matrix(
        ["sick", "well"],
        {"sick": {"fingerprint": {"opacity": "marked", "edge": "any"}},
         "well": {"fingerprint": {"opacity": "absent", "edge": "sharp"}}},
        CONCEPTS)
    assert np.allclose(fp[0, 0], 1.0) and np.isnan(fp[0, 1]), "`any` is a mask, not a middle value"
    assert np.allclose(fp[1], [0.0, 0.0])


# ---- arm B, the label-free predictor ----------------------------------------------------------

def test_arm_b_is_the_negative_mean_absolute_difference_over_the_overlap():
    images = np.array([[1.0, 1.0],          # marked, blurred
                       [0.0, 0.0],          # absent, sharp
                       [0.5, np.nan]])      # mild, unanswered
    fingerprints = np.array([[1.0, np.nan],  # sick: commits to opacity only
                             [0.0, 0.0]])    # well: commits to both
    s = classify.arm_b_scores(images, fingerprints)
    assert np.allclose(s[0], [-0.0, -1.0]), "a perfect match on the one committed concept"
    assert np.allclose(s[1], [-1.0, -0.0])
    # The image answered only opacity, so the `well` class is scored on opacity alone too.
    assert np.allclose(s[2], [-0.5, -0.5])


def test_arm_b_scores_a_class_with_no_overlap_at_the_floor():
    """Not evidence against the class - there is simply nothing to say for it - but a NaN would
    make the AUC undefined rather than uninformative."""
    s = classify.arm_b_scores(np.array([[np.nan, 0.3]]), np.array([[0.4, np.nan]]))
    assert s.shape == (1, 1) and s[0, 0] == -1.0


def test_arm_b_prefers_the_class_whose_fingerprint_is_nearer():
    images = np.array([[0.9, 0.8]])
    fingerprints = np.array([[1.0, 1.0], [0.0, 0.0]])
    s = classify.arm_b_scores(images, fingerprints)
    assert s[0, 0] > s[0, 1]


def test_the_permutation_control_moves_the_fingerprints_off_their_classes():
    fp = np.array([[0.0, 0.0], [1.0, 1.0], [0.5, 0.5]])
    permuted = classify.permute_fingerprints(fp, seed=0)
    assert sorted(permuted.flatten().tolist()) == sorted(fp.flatten().tolist()), "same rows"
    assert not np.array_equal(permuted, fp), "attached to different classes"


def test_the_concept_control_keeps_each_column_and_destroys_the_pairing():
    x = np.arange(12, dtype=float).reshape(6, 2)
    permuted = classify.permute_columns(x, seed=0)
    for j in range(x.shape[1]):
        assert sorted(permuted[:, j]) == sorted(x[:, j]), "the marginal survives"
    assert not np.array_equal(permuted, x)


# ---- imputation ---------------------------------------------------------------------------------

def test_a_missing_answer_becomes_the_pool_median_and_is_flagged():
    pool = np.array([[0.0, 0.0], [1.0, 1.0], [0.5, np.nan]])
    medians = classify.pool_medians(pool)
    assert np.allclose(medians, [0.5, 0.5])
    filled, flags = classify.impute(pool, medians)
    assert np.allclose(filled[2], [0.5, 0.5])
    assert flags.shape == (3, 1), "one indicator, for the only concept with a missing answer"
    assert np.allclose(flags[:, 0], [0, 0, 1])


def test_a_concept_nobody_ever_missed_contributes_no_indicator():
    filled, flags = classify.impute(np.array([[0.0, 1.0], [1.0, 0.0]]), np.array([0.5, 0.5]))
    assert flags.shape == (2, 0)


def test_a_concept_the_model_never_answered_takes_the_middle_of_the_scale():
    assert np.allclose(classify.pool_medians(np.array([[np.nan], [np.nan]])), [0.5])


# ---- the labelled subsets -----------------------------------------------------------------------

def test_subsets_are_nested_and_floored_at_one_image_per_class():
    labels = np.array([0] * 60 + [1] * 30 + [2] * 10)
    subsets = classify.nested_subsets(labels, [5, 20, 50], n_classes=3, seed=0)
    for small, big in ((5, 20), (20, 50)):
        assert set(subsets[small]) <= set(subsets[big]), "a curve is one labelling effort growing"
    for n, idx in subsets.items():
        assert len(idx) == n
        assert set(labels[idx]) == {0, 1, 2}, "no class is missing, even at n=5"


def test_subsets_track_the_pool_proportions_where_they_can():
    labels = np.array([0] * 800 + [1] * 200)
    idx = classify.nested_subsets(labels, [100], n_classes=2, seed=0)[100]
    counts = np.bincount(labels[idx], minlength=2)
    assert abs(counts[0] - 80) <= 1 and abs(counts[1] - 20) <= 1


def test_a_different_seed_draws_a_different_subset():
    labels = np.array([0] * 50 + [1] * 50)
    a = classify.nested_subsets(labels, [10], 2, seed=0)[10]
    b = classify.nested_subsets(labels, [10], 2, seed=1)[10]
    assert set(a) != set(b)


# ---- the classifier ------------------------------------------------------------------------------

def test_a_class_absent_from_the_subset_scores_zero_rather_than_being_dropped():
    """Every arm's scores have to have the same shape, or the AUC is over different classes."""
    rng = np.random.default_rng(0)
    x_train = rng.normal(size=(20, 4)); y_train = np.array([0] * 10 + [1] * 10)
    got = classify.fit_predict(x_train, y_train, rng.normal(size=(7, 4)), n_classes=3,
                               l2_grid=[1.0], cv_folds=5, seed=0)
    assert got["scores"].shape == (7, 3)
    assert np.allclose(got["scores"][:, 2], 0.0)
    assert np.allclose(got["scores"].sum(axis=1), 1.0)


def test_the_fold_count_drops_to_what_the_smallest_class_allows():
    rng = np.random.default_rng(0)
    x = rng.normal(size=(12, 3)); y = np.array([0] * 9 + [1] * 3)
    got = classify.fit_predict(x, y, rng.normal(size=(4, 3)), 2, [0.1, 1.0], cv_folds=5, seed=0)
    assert got["folds"] == 3, "five folds do not fit three images of a class"


def test_the_regularisation_is_chosen_from_the_grid_inside_the_labelled_images():
    rng = np.random.default_rng(0)
    x = np.vstack([rng.normal(-1, 1, size=(30, 3)), rng.normal(1, 1, size=(30, 3))])
    y = np.array([0] * 30 + [1] * 30)
    got = classify.fit_predict(x, y, x[:5], 2, [0.01, 1.0, 100.0], cv_folds=5, seed=0)
    assert got["C"] in (0.01, 1.0, 100.0)
    assert got["folds"] == 5


def test_a_subset_with_one_class_says_so_instead_of_faking_a_probability():
    got = classify.fit_predict(np.zeros((4, 2)), np.zeros(4, dtype=int), np.zeros((3, 2)),
                               n_classes=2, l2_grid=[1.0], cv_folds=5, seed=0)
    assert got["folds"] == 0 and got["C"] is None
    assert np.allclose(got["scores"][:, 0], 1.0)


def test_concatenating_the_blocks_keeps_both_and_changes_nothing_else():
    """Arm C+P (H5) is arm C's matrix beside arm P's, standardised together by the same fit_predict.
    The columns must be the two blocks in order and nothing else, because the whole claim of the arm
    is that it differs from arm P in the presence of the concept columns alone."""
    rng = np.random.default_rng(0)
    c = rng.random((30, 4))
    p = rng.normal(size=(30, 9))
    cp = np.hstack([c, p])
    assert cp.shape == (30, 13)
    assert np.array_equal(cp[:, :4], c) and np.array_equal(cp[:, 4:], p)
    got = classify.fit_predict(cp, np.array([0] * 15 + [1] * 15), cp[:5], n_classes=2,
                               l2_grid=[1.0], cv_folds=5, seed=0)
    assert got["scores"].shape == (5, 2)


# ---- the multi-label task ------------------------------------------------------------------------

def test_strata_are_the_class_or_any_finding():
    """The nested subsets of the curve are stratified on the class; for chestmnist, whose label is a
    vector of fourteen findings, on whether the image carries any finding at all."""
    assert list(classify.strata(np.array([2, 0, 1]))) == [2, 0, 1]
    assert list(classify.strata(np.array([[2], [0]]))) == [2, 0]
    assert list(classify.strata(np.array([[1, 0, 0], [0, 0, 0], [0, 1, 1]]))) == [1, 0, 1]


def test_one_vs_rest_fits_each_finding_and_scores_a_constant_where_it_cannot():
    """The multi-label path of fit_predict: one regression per finding, a probability per finding
    per image, and a finding with no positives in the subset scored as a constant column rather than
    fitted on nothing or dropped."""
    rng = np.random.default_rng(0)
    x = rng.normal(size=(60, 3))
    y = np.zeros((60, 3), dtype=int)
    y[:, 0] = (x[:, 0] > 0).astype(int)              # finding 0 follows feature 0
    y[:, 1] = rng.integers(0, 2, size=60)            # finding 1 is noise
    #                                                  finding 2 never occurs in the subset
    got = classify.fit_predict(x, y, x[:10], n_classes=3, l2_grid=[0.1, 1.0], cv_folds=5, seed=0,
                               multi_label=True)
    assert got["scores"].shape == (10, 3)
    assert np.all((got["scores"] >= 0) & (got["scores"] <= 1))
    assert np.allclose(got["scores"][:, 2], 0.0), "an absent finding is a constant column"
    assert got["classes"] == [0, 1] and got["C_per_finding"][2] is None
    order = np.argsort(got["scores"][:, 0])
    assert (x[:10][order, 0] > 0).astype(int).tolist() == sorted((x[:10, 0] > 0).astype(int).tolist()), \
        "the fitted finding ranks its positives above its negatives"
