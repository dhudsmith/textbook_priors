"""The analysis chain end to end, on an archive small enough to reason about.

The estimators have their own tests and the metric has its own; what this one covers is the glue -
the stage functions that read a gathered archive, build the matrices, write the scores, run the
bootstrap, decide the hypotheses and draw the figures. That glue is where a wrong key or a
transposed matrix hides, and it is the one part that cannot be checked by reading it.

The fixture is built so the answer is known: the concept answers are a clean function of the label,
so arms B and C should be near-perfect, the zero-shot distribution is deliberately useless, so arm A
should be near chance, and the post-hoc arm D leans with the label, so it should land between them.
A run that gets those backwards has its arms crossed somewhere.
"""
import importlib
import json
from pathlib import Path

import numpy as np
import pytest
import yaml

from .conftest import ROOT

CONCEPTS = [
    {"id": "one", "question": "?", "scale": ["low", "high"], "anchors": {}},
    {"id": "two", "question": "?", "scale": ["small", "mid", "large"], "anchors": {}},
]
CLASSES = ["alpha", "beta"]
MODELS = {"tiny-model": {"family": "t", "params_b": 1, "concurrency": 8, "cap": 4, "splits": ["test"]},
          "big-model": {"family": "t", "params_b": 9, "concurrency": 8, "cap": 4,
                        "splits": ["test", "pool"]}}


def rows_for(labels, rng, signal=True):
    """A concept answer per image. With `signal`, the answers follow the label exactly."""
    out = []
    for i, y in enumerate(labels):
        if signal:
            answers = {"one": ["low", "high"][y], "two": ["small", "large"][y]}
        else:
            answers = {"one": rng.choice(["low", "high"]), "two": rng.choice(["small", "large"])}
        if i % 37 == 0:                                  # a few unanswered concepts, as in the real run
            answers["two"] = None
        out.append({"position": i, "index": int(i), "label": int(y), "complete": None not in answers.values(),
                    "answers": answers})
    return out


@pytest.fixture
def workspace(tmp_path):
    """A miniature of the real thing: one dataset, two models, two classes, on disk."""
    rng = np.random.default_rng(0)
    n_test, n_pool = 120, 200
    y_test = rng.integers(0, 2, size=n_test)
    y_pool = rng.integers(0, 2, size=n_pool)

    config = {
        "outdir": str(tmp_path / "results"), "conceptdir": str(tmp_path / "concepts"),
        "release": str(tmp_path / "medmnist.yaml"), "cachedir": str(tmp_path / "cache"),
        "literature": str(tmp_path / "literature.yaml"),
        "featuredir": str(tmp_path / "features"), "figdir": str(tmp_path / "figs"),
        "tabdir": str(tmp_path / "tabs"), "datasets": ["toymnist"], "size": 224,
        "sample": {"test_n": n_test, "pool_n": n_pool, "seed": 0},
        "curve": {"n": [20, 50], "seeds": [0, 1]},
        "vlm": {"primary": "big-model", "models": MODELS, "prompt": {"anchors": True},
                "chunk": 50, "max_tokens": 512, "retries": 1, "transport_retries": 2,
                "timeout": 30, "temperature": 0.0, "reasoning": "none",
                "base_url": "http://example", "key_file": str(tmp_path / "key")},
        "features": {"arch": "resnet18", "weights": "imagenet1k_v1", "batch": 8},
        "classify": {"l2_grid": [0.1, 1.0], "cv_folds": 5, "missing_max_frac": 0.05,
                     "permute": {"seeds": [0, 1]}},
        "evaluate": {"bootstrap": 200, "ci": 0.95, "seed": 0, "h3_min_wins": 1},
        "resources": {},
    }
    for key in ("outdir", "conceptdir", "cachedir", "featuredir", "figdir", "tabdir"):
        Path(config[key]).mkdir(parents=True, exist_ok=True)
    (tmp_path / "config.yaml").write_text(yaml.safe_dump(config))
    (tmp_path / "medmnist.yaml").write_text(yaml.safe_dump(
        {"medmnist_version": "3.0.2", "size": 224,
         "datasets": {"toymnist": {"file": "toymnist_224.npz", "md5_224": "x", "size_bytes": 1,
                                   "medmnist_task": "binary-class", "n_channels": 1,
                                   "n_samples": {"train": 1, "val": 1, "test": 1},
                                   "label": {0: "alpha", 1: "beta"}}}}))
    (tmp_path / "concepts" / "toymnist.yaml").write_text(yaml.safe_dump({
        "dataset": "toymnist", "modality": "toys", "task": "binary", "medmnist_task": "binary-class",
        "concepts": CONCEPTS,
        "classes": {"alpha": {"fingerprint": {"one": "low", "two": "small"}},
                    "beta": {"fingerprint": {"one": "high", "two": "any"}}}}))
    (tmp_path / "literature.yaml").write_text(yaml.safe_dump({
        "citation": "toy2020", "datasets": {"toymnist": {"resnet18_224": {"auc": 0.99, "acc": 0.95}}}}))

    results = Path(config["outdir"])
    (results / "prompts").mkdir(parents=True, exist_ok=True)
    (results / "prompts" / "toymnist.json").write_text(json.dumps(
        {"dataset": "toymnist", "concepts": CONCEPTS, "classes": CLASSES, "bank_sha256": "x",
         "prompts": {"concept": {"sha256": "c"}, "zero_shot": {"sha256": "z"}}}))

    # The gathered archive: both models on the test split, the primary also on the pool, and a
    # zero-shot cell whose numbers carry nothing.
    cells = {}
    for model in MODELS:
        cells[f"{model}__test__concept"] = {
            "model": model, "split": "test", "prompt": "concept", "served_model": model,
            "prompt_sha256": "c", "n": n_test, "incomplete_frac": 0.0, "over_missing_cap": False,
            "rows": rows_for(y_test, rng, signal=(model == "big-model"))}
    cells["big-model__pool__concept"] = {
        "model": "big-model", "split": "pool", "prompt": "concept", "served_model": "big-model",
        "prompt_sha256": "c", "n": n_pool, "incomplete_frac": 0.0, "over_missing_cap": False,
        "rows": rows_for(y_pool, rng)}
    cells["big-model__test__zero_shot"] = {
        "model": "big-model", "split": "test", "prompt": "zero_shot", "served_model": "big-model",
        "prompt_sha256": "z", "n": n_test, "incomplete_frac": 0.0, "over_missing_cap": False,
        "rows": [{"position": i, "index": i, "label": int(y), "complete": True,
                  "scores": {"alpha": 0.5, "beta": 0.5}} for i, y in enumerate(y_test)]}
    (results / "scores").mkdir(parents=True, exist_ok=True)
    (results / "scores" / "toymnist.json").write_text(json.dumps(
        {"dataset": "toymnist", "concepts": [c["id"] for c in CONCEPTS], "classes": CLASSES,
         "missing_max_frac": 0.05, "cells": cells, "chunk_files": []}))

    np.savez(Path(config["cachedir"]) / "toymnist.npz",
             test_labels=y_test, pool_labels=y_pool,
             test_indices=np.arange(n_test), pool_indices=np.arange(n_pool),
             test_images=np.zeros((n_test, 4, 4), dtype=np.uint8),
             pool_images=np.zeros((n_pool, 4, 4), dtype=np.uint8))
    # Pixel features that carry the label weakly, so arm P is better than chance and worse than C.
    np.savez(Path(config["featuredir"]) / "toymnist.npz",
             test_features=(y_test[:, None] + rng.normal(0, 1.4, size=(n_test, 6))).astype(np.float32),
             pool_features=(y_pool[:, None] + rng.normal(0, 1.4, size=(n_pool, 6))).astype(np.float32))
    return tmp_path, config, y_test


@pytest.fixture
def stages(workspace, monkeypatch):
    """priors.stages, reloaded against the miniature config."""
    tmp_path, _, _ = workspace
    monkeypatch.setenv("PRIORS_CONFIG", str(tmp_path / "config.yaml"))
    monkeypatch.chdir(ROOT)
    import priors.stages as module
    return importlib.reload(module)


def test_the_chain_runs_and_the_arms_come_out_where_the_fixture_put_them(workspace, stages):
    tmp_path, config, y_test = workspace
    results = Path(config["outdir"])

    stages.classify("toymnist", str(results / "classify/toymnist.json"),
                    str(results / "classify/toymnist.npz"))
    scores = np.load(results / "classify/toymnist.npz")
    assert np.array_equal(scores["labels"], y_test)
    assert {"A", "B__big-model", "B__tiny-model", "C__n20__seed0",
            "P__n50__seed1"} <= set(scores.files)

    stages.evaluate("toymnist", str(results / "evaluate/toymnist.json"))
    got = json.loads((results / "evaluate/toymnist.json").read_text())

    # The fixture's concept answers are a clean function of the label for the primary model, and its
    # zero-shot numbers are constant, so the arms must land in this order or something is crossed.
    assert got["auc"]["B__big-model"] > 0.9, "arm B should read a fingerprint that matches exactly"
    assert got["auc"]["B__tiny-model"] < got["auc"]["B__big-model"], "the noisy model must be worse"
    assert 0.4 <= got["auc"]["A"] <= 0.6, "a constant distribution cannot rank anything"
    assert got["auc"]["C__n50__seed0"] > got["auc"]["P__n50__seed0"], "clean features beat noisy ones"

    # The permutation control must cost arm B almost everything it had.
    assert got["controls"]["B__big-model"]["drop"]["median"] > 0.2

    stages.evaluate_across(str(results / "evaluation.json"))
    across = json.loads((results / "evaluation.json").read_text())
    assert across["h2"]["b_beats_a"]["toymnist"] is True
    assert across["h3"]["ladder"]["t"]["larger"] == "big-model"
    assert across["h3"]["ladder"]["t"]["wins"] == 1

    stages.tables(config["tabdir"])
    stages.figures(config["figdir"])
    for name in ("h1", "h2", "h3", "literature", "completeness", "numbers"):
        assert (Path(config["tabdir"]) / f"{name}.tex").stat().st_size > 0
    for name in ("curve", "n_b", "ladder"):
        assert (Path(config["figdir"]) / f"fig_{name}.png").stat().st_size > 0

    # Every macro the report's prose reads has to exist, or pdflatex fails on an undefined control
    # sequence after the whole study has run.
    macros = (Path(config["tabdir"]) / "numbers.tex").read_text()
    for name in ("hOneSupported", "hTwoSupported", "hThreeSupported", "cBeatsPWins", "bBeatsAWins",
                 "friedmanP", "medianNB", "numDatasets", "numModels",
                 "litGapZeroMedian", "litGapConceptMedian", "litGapPixelMedian", "litLargestN",
                 "litPixelWithinTwoPoints", "litZeroWithinFivePoints", "aucLitToy"):
        assert f"\\newcommand{{\\{name}}}" in macros, name

    # The literature table reads the ceiling against every arm, not only against arm B: the study
    # has four arms and a table that showed two would place the ceiling against a part of it.
    lit = (Path(config["tabdir"]) / "literature.tex").read_text()
    assert "& A & B &" in lit, lit.split("hline")[1]


def test_n_b_is_reported_as_a_code_when_the_crossing_is_outside_the_grid(workspace, stages):
    tmp_path, config, _ = workspace
    results = Path(config["outdir"])
    stages.classify("toymnist", str(results / "classify/toymnist.json"),
                    str(results / "classify/toymnist.npz"))
    stages.evaluate("toymnist", str(results / "evaluate/toymnist.json"))
    n_b = json.loads((results / "evaluate/toymnist.json").read_text())["n_b"]
    assert n_b["point"] in {"20", "50", "<=20", ">50"}
    assert 0.0 <= n_b["never_reaches_frac"] <= 1.0


def test_the_driver_imports_nothing_a_stage_does_not_need():
    """The stages do not share an environment. The features job runs in envs/priors_torch.yml,
    which has torch and neither sklearn nor openai, and a driver that imported every module at the
    top made that job fail on `import sklearn` before it did any work. One entry point per unit of
    work does not mean one dependency set for all of them."""
    source = (ROOT / "priors" / "stages.py").read_text()
    top = source[:source.index("def ")]
    for heavy in ("classify", "evaluate", "llm", "score", "features", "report", "prompts", "sample"):
        assert f"from . import {heavy}" not in top, f"{heavy} is imported at module scope"
        assert f"import {heavy} as" not in top, f"{heavy} is imported at module scope"
    assert "from . import data" in top, "data is yaml only and every stage uses it"


def test_the_light_environment_carries_no_torch_and_the_torch_one_no_sklearn():
    """Stated as a test because the two environments are the reason the imports are lazy."""
    light = (ROOT / "envs" / "priors.yml").read_text()
    heavy = (ROOT / "envs" / "priors_torch.yml").read_text()
    assert "torch" not in light.split("dependencies:")[1]
    assert "scikit-learn" not in heavy and "openai" not in heavy
    assert "torch" in heavy and "scikit-learn" in light
