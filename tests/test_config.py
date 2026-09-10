"""Config and profile consistency: the throttles, the model design, the call budget the plan states."""
import math
import re

import yaml

from tests.conftest import ROOT


def _slug(m):
    return re.sub(r"[^0-9A-Za-z]+", "_", m)


def test_profile_throttles_equal_the_config_caps(cfg):
    prof = yaml.safe_load((ROOT / "profiles/palmetto/config.yaml").read_text())
    caps = dict(r.split("=") for r in prof["resources"])
    for m, mc in cfg["vlm"]["models"].items():
        assert int(caps[f"llm_{_slug(m)}"]) == int(mc["cap"]), m
        assert int(mc["cap"]) < int(mc["concurrency"])
    assert "zenodo" in caps


def test_models_form_a_crossed_two_by_two(cfg):
    models = cfg["vlm"]["models"]
    fams = {}
    for m, mc in models.items():
        fams.setdefault(mc["family"], []).append(mc["params_b"])
    assert len(fams) == 2 and all(len(v) == 2 for v in fams.values())
    assert cfg["vlm"]["primary"] in models
    assert "pool" in models[cfg["vlm"]["primary"]]["splits"]
    assert all(mc["splits"] == ["test"] for m, mc in models.items() if m != cfg["vlm"]["primary"])


def _n(cfg, release, ds, split):
    s = cfg["sample"]
    n = release["datasets"][ds]["n_samples"]
    return min(s["test_n"], n["test"]) if split == "test" else min(s["pool_n"], n["train"])


def test_call_budget_and_job_count(cfg, release):
    """47,406 calls: the plan's 49,406 less the 2,000 chestmnist calls no arm reads (the ladder
    models' concept scores and the zero-shot prompt on a multi-label dataset). 477 chunk jobs."""
    ds_all = cfg["datasets"]
    arm_b = [d for d in ds_all if d not in cfg["arm_b_exclude"]]
    primary = cfg["vlm"]["primary"]
    chunk = cfg["vlm"]["chunk"]
    calls = jobs = 0
    for m, mc in cfg["vlm"]["models"].items():
        for ds in (ds_all if m == primary else arm_b):
            for split in mc["splits"]:
                n = _n(cfg, release, ds, split)
                calls += n
                jobs += math.ceil(n / chunk)
    for ds in arm_b:
        n = _n(cfg, release, ds, "test")
        calls += n
        jobs += math.ceil(n / chunk)
    assert calls == 47406
    assert jobs == 477


def test_zeroshot_names_cover_the_label_map(cfg, release):
    for ds, names in cfg["vlm"]["zeroshot_names"].items():
        assert set(names) == set(release["datasets"][ds]["label"].values())


def test_every_dataset_has_a_bank_file_and_curve_is_sorted(cfg):
    for ds in cfg["datasets"]:
        assert (ROOT / cfg["conceptdir"] / f"{ds}.yaml").exists()
    assert cfg["curve"]["n"] == sorted(cfg["curve"]["n"]) and cfg["curve"]["n"][0] == 50
    assert set(cfg["modality_order"]) == set(cfg["datasets"])
