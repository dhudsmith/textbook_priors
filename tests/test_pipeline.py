"""The analysis chain end to end, on an archive small enough to reason about.

The estimators have their own tests and the metric has its own; what this one covers is the glue -
the stage functions that read a gathered archive, build the matrices, write the scores, run the
bootstrap, decide the hypotheses and draw the figures. That glue is where a wrong key or a
transposed matrix hides, and it is the one part that cannot be checked by reading it.

The fixture is built so the answer is known: the concept answers are a clean function of the label,
so arms B and C should be near-perfect, and the zero-shot distribution is deliberately useless, so
arm A should be near chance. A run that gets those backwards has its arms crossed somewhere.

H4's readers are built the same way. The thinking reader answers a little better than the baseline
and the frontier reader better again, so both steps of the chain must come out positive; a chain
that read its readers in the wrong order, or that compared a reader with itself, would show up as a
step of zero or a step with the wrong sign.

A second, multi-label dataset rides beside the first: three findings, arms C and P only, scored by
the primary model alone, with a pool too small for the largest curve point. It exercises the path
chestmnist takes - one-vs-rest fits, findings-as-columns AUC, no arm A or B, a shorter grid - and
the across-dataset stage's habit of counting it for H1 and leaving it out of H2 to H4.
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
# H4's readers: the same model asked to think, and a different model asked to think as hard.
# The chain is anchored on `tiny-model`, whose answers are noise, so that the fixture can make each
# step of the chain legibly better without touching `big-model` - the cell arms B and C read, which
# has to stay a clean function of the label for the assertions below it to mean anything.
SUBSAMPLE = 80
READERS = {"tiny-model-medium": {"model": "tiny-model", "effort": "medium", "api": "local",
                                 "cap": 4, "max_tokens": 2048, "subsample": SUBSAMPLE},
           "frontier-medium": {"model": "frontier", "effort": "medium", "api": "gateway",
                               "service_tier": "flex", "cap": 4, "max_tokens": 4096,
                               "subsample": SUBSAMPLE}}


def rows_for(labels, rng, signal=True, noise=0.0):
    """A concept answer per image. With `signal`, the answers follow the label exactly.

    `noise` flips that fraction of answers away from the label, which is how the fixture makes one
    reader legibly worse than another: the probe should recover less from the noisier answers, and
    by a margin the bootstrap can see.
    """
    out = []
    for i, y in enumerate(labels):
        if signal:
            flip = rng.random() < noise
            v = 1 - y if flip else y
            answers = {"one": ["low", "high"][v], "two": ["small", "large"][v]}
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
        "tabdir": str(tmp_path / "tabs"), "datasets": ["toymnist", "toychest"], "size": 224,
        "sample": {"test_n": n_test, "pool_n": n_pool, "seed": 0},
        "curve": {"n": [20, 50], "seeds": [0, 1]},
        "vlm": {"primary": "big-model", "models": MODELS, "readers": READERS,
                "prompt": {"anchors": True},
                "chunk": 50, "max_tokens": 512, "retries": 1, "transport_retries": 2,
                "timeout": 30, "temperature": 0.0, "reasoning": "none",
                "base_url": "http://example", "key_file": str(tmp_path / "key")},
        "features": {"arch": "resnet18", "weights": "imagenet1k_v1", "batch": 8},
        "classify": {"l2_grid": [0.1, 1.0], "cv_folds": 5, "missing_max_frac": 0.05,
                     "permute": {"seeds": [0, 1]}, "probe": {"folds": 4, "seed": 0}},
        # One arm-B dataset: at alpha 0.6 one win of one (p = 0.5) reaches the level, so the fixture's
        # verdicts can be asserted; at the real 0.05 a single dataset can never support anything.
        "evaluate": {"bootstrap": 200, "ci": 0.95, "seed": 0, "alpha": 0.6},
        "h4": {"baseline": "tiny-model", "thinking": "tiny-model-medium",
               "frontier": "frontier-medium", "subsample": SUBSAMPLE},
        "h5": {"n": 20},
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
                                   "label": {0: "alpha", 1: "beta"}},
                      "toychest": {"file": "toychest_224.npz", "md5_224": "y", "size_bytes": 1,
                                   "medmnist_task": "multi-label, binary-class", "n_channels": 1,
                                   "n_samples": {"train": 1, "val": 1, "test": 1},
                                   "label": {0: "f0", 1: "f1", 2: "f2"}}}}))
    (tmp_path / "concepts" / "toymnist.yaml").write_text(yaml.safe_dump({
        "dataset": "toymnist", "modality": "toys", "task": "binary", "medmnist_task": "binary-class",
        "concepts": CONCEPTS,
        "classes": {"alpha": {"fingerprint": {"one": "low", "two": "small"}},
                    "beta": {"fingerprint": {"one": "high", "two": "any"}}}}))
    (tmp_path / "literature.yaml").write_text(yaml.safe_dump({
        "citation": "toy2020", "datasets": {"toymnist": {"resnet18_224": {"auc": 0.99, "acc": 0.95}},
                                            "toychest": {"resnet18_224": {"auc": 0.80, "acc": 0.90}}}}))

    results = Path(config["outdir"])
    (results / "prompts").mkdir(parents=True, exist_ok=True)
    (results / "prompts" / "toymnist.json").write_text(json.dumps(
        {"dataset": "toymnist", "concepts": CONCEPTS, "classes": CLASSES, "bank_sha256": "x",
         "bank_file": "data/concepts/toymnist.yaml",
         # system/user as `render_prompts` writes them: the appendix prints these verbatim, so a
         # fixture without them would let a missing field reach the report unnoticed.
         "prompts": {"concept": {"sha256": "c", "keys": [c["id"] for c in CONCEPTS],
                                 "system": "You are an expert reader.",
                                 "user": "Answer 2 questions about this image."},
                     "zero_shot": {"sha256": "z", "keys": CLASSES,
                                   "system": "You are an expert reader.",
                                   "user": "Which of 2 categories is this image?"}}}))

    # The gathered archive: both models on the test split, the primary also on the pool, and a
    # zero-shot cell whose numbers carry nothing.
    cells = {}
    for model in MODELS:
        cells[f"{model}__test__concept"] = {
            "model": model, "split": "test", "prompt": "concept", "served_model": model,
            "prompt_sha256": "c", "n": n_test, "incomplete_frac": 0.0, "over_missing_cap": False,
            "rows": rows_for(y_test, rng, signal=(model == "big-model"))}
    # H4's readers, on the prefix only. The baseline (tiny-model) is pure noise, the thinking
    # reader is mostly right, the frontier reader almost always right, so both steps of the chain
    # must come out positive and the figure must rise from left to right.
    for reader, noise in (("tiny-model-medium", 0.25), ("frontier-medium", 0.05)):
        cells[f"{reader}__test__concept"] = {
            "model": reader, "split": "test", "prompt": "concept", "served_model": reader,
            "prompt_sha256": "c", "n": SUBSAMPLE, "incomplete_frac": 0.0,
            "over_missing_cap": False,
            "rows": rows_for(y_test[:SUBSAMPLE], np.random.default_rng(7), noise=noise)}
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

    add_multi_label_dataset(tmp_path, config, rng)
    return tmp_path, config, y_test


def add_multi_label_dataset(tmp_path, config, rng):
    """`toychest`: three findings, a pool of 40 (so the grid's 50 is dropped), the primary model
    alone on the concept prompt. The first concept follows finding 0 and the second finding 1, so
    arm C must read both findings well and finding 2, which nothing predicts, at chance."""
    n_test, n_pool = 90, 40
    findings = 3
    y_test = (rng.random((n_test, findings)) < 0.4).astype(int)
    y_pool = (rng.random((n_pool, findings)) < 0.4).astype(int)
    y_pool[0] = 0                                        # at least one film with no finding
    (tmp_path / "concepts" / "toychest.yaml").write_text(yaml.safe_dump({
        "dataset": "toychest", "modality": "toy films", "task": "multi-label",
        "medmnist_task": "multi-label, binary-class", "concepts": CONCEPTS,
        "classes": {f"f{j}": {"fingerprint": {"one": "any", "two": "any"}} for j in range(findings)}}))
    results = Path(config["outdir"])
    (results / "prompts" / "toychest.json").write_text(json.dumps(
        {"dataset": "toychest", "concepts": CONCEPTS, "classes": [f"f{j}" for j in range(findings)],
         "bank_sha256": "y", "bank_file": "data/concepts/toychest.yaml", "multi_label": True,
         "prompts": {"concept": {"sha256": "cc", "keys": [c["id"] for c in CONCEPTS],
                                 "system": "You are an expert reader.",
                                 "user": "Answer 2 questions about this film."},
                     "zero_shot": None}}))

    def rows(labels):
        return [{"position": i, "index": i, "label": [int(v) for v in y], "complete": True,
                 "answers": {"one": ["low", "high"][y[0]], "two": ["small", "large"][y[1]]}}
                for i, y in enumerate(labels)]
    cells = {"big-model__test__concept": {
                 "model": "big-model", "split": "test", "prompt": "concept", "served_model": "big-model",
                 "prompt_sha256": "cc", "n": n_test, "incomplete_frac": 0.0, "over_missing_cap": False,
                 "rows": rows(y_test)},
             "big-model__pool__concept": {
                 "model": "big-model", "split": "pool", "prompt": "concept", "served_model": "big-model",
                 "prompt_sha256": "cc", "n": n_pool, "incomplete_frac": 0.0, "over_missing_cap": False,
                 "rows": rows(y_pool)}}
    (results / "scores" / "toychest.json").write_text(json.dumps(
        {"dataset": "toychest", "concepts": [c["id"] for c in CONCEPTS],
         "classes": [f"f{j}" for j in range(findings)], "missing_max_frac": 0.05, "cells": cells,
         "chunk_files": []}))
    np.savez(Path(config["cachedir"]) / "toychest.npz",
             test_labels=y_test, pool_labels=y_pool,
             test_indices=np.arange(n_test), pool_indices=np.arange(n_pool),
             test_images=np.zeros((n_test, 4, 4), dtype=np.uint8),
             pool_images=np.zeros((n_pool, 4, 4), dtype=np.uint8))
    np.savez(Path(config["featuredir"]) / "toychest.npz",
             test_features=(y_test[:, :1] + rng.normal(0, 1.4, size=(n_test, 6))).astype(np.float32),
             pool_features=(y_pool[:, :1] + rng.normal(0, 1.4, size=(n_pool, 6))).astype(np.float32))


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
            "P__n50__seed1", "CP__n20__seed0", "CP__n50__seed1"} <= set(scores.files)

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

    # The multi-label dataset: arms C and P only, a grid its pool can reach, and no n_B.
    stages.classify("toychest", str(results / "classify/toychest.json"),
                    str(results / "classify/toychest.npz"))
    chest = np.load(results / "classify/toychest.npz")
    assert chest["labels"].shape == (90, 3)
    assert not any(k == "A" or k.startswith("B__") or k.startswith("CV__") for k in chest.files)
    assert {"C__n20__seed0", "P__n20__seed1", "CP__n20__seed0", "Cperm__n20__seed0"} <= set(chest.files)
    assert not any("n50" in k for k in chest.files), "a pool of 40 cannot fill a subset of 50"
    stages.evaluate("toychest", str(results / "evaluate/toychest.json"))
    chest_eval = json.loads((results / "evaluate/toychest.json").read_text())
    assert chest_eval["multi_label"] and chest_eval["curve_n"] == [20]
    assert chest_eval["n_b"] is None and chest_eval["h4"] is None
    assert chest_eval["auc"]["C__n20__seed0"] > 0.7, "two of three findings are readable"
    assert "B_minus_A" not in chest_eval["differences"]

    stages.evaluate_across(str(results / "evaluation.json"))
    across = json.loads((results / "evaluation.json").read_text())
    # H1 counts both datasets; everything that needs an arm B counts the single-label one alone.
    assert across["arm_b_datasets"] == ["toymnist"]
    assert set(across["h1"]["c_beats_p_at_smallest_n"]) == {"toymnist", "toychest"}
    assert set(across["h1"]["n_b"]) == {"toymnist"}
    assert set(across["h2"]["b_beats_a"]) == {"toymnist"} and across["h2"]["n_datasets"] == 1

    # H5 counts every dataset, reads the grid point config names, and its arm is the two blocks
    # concatenated: the fixture's concept features carry the label and its pixel features are
    # noisy, so C+P must beat P where C does.
    h5 = across["h5"]
    assert h5["n"] == 20 and set(h5["per_dataset"]) == {"toymnist", "toychest"}
    assert h5["per_dataset"]["toymnist"] is True
    assert h5["differences"]["toymnist"]["median"] > 0
    summary = json.loads((results / "classify/toymnist.json").read_text())
    cols = summary["feature_columns"]
    assert cols["CP"] == cols["C"] + cols["P"], "the concatenated block is exactly the two blocks"
    assert across["h2"]["b_beats_a"]["toymnist"] is True
    assert across["h3"]["ladder"]["t"]["larger"] == "big-model"
    assert across["h3"]["ladder"]["t"]["wins"] == 1

    # H4: the chain must be read in the order config fixes it, and each step must recover the sign
    # the fixture built in. A chain that compared a reader with itself, or that took the readers in
    # dictionary order rather than chain order, would show a step of zero or the wrong sign here.
    h4 = across["h4"]
    assert h4["h4a"]["from"] == "tiny-model" and h4["h4a"]["to"] == "tiny-model-medium"
    assert h4["h4b"]["from"] == "tiny-model-medium" and h4["h4b"]["to"] == "frontier-medium"
    assert h4["h4a"]["differences"]["toymnist"]["median"] > 0, "thinking beats noise in the fixture"
    assert h4["h4b"]["differences"]["toymnist"]["median"] > 0, "the frontier reader is cleanest"
    assert h4["h4a"]["supported"] and h4["h4b"]["supported"] and h4["supported"]
    # Every reader is reported, not only the three in the chain: a reader hidden from the table is
    # one the reader of the table cannot check.
    assert set(h4["readers"]) == {"big-model", "tiny-model", "tiny-model-medium", "frontier-medium"}
    assert h4["probe_auc"]["toymnist"]["frontier-medium"] > h4["probe_auc"]["toymnist"]["tiny-model"]

    # The probe is fitted inside the images it scores, so it covers the prefix and not the sample.
    got_h4 = json.loads((results / "evaluate/toymnist.json").read_text())["h4"]
    assert got_h4["subsample"] == SUBSAMPLE

    stages.tables(config["tabdir"])
    stages.figures(config["figdir"])
    for name in ("h1", "h2", "h3", "h4", "h5", "literature", "completeness", "features",
                 "appendix_prompts", "numbers"):
        assert (Path(config["tabdir"]) / f"{name}.tex").stat().st_size > 0
    for name in ("curve", "n_b", "ladder", "readers", "thinking", "h5"):
        assert (Path(config["figdir"]) / f"fig_{name}.png").stat().st_size > 0

    # The appendix has to print what was actually sent, or it is decoration. It reads the same
    # rendered file every score manifest hashes, so the strings must appear in it verbatim, and the
    # multi-label dataset must be shown as having no zero-shot prompt rather than silently omitted.
    appendix = (Path(config["tabdir"]) / "appendix_prompts.tex").read_text()
    for dataset in ("toymnist", "toychest"):
        rendered = json.loads((results / "prompts" / f"{dataset}.json").read_text())
        for key, message in rendered["prompts"].items():
            if message is None:
                assert "multi-label, so arm A is not defined" in appendix
                continue
            assert message["user"] in appendix, f"{dataset} {key} user text missing"
            assert message["sha256"][:16] in appendix

    # Wrapping for the page must not alter the prompt. The invariant that makes the printed
    # SHA-256 checkable is that only whitespace changes, so every other character survives in order.
    from priors.report import _wrap_verbatim
    long_prompt = json.loads((results / "prompts" / "toymnist.json").read_text())["prompts"]
    for message in long_prompt.values():
        for text in (message["system"], message["user"], "x " * 300, "  indented " + "y" * 400):
            wrapped = _wrap_verbatim(text)
            assert "".join(wrapped.split()) == "".join(text.split())
            assert max(len(line) for line in wrapped.split("\n")) <= 92 or "y" * 93 in text

    # The feature table documents arm C+P's fusion as a fact: its width is the sum of the blocks.
    features = (Path(config["tabdir"]) / "features.tex").read_text()
    cols = json.loads((results / "classify/toymnist.json").read_text())["feature_columns"]
    assert f"{cols['C']} & {cols['P']} & {cols['CP']}" in features

    # Every macro the report's prose reads has to exist, or pdflatex fails on an undefined control
    # sequence after the whole study has run.
    macros = (Path(config["tabdir"]) / "numbers.tex").read_text()
    for name in ("hOneSupported", "hTwoSupported", "hThreeSupported", "cBeatsPWins", "bBeatsAWins",
                 "friedmanP", "medianNB", "numDatasets", "numArmBDatasets", "minWinsAll", "numModels",
                 "hFiveSupported", "hFiveWins", "hFiveN", "hFiveMedianGain",
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
