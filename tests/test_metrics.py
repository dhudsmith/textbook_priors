"""The AUC convention this project reports, pinned to the package that defines it.

Every number in the study is `medmnist.evaluator.getAUC` on the shared 500-image test sample
(WORKFLOW.md section 3), chosen because it is the MedMNIST benchmark's own convention rather than
because it is the only reasonable one. These tests say exactly what that convention is, so that a
figure caption reading "macro one-vs-rest AUC" is a statement about the code and not a hope.

They test the package, not our code, on purpose: three properties of it are load-bearing here, and
if a future version changed any of them the arms would stop being comparable.
"""
import numpy as np
import pytest
from sklearn.metrics import roc_auc_score


@pytest.fixture
def multiclass():
    """A four-class problem with scores that are informative but not perfect."""
    rng = np.random.default_rng(0)
    y = rng.integers(0, 4, size=200)
    scores = rng.random((200, 4))
    scores[np.arange(200), y] += 0.8            # the true class scores a little higher
    return y, scores / scores.sum(axis=1, keepdims=True)


def test_multiclass_auc_is_the_unweighted_mean_of_one_vs_rest_aucs(evaluator, multiclass):
    y, scores = multiclass
    ours = evaluator.getAUC(y, scores, "multi-class")
    per_class = [roc_auc_score((y == i).astype(int), scores[:, i]) for i in range(scores.shape[1])]
    assert ours == pytest.approx(float(np.mean(per_class)))
    # Which is sklearn's macro one-vs-rest, the name the report uses for it.
    assert ours == pytest.approx(roc_auc_score(y, scores, multi_class="ovr", average="macro"))
    # Unweighted: a rare class counts as much as a common one, so a dataset's class balance does
    # not quietly reweight the comparison between arms.
    assert ours != pytest.approx(roc_auc_score(y, scores, multi_class="ovr", average="weighted"))


def test_the_auc_reads_any_monotone_class_score_not_only_a_distribution(evaluator, multiclass):
    """Arm B scores a class by the negative mean absolute difference from its fingerprint, which is
    neither positive nor normalised, and WORKFLOW.md section 3 says the AUC reads that score
    directly with no softmax. This is why that is allowed: the metric ranks each class column
    independently, so any strictly increasing per-column transform leaves it unchanged."""
    y, scores = multiclass
    reference = evaluator.getAUC(y, scores, "multi-class")
    negative_distances = 3.0 * scores - 7.0                       # arm B's shape: all negative
    assert evaluator.getAUC(y, negative_distances, "multi-class") == pytest.approx(reference)
    per_column_scaling = scores * np.array([0.5, 2.0, 10.0, 1.0]) - 4.0
    assert evaluator.getAUC(y, per_column_scaling, "multi-class") == pytest.approx(reference)
    # sklearn's own macro-ovr would refuse these, which is the practical reason to keep to getAUC.
    with pytest.raises(ValueError):
        roc_auc_score(y, negative_distances, multi_class="ovr", average="macro")


def test_binary_auc_reads_the_last_column_as_the_positive_class(evaluator):
    """pneumoniamnist is `binary-class`, where a two-column score matrix is not averaged over both
    columns: the package takes the last one. Feeding it class 0's probability would report 1 - AUC,
    which looks like a plausible number and is exactly backwards."""
    y = np.array([0, 0, 0, 1, 1, 1, 0, 1])
    positive = np.array([0.1, 0.3, 0.2, 0.9, 0.6, 0.8, 0.4, 0.5])
    two_column = np.stack([1 - positive, positive], axis=1)
    expected = roc_auc_score(y, positive)
    assert evaluator.getAUC(y, two_column, "binary-class") == pytest.approx(expected)
    assert evaluator.getAUC(y, positive, "binary-class") == pytest.approx(expected)
    assert evaluator.getAUC(y, two_column[:, ::-1], "binary-class") == pytest.approx(1 - expected)
