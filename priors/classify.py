"""classify: the four arms, from the response archive and the pixel features.

Every estimator WORKFLOW.md section 3 fixes lives here, and nothing else does. The arms:

    A  zero-shot      the VLM's class distribution, read straight out of the archive
    B  textbook-only  nearest class fingerprint, no labels at all
    C  concept probe  regularised logistic regression on concept scores, n labels
    P  pixel probe    the same regression on frozen ImageNet features, the same n labels

C and P differ in their features and in nothing else - same classifier, same regularisation search,
same labelled subsets - because that is what makes the two curves a statement about the features.

Three choices are worth reading before the code, because each is a decision rather than an
implementation detail:

  * **Equal spacing weights concepts by scale length.** A concept's ordered scale maps to equally
    spaced values on [0, 1], so an adjacent miss costs 1.0 on a two-level scale and 0.25 on a
    five-level one. That is a consequence of the mapping, not a claim about importance, and it is
    why no per-concept coefficient here should be read as one.
  * **A missing answer is imputed and flagged, never guessed.** It becomes the labelled pool's
    median for that concept plus a missing-indicator column, so the regression can use "the model
    would not say" as information rather than as a value.
  * **Arm B scores only what both sides commit to.** A class's fingerprint masks `any`, the image's
    vector masks what the model did not answer, and the score is the negative mean absolute
    difference over the overlap. A thin fingerprint is therefore scored on few concepts and a
    near-miss on any of them costs it proportionally more, which is the honest reading of a thin
    fingerprint (data/concepts/README.md).
"""
from __future__ import annotations

import numpy as np
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
from sklearn.preprocessing import StandardScaler

MISSING = np.nan


def level_values(scale) -> dict:
    """A concept's ordered scale as equally spaced numbers on [0, 1]."""
    n = len(scale)
    if n < 2:
        raise ValueError(f"a scale needs at least two levels: {scale}")
    return {level: i / (n - 1) for i, level in enumerate(scale)}


def concept_matrix(rows, concepts) -> np.ndarray:
    """Answers -> an (images, concepts) matrix on [0, 1], with NaN where the model did not answer.

    Column order is the bank's concept order, which is the order the prompt asked in and the order
    every later matrix is indexed by.
    """
    values = [level_values(c["scale"]) for c in concepts]
    out = np.full((len(rows), len(concepts)), MISSING, dtype=np.float64)
    for i, row in enumerate(rows):
        answers = row["answers"]
        for j, concept in enumerate(concepts):
            level = answers.get(concept["id"])
            if level is not None:
                out[i, j] = values[j][level]
    return out


def fingerprint_matrix(classes, fingerprints, concepts) -> np.ndarray:
    """The bank's class fingerprints as a (classes, concepts) matrix, NaN where it says `any`."""
    values = [level_values(c["scale"]) for c in concepts]
    out = np.full((len(classes), len(concepts)), MISSING, dtype=np.float64)
    for i, name in enumerate(classes):
        committed = fingerprints[name]["fingerprint"]
        for j, concept in enumerate(concepts):
            level = committed.get(concept["id"])
            if level is not None and level != "any":
                out[i, j] = values[j][level]
    return out


def arm_b_scores(images: np.ndarray, fingerprints: np.ndarray) -> np.ndarray:
    """Arm B: the negative mean absolute difference from each class's fingerprint.

    Scored over the concepts the fingerprint commits to AND the image answered. A class with no
    overlap at all scores -1.0, the worst a mean absolute difference on [0, 1] can be: it is not
    evidence against the class, but there is nothing to say for it either, and leaving it NaN would
    make the AUC undefined rather than merely uninformative.

    The AUC reads these scores directly. They are negative distances, not probabilities, and no
    softmax is applied: the metric ranks each class column independently, so any strictly increasing
    transform leaves it unchanged (checked in the smoke tier against the package's own evaluator).
    """
    n, c = len(images), len(fingerprints)
    out = np.full((n, c), -1.0)
    for j in range(c):
        overlap = ~np.isnan(images) & ~np.isnan(fingerprints[j])[None, :]
        counts = overlap.sum(axis=1)
        diffs = np.where(overlap, np.abs(images - fingerprints[j][None, :]), 0.0)
        scored = counts > 0
        out[scored, j] = -(diffs[scored].sum(axis=1) / counts[scored])
    return out


def impute(matrix: np.ndarray, medians: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Fill missing answers with the labelled pool's median, and flag them.

    Returns the filled matrix and the missing-indicator columns that are not constant. A concept
    nobody ever failed to answer contributes an all-zero indicator, which carries no information
    and is dropped rather than standardised into a division by zero.
    """
    missing = np.isnan(matrix)
    filled = np.where(missing, medians[None, :], matrix)
    keep = missing.any(axis=0)
    return filled, missing[:, keep].astype(np.float64)


def pool_medians(matrix: np.ndarray) -> np.ndarray:
    """Per-concept medians of the labelled pool, ignoring the missing answers.

    A concept the model never answered anywhere in the pool has no median; it takes 0.5, the middle
    of the scale, which is the least committal value the mapping allows.
    """
    import warnings

    with warnings.catch_warnings():        # an all-missing concept is handled below, not a bug
        warnings.simplefilter("ignore", RuntimeWarning)
        medians = np.nanmedian(matrix, axis=0)
    return np.where(np.isnan(medians), 0.5, medians)


def nested_subsets(labels, grid, n_classes: int, seed: int) -> dict:
    """Class-stratified nested prefixes of the labelled pool, one per grid point.

    Nested by construction: the subset for each n extends the one before it, so the curve is a
    single labelling effort growing, not six unrelated draws. Each subset is as close to the pool's
    class proportions as a whole number allows, with a floor of one image per class, because a
    subset missing a class cannot predict it at all.
    """
    rng = np.random.default_rng(seed)
    by_class = {c: rng.permutation(np.flatnonzero(labels == c)) for c in range(n_classes)}
    available = np.array([len(by_class[c]) for c in range(n_classes)])
    share = available / available.sum()

    taken = np.zeros(n_classes, dtype=int)
    subsets = {}
    for n in sorted(grid):
        target = np.minimum(np.maximum(np.floor(share * n).astype(int), 1), available)
        # Largest remainder for what rounding left over, then never take fewer than the last grid
        # point did - that is what keeps the prefixes nested.
        while target.sum() < min(n, available.sum()):
            room = available - target
            order = np.argsort(-(share * n - target) * (room > 0) - 1e9 * (room <= 0))
            target[order[0]] += 1
        target = np.maximum(target, taken)
        subsets[n] = np.concatenate([by_class[c][:target[c]] for c in range(n_classes)])
        taken = target
    return subsets


def fit_predict(x_train, y_train, x_test, n_classes: int, l2_grid, cv_folds: int, seed: int) -> dict:
    """Multinomial logistic regression with its L2 strength chosen inside the labelled images.

    No validation set: n labels means n labels (WORKFLOW.md section 3). The regularisation strength
    is chosen by stratified k-fold cross-validation over those same n images, the features are
    standardised on them, and the fold count drops to the smallest class count when five folds
    would not fit. A class absent from the subset gets an all-zero score column rather than being
    dropped, so every arm's scores have the same shape and the AUC is over the same classes.
    """
    present = np.unique(y_train)
    scaler = StandardScaler().fit(x_train)
    train, test = scaler.transform(x_train), scaler.transform(x_test)

    folds = int(min(cv_folds, np.bincount(y_train, minlength=n_classes)[present].min()))
    if len(present) < 2:
        # One class in the subset: the fit is degenerate, so say so rather than fake a probability.
        scores = np.zeros((len(x_test), n_classes))
        scores[:, present[0]] = 1.0
        return {"scores": scores, "C": None, "folds": 0, "classes": present.tolist()}

    best, best_score = None, -np.inf
    if folds >= 2:
        splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
        for c in l2_grid:
            total = 0.0
            for fit_idx, val_idx in splitter.split(train, y_train):
                # scikit-learn 1.9 dropped `multi_class`: softmax over all classes at once is
                # what LogisticRegression does for a multiclass problem under lbfgs, which is the
                # multinomial regression WORKFLOW.md section 3 specifies.
                model = LogisticRegression(C=c, max_iter=2000)
                model.fit(train[fit_idx], y_train[fit_idx])
                total += model.score(train[val_idx], y_train[val_idx])
            if total / folds > best_score:
                best, best_score = c, total / folds
    else:
        best = float(np.median(l2_grid))

    model = LogisticRegression(C=best, max_iter=2000)
    model.fit(train, y_train)
    probabilities = model.predict_proba(test)
    scores = np.zeros((len(x_test), n_classes))
    scores[:, model.classes_] = probabilities
    return {"scores": scores, "C": float(best), "folds": folds, "classes": present.tolist()}


def permute_fingerprints(fingerprints: np.ndarray, seed: int) -> np.ndarray:
    """Arm B's control: the same fingerprints, attached to the wrong classes.

    The bank's rows still say what a textbook says; only the labels on them are shuffled. If arm B
    scores as well this way, it was never reading the bank (H2).
    """
    rng = np.random.default_rng(seed)
    order = rng.permutation(len(fingerprints))
    while len(fingerprints) > 1 and np.all(order == np.arange(len(fingerprints))):
        order = rng.permutation(len(fingerprints))
    return fingerprints[order]


def permute_columns(matrix: np.ndarray, seed: int) -> np.ndarray:
    """Arm C's control: each concept column shuffled across images independently.

    The marginal distribution of every concept survives; only the pairing with the image, and hence
    with the label, is destroyed. What remains is what the classifier could learn from the concept
    scores' shape alone.
    """
    rng = np.random.default_rng(seed)
    out = matrix.copy()
    for j in range(out.shape[1]):
        out[:, j] = out[rng.permutation(len(out)), j]
    return out
