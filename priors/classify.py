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


def strata(labels) -> np.ndarray:
    """What the nested subsets are stratified on: the class for a single-label task, and for the
    multi-label one whether the image carries any finding at all. Fourteen co-occurring findings
    have no single class to stratify on, and any-finding against no-finding is the split that
    matters for a curve whose first point is fifty images: it keeps positives of some kind in every
    subset. The floor of one image per stratum is then one abnormal film, not one of each finding,
    and a finding absent from a subset scores a constant (see fit_predict)."""
    labels = np.asarray(labels)
    if labels.ndim == 2 and labels.shape[1] > 1:
        return (labels.sum(axis=1) > 0).astype(int)
    return labels.reshape(-1).astype(int)


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


def fit_predict(x_train, y_train, x_test, n_classes: int, l2_grid, cv_folds: int, seed: int,
                multi_label: bool = False) -> dict:
    """Multinomial logistic regression with its L2 strength chosen inside the labelled images.

    No validation set: n labels means n labels (WORKFLOW.md section 3). The regularisation strength
    is chosen by stratified k-fold cross-validation over those same n images, the features are
    standardised on them, and the fold count drops to the smallest class count when five folds
    would not fit. A class absent from the subset gets an all-zero score column rather than being
    dropped, so every arm's scores have the same shape and the AUC is over the same classes.

    `multi_label` (chestmnist) fits the same regression one finding at a time, one-vs-rest, which is
    what the package's per-finding AUC is a metric of. Two things differ from the single-label path
    and are said here rather than discovered: a finding with no positives (or no negatives) in the
    subset cannot be fitted and scores a constant column, which the AUC reads as uninformative; and
    the L2 strength is chosen by out-of-fold AUC rather than accuracy, because a finding present in
    two percent of films makes "always negative" the most accurate classifier at every strength and
    accuracy could not choose between them.
    """
    if multi_label:
        return _fit_predict_one_vs_rest(x_train, np.asarray(y_train), x_test, n_classes, l2_grid,
                                        cv_folds, seed)
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


def _fit_predict_one_vs_rest(x_train, y_train, x_test, n_findings, l2_grid, cv_folds, seed) -> dict:
    """The multi-label half of fit_predict: one binary regression per finding, L2 by out-of-fold AUC."""
    from sklearn.metrics import roc_auc_score

    scaler = StandardScaler().fit(x_train)
    train, test = scaler.transform(x_train), scaler.transform(x_test)
    scores = np.zeros((len(x_test), n_findings))
    chosen, fold_counts, present = [], [], []
    for j in range(n_findings):
        yj = y_train[:, j].astype(int)
        n_pos = int(yj.sum())
        if n_pos == 0 or n_pos == len(yj):
            scores[:, j] = float(yj[0])            # nothing to learn: the subset is all one way
            chosen.append(None); fold_counts.append(0)
            continue
        present.append(j)
        folds = int(min(cv_folds, n_pos, len(yj) - n_pos))
        best, best_score = float(np.median(l2_grid)), -np.inf
        if folds >= 2:
            splitter = StratifiedKFold(n_splits=folds, shuffle=True, random_state=seed)
            for c in l2_grid:
                oof = np.zeros(len(yj))
                for fit_idx, val_idx in splitter.split(train, yj):
                    model = LogisticRegression(C=c, max_iter=2000).fit(train[fit_idx], yj[fit_idx])
                    oof[val_idx] = model.predict_proba(train[val_idx])[:, 1]
                got = roc_auc_score(yj, oof)
                if got > best_score:
                    best, best_score = c, got
        model = LogisticRegression(C=best, max_iter=2000).fit(train, yj)
        scores[:, j] = model.predict_proba(test)[:, 1]
        chosen.append(float(best)); fold_counts.append(folds)
    fitted = [c for c in chosen if c is not None]
    return {"scores": scores, "C": float(np.median(fitted)) if fitted else None,
            "C_per_finding": chosen, "folds": int(min(fold_counts)) if fold_counts else 0,
            "classes": present}


def cv_probe(x, y, n_classes: int, l2_grid, folds: int, seed: int) -> dict:
    """How much class information is in these concept answers, without a labelled pool.

    H4's measure (WORKFLOW.md sections 2 and 3). Arm C answers the same question but needs the
    2,000-image pool, which only the primary model at effort `none` was ever asked to score; buying
    it for every reader would cost twelve thousand calls to compare six readings of the same two
    hundred images. So the classifier is fitted *inside* the scored images by stratified k-fold
    cross-validation, and what comes back is the out-of-fold score for every image: each image is
    predicted by a model that never saw it.

    Three properties this has to have, because H4 is a comparison between readers and not a claim
    about any one of them:

      * **The folds are identical across readers.** They are built from the labels and the seed,
        both of which are the same for every reader, so a difference between two readers is the
        concept answers and nothing else.
      * **Every image gets exactly one out-of-fold score**, so the result is one score matrix of
        the same shape as every other arm's and goes into the same paired bootstrap. The bootstrap
        then resamples images over fixed predictions, exactly as it does for arms B, C and P.
      * **It is not arm C and must not be read as arm C.** A cross-validated fit on 200 images is
        an estimate of information content, not a point on the learning curve: no `n` labels were
        spent, because the same images are both the training and the evaluation material. The
        report says so where it is read.

    A class too rare to appear in every fold drops the fold count, the same rule arm C uses; a
    class with fewer members than two cannot be cross-validated at all and its column stays zero,
    which the AUC convention reads as an uninformative column rather than a missing one.
    """
    counts = np.bincount(y, minlength=n_classes)
    usable = counts[counts > 0].min()
    k = int(min(folds, usable))
    scores = np.zeros((len(x), n_classes))
    if k < 2 or len(np.unique(y)) < 2:
        return {"scores": scores, "folds": 0, "thin_classes": int((counts < k).sum())}

    splitter = StratifiedKFold(n_splits=k, shuffle=True, random_state=seed)
    for fit_idx, held_idx in splitter.split(x, y):
        got = fit_predict(x[fit_idx], y[fit_idx], x[held_idx], n_classes, l2_grid, folds, seed)
        scores[held_idx] = got["scores"]
    return {"scores": scores, "folds": k, "thin_classes": int((counts < k).sum())}


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
