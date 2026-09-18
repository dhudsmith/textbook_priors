#!/usr/bin/env python3
"""Export one run's results as the talk website's data snapshot.

The site at `talk/` has no compute of its own and hand-types no number: it reads the JSON this
script writes. That is the one deliberate exception to "results are never committed" (talk/PLAN.md
section 4) - the site is built on GitHub's runners, where `results/` does not exist, and a talk is
a snapshot of one run by design.

It reads only; it writes only under `talk/public/`. Nothing here decides a hypothesis: every
verdict below is copied from `results/evaluation.json`, which the `evaluate_across` rule wrote.

Run it with the base python (numpy, Pillow, PyYAML), or through the opt-in `talk_data` rule:

    python3 talk/scripts/export_talk_data.py
    snakemake --profile profiles/local -j 1 talk_data

Two fields are hand-authored rather than read, both marked and both cited in the output: the
timeline's `kind` per session-log entry (TIMELINE_KINDS), and the contention measurements
transcribed from CHANGELOG.md 2026-09-12 (CONTENTION). Everything else comes from a file.
"""
from __future__ import annotations

import argparse
import csv
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import yaml
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "talk" / "public"

# ---------------------------------------------------------------------------------------------
# The two hand-authored tables. Both are prose turned into data; both name their source.
# ---------------------------------------------------------------------------------------------

# One kind per session-log entry, assigned by reading the entry. The kinds are the four-day
# strip's only colour, and they are a reading of SESSION_LOG.md rather than a field in it:
#   direct  the user set the direction or the scope       decide  a choice was settled
#   build   a rule, a module or a document was written    catch   something wrong was found
#   run     compute was submitted and results landed      rewind  work was removed or undone
TIMELINE_KINDS = {
    "2026-09-11 15:15": "direct", "2026-09-11 15:26": "direct", "2026-09-11 16:05": "decide",
    "2026-09-11 16:20": "build",  "2026-09-11 17:30": "run",    "2026-09-11 20:05": "catch",
    "2026-09-11 21:20": "decide", "2026-09-11 21:45": "decide", "2026-09-11 22:00": "catch",
    "2026-09-12 09:05": "direct", "2026-09-12 09:02": "build",  "2026-09-12 09:35": "catch",
    "2026-09-12 14:40": "direct", "2026-09-12 15:05": "direct", "2026-09-12 15:20": "catch",
    "2026-09-12 15:45": "rewind", "2026-09-12 16:05": "decide", "2026-09-12 17:40": "run",
    "2026-09-12 21:25": "decide", "2026-09-12 21:45": "run",    "2026-09-12 22:30": "direct",
    "2026-09-12 23:05": "catch",  "2026-09-12 23:15": "rewind", "2026-09-13 07:00": "decide",
    "2026-09-13 07:30": "direct", "2026-09-13 08:05": "direct", "2026-09-13 08:20": "direct",
    "2026-09-13 10:15": "run",    "2026-09-13 10:40": "direct", "2026-09-13 12:25": "catch",
    "2026-09-13 12:45": "run",    "2026-09-13 14:25": "build",  "2026-09-13 20:05": "build",
    "2026-09-13 20:40": "decide", "2026-09-13 21:00": "direct", "2026-09-13 22:15": "run",
    "2026-09-13 22:25": "build",  "2026-09-13 23:05": "build",  "2026-09-14 06:55": "decide",
    "2026-09-16 23:25": "direct",
}

# Transcribed from CHANGELOG.md 2026-09-12, "The service serialises us: concurrency buys no
# throughput" and "The primary model is contention-bound, and a wave that wrote nothing". Two
# points, not a curve; the changelog says so and so does the caption.
CONTENTION = {
    "source": "CHANGELOG.md 2026-09-12",
    "note": ("Measured on qwen3.8-27b-fp8 through the same code path, not modelled. Two points per "
             "series rather than a curve; the service is shared, so some of the change may be "
             "other users' load."),
    "series": [
        {"id": "zero_shot_thinking_off", "label": "class prompt, thinking off",
         "model": "qwen3.8-27b-fp8",
         "points": [{"jobs": 1, "s_per_call": 1.5, "calls_per_s": 0.67},
                    {"jobs": 24, "s_per_call": 42.8, "calls_per_s": 0.56}]},
        {"id": "concept_thinking_off", "label": "visual-features prompt, thinking off",
         "model": "qwen3.8-27b-fp8",
         "points": [{"jobs": 1, "s_per_call": 4.5, "calls_per_s": 0.22},
                    {"jobs": 48, "s_per_call": 89.0, "calls_per_s": 0.54}]},
        {"id": "concept_thinking_medium", "label": "visual-features prompt, thinking at medium",
         "model": "qwen3.8-27b-fp8-medium",
         "points": [{"jobs": 1, "s_per_call": 1.5, "calls_per_s": 0.67},
                    {"jobs": 11, "s_per_call": 134.0, "calls_per_s": 0.08}]},
    ],
    "ladder_models": [
        {"model": "qwen3.5-9b", "cap": 96, "s_per_call": 2.8},
        {"model": "gemma-4-12b", "cap": 24, "s_per_call": 3.4},
        {"model": "gemma-4-31b", "cap": 12, "s_per_call": 5.0},
        {"model": "qwen3.8-27b-fp8", "cap": 48, "s_per_call": 89.0},
    ],
}

# The close's "caught by" tally: each near miss the study recorded, and what actually caught it.
# Read off CHANGELOG.md and SESSION_LOG.md by date; the `source` field is where to check it.
CATCHES = [
    {"what": "An unfair baseline that would have made the headline claim true whatever the numbers said",
     "caught_by": "a person reading the plan", "source": "CHANGELOG.md 2026-09-09"},
    {"what": "Four generated rules that all ran the last model's command",
     "caught_by": "one chunk run before 270", "source": "CHANGELOG.md 2026-09-11"},
    {"what": "3,000 good answers filed in a part of the reply our code never read, and recorded as missing",
     "caught_by": "one diagnostic call", "source": "CHANGELOG.md 2026-09-11"},
    {"what": "Forty-eight jobs at once that ran for two hours and wrote nothing",
     "caught_by": "a timed call", "source": "CHANGELOG.md 2026-09-12"},
    {"what": "Thinking believed impossible, when the cause was our own limit on reply length",
     "caught_by": "a test at 15:20", "source": "CHANGELOG.md 2026-09-12"},
    {"what": "A second agent session moving the shared working copy to another version of the code mid-run",
     "caught_by": "the record filed beside each result", "source": "SESSION_LOG.md 2026-09-13 12:25"},
    {"what": "Eleven thinking jobs at once that would all have hit their time limit",
     "caught_by": "one chunk run first, and a timed call", "source": "CHANGELOG.md 2026-09-12"},
]

# The report's own colour tables (priors/report.py), so a listener who has seen the PDF recognises
# them. Read, not re-chosen. The dark-mode steps are the same hues lifted off a dark surface.
# What is true of each model the study called, beyond what config/config.yaml records. Two facts
# are not in the configuration and must not be guessed from it: whether the weights are open, and
# which reasoning efforts the model accepts. Both are transcribed here from
# docs/rcd_llm_service.md - the vision-capable table read 2026-09-12 from the service's own
# `/v1/models?full=true`, and the note that the gateway models take `reasoning_effort` but reject
# `minimal`, which is why no closed model here can be asked not to think. `api: gateway` in the
# configuration is a transport, not a licence, so it is not used as a stand-in for either.
#
# `params_b: None` is not missing data: the closed family publishes no parameter count, which is
# itself a finding - it is why H7 had to order that family by price instead of by size.
MODEL_FACTS = {
    "qwen3.5-9b":      {"weights": "open",   "reasoning": ["none", "high"]},
    "gemma-4-12b":     {"weights": "open",   "reasoning": ["none", "high"]},
    "qwen3.8-27b-fp8": {"weights": "open",   "reasoning": ["none", "low", "medium", "xhigh"]},
    "gemma-4-31b":     {"weights": "open",   "reasoning": ["none", "high"]},
    "gpt-5.6-luna":    {"weights": "closed", "reasoning": ["low", "medium"],
                        "family": "gpt-5.6", "params_b": None},
    "gpt-5.6-terra":   {"weights": "closed", "reasoning": ["low", "medium"],
                        "family": "gpt-5.6", "params_b": None},
    "gpt-5.6-sol":     {"weights": "closed", "reasoning": ["low", "medium"],
                        "family": "gpt-5.6", "params_b": None},
}
MODEL_FACTS_SOURCE = "docs/rcd_llm_service.md (read from /v1/models?full=true, 2026-09-12)"


def model_table(config: dict, by_model: dict, primary: str, price_order: list[str]) -> list[dict]:
    """One row per model the study actually called, in the order the talk meets them.

    The open models come first in size order, because that is the ladder H3 climbs, and the closed
    family follows in the price order H7 used. `calls` is every call the model answered under any
    reasoning effort, so a model that was also read as a thinking reader carries one number rather
    than two rows.
    """
    readers = config["vlm"]["readers"]
    served = {}
    for key, entry in by_model.items():
        name = readers[key]["model"] if key in readers else key
        got = served.setdefault(name, {"calls": 0, "served": []})
        got["calls"] += entry["calls"]
        got["served"] += [n for n in entry["served"] if n not in got["served"]]

    order = sorted(config["vlm"]["models"], key=lambda m: config["vlm"]["models"][m]["params_b"])
    order += [m for m in price_order if m not in order]
    rows = []
    for name in order:
        facts = MODEL_FACTS[name]
        spec = config["vlm"]["models"].get(name, {})
        rows.append({
            "name": name,
            "family": spec.get("family", facts.get("family")),
            "params_b": spec.get("params_b", facts.get("params_b")),
            "weights": facts["weights"],
            "reasoning": facts["reasoning"],
            "calls": served.get(name, {}).get("calls", 0),
            "served": served.get(name, {}).get("served", []),
            "primary": name == primary,
        })
    return rows


# One name per arm, and the same name the page uses for it everywhere else: the model's own
# guess, the feature scores, a classifier. The zero-label arms wear no "(no labels)" because the
# figure already draws them flat and the arm table has a column for it.
ARM_STYLE = [
    {"id": "A", "label": "arm A: the model's own guess", "colour": "#7f7f7f", "dark": "#a8a8a6",
     "dash": "2 3", "labels": 0},
    {"id": "B", "label": "arm B: feature scores matched to the textbook", "colour": "#2ca02c",
     "dark": "#5cc45c", "dash": "6 4", "labels": 0},
    {"id": "C", "label": "arm C: classifier on the feature scores", "colour": "#1f77b4",
     "dark": "#5aa7dd", "dash": None, "labels": "n"},
    {"id": "P", "label": "arm P: classifier on image features", "colour": "#d62728",
     "dark": "#f2615f", "dash": None, "labels": "n"},
    {"id": "CP", "label": "arm C+P: classifier on both", "colour": "#762a83", "dark": "#b47ec0",
     "dash": "5 3", "labels": "n"},
]
LIT_STYLE = {"id": "lit", "label": "ceiling: published result, trained on every label "
                                   "(Yang et al. 2023)",
             "colour": "#8c564b", "dark": "#c08a7c", "dash": "1 4"}
DATASET_HUES = ["#1f77b4", "#d62728", "#2ca02c", "#762a83", "#e6820e", "#17789c",
                "#8c564b", "#c2185b", "#5b8c00", "#00695c", "#7f7f7f", "#9a6a00"]
DATASET_HUES_DARK = ["#5aa7dd", "#f2615f", "#5cc45c", "#b47ec0", "#f6a545", "#4fa9cb",
                     "#c08a7c", "#ee6592", "#96c832", "#3fa697", "#a8a8a6", "#d7a52f"]
DATASET_MARKERS = ["circle", "square", "triangle", "diamond", "triangle-down", "plus"]

SOURCES: list[str] = []


def note(rel: str) -> str:
    if rel not in SOURCES:
        SOURCES.append(rel)
    return rel


def read_json(rel: str):
    note(rel)
    return json.loads((ROOT / rel).read_text())


def read_yaml(rel: str):
    note(rel)
    return yaml.safe_load((ROOT / rel).read_text())


def read_text(rel: str) -> str:
    note(rel)
    return (ROOT / rel).read_text()


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


# The cluster is named in the README; the individual compute node is not named anywhere the
# project publishes, so the snapshot says which cluster ran the job and not which node.
CLUSTER = "a Palmetto2 compute node"

# The two things this snapshot deliberately does not carry out of the run's own files. Both are
# stated here rather than left to be noticed, because the point of the snapshot is that it can be
# checked against the archive it came from.
REDACTIONS = [
    "the owner-only LLM key path (params.key_file) is dropped from every manifest",
    f"the compute node's hostname is replaced by the cluster ({CLUSTER.strip()})",
    "absolute paths are rewritten relative to the repository root",
]


def redact_host(_host: str | None) -> str:
    """A manifest's host as the public snapshot may carry it: the cluster, not the node."""
    return CLUSTER


def relative_paths(value):
    """Rewrite this checkout's absolute paths as repo-relative ones, at any depth."""
    prefix = str(ROOT) + "/"
    if isinstance(value, str):
        return value[len(prefix):] if value.startswith(prefix) else value
    if isinstance(value, list):
        return [relative_paths(v) for v in value]
    if isinstance(value, dict):
        return {k: relative_paths(v) for k, v in value.items()}
    return value


def strip_private(manifest: dict) -> dict:
    """A manifest as the site may see it: no owner-only key path, no compute node name, and the
    argv the near miss of 2026-09-11 was caught in, with this checkout's own location removed."""
    out = relative_paths(json.loads(json.dumps(manifest)))
    out.get("params", {}).pop("key_file", None)
    if "host" in out:
        out["host"] = redact_host(out.get("host"))
    return out


def write_json(rel: str, payload) -> Path:
    path = PUBLIC / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=1, sort_keys=False) + "\n")
    return path


def save_png(array: np.ndarray, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = "L" if array.ndim == 2 else "RGB"
    Image.fromarray(array, mode=mode).save(path, format="PNG", optimize=True)


# ---------------------------------------------------------------------------------------------


def ceiling_of(literature: dict, dataset: str) -> tuple[str, dict]:
    """The published ceiling for one task: the best of the five methods, by AUC.

    The same definition priors/report.py uses, so the site's ceiling and the PDF's are one number.
    """
    return max(literature["datasets"][dataset].items(), key=lambda kv: kv[1]["auc"])


def median(values: list[float]) -> float:
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def registration(pattern: str) -> dict:
    """The commit that first carried a hypothesis's rule into WORKFLOW.md.

    Pre-registration lives in git: this is the evidence, read out of the history rather than
    asserted. The commit carrying the rule has to precede the one carrying the numbers.
    """
    line = git("log", "--reverse", "--format=%H %ad", "--date=short", f"-S{pattern}",
               "--", "WORKFLOW.md").splitlines()
    if not line:
        return {}
    commit, date = line[0].split()
    return {"commit": commit, "short": commit[:10], "date": date}


def build_study(args) -> dict:
    config = read_yaml("config/config.yaml")
    release = read_yaml("config/medmnist.yaml")
    literature = read_yaml("data/literature/benchmarks.yaml")
    across = read_json("results/evaluation.json")
    figures = read_json("results/figures.json")
    datasets = config["datasets"]
    primary = config["vlm"]["primary"]

    per = {d: read_json(f"results/evaluate/{d}.json") for d in datasets}
    classify = {d: read_json(f"results/classify/{d}.json") for d in datasets}
    banks = {d: read_yaml(f"data/concepts/{d}.yaml") for d in datasets}

    run = across["manifest"]
    arm_b = across["arm_b_datasets"]

    # --- the seven hypotheses, their rules and their verdicts. Every count, p and verdict is
    # copied from results/evaluation.json; nothing here recomputes a decision.
    h = {k: across[k] for k in ("h1", "h2", "h3", "h4", "h5", "h6", "h7")}
    numbers_commit = run["git_commit"]

    def precedes(reg: dict) -> bool | None:
        if not reg:
            return None
        ok = subprocess.run(["git", "merge-base", "--is-ancestor", reg["commit"], numbers_commit],
                            cwd=ROOT, capture_output=True)
        return ok.returncode == 0

    verdicts = []
    for spec in [
        dict(id="h1", section="h1", title="Substitution",
             question="Are textbook features worth a measurable number of labelled images?",
             rule=("median n_B ≥ 100 over the eleven arm-B datasets AND AUC(C) > AUC(P) at "
                   "n = 50 on at least 10 of the 12 datasets (p < 0.05)"),
             wins=h["h1"]["c_beats_p_wins"], threshold=h["h1"]["min_wins"],
             n_datasets=h["h1"]["n_datasets"], p=h["h1"]["c_beats_p_sign_test_p"],
             supported=h["h1"]["supported"], per_dataset=h["h1"]["c_beats_p_at_smallest_n"],
             metric="AUC(C) > AUC(P) at n = 50", registered=registration("H1 — Substitution")),
        dict(id="h2", section="h2", title="The bank, not just the model",
             question="Does directing the model at cited visual features beat asking for the diagnosis?",
             rule="AUC(B) > AUC(A) on at least 9 of the 11 arm-B datasets (p < 0.05)",
             wins=h["h2"]["b_beats_a_wins"], threshold=h["h2"]["min_wins"],
             n_datasets=h["h2"]["n_datasets"], p=h["h2"]["b_beats_a_sign_test_p"],
             supported=h["h2"]["supported"], per_dataset=h["h2"]["b_beats_a"],
             metric="AUC(B) > AUC(A)", registered=registration("H2 — The bank")),
        dict(id="h3", section="h3", title="Scale",
             question="Does the prior get better with a bigger model?",
             rule=("the larger model has the higher AUC(B) on at least 9 of 11 datasets in BOTH "
                   "families (p < 0.05)"),
             wins=min(s["wins"] for s in h["h3"]["ladder"].values()),
             threshold=h["h3"].get("min_wins", 9), n_datasets=len(arm_b),
             p=max(s["sign_test_p"] for s in h["h3"]["ladder"].values()),
             supported=h["h3"]["supported"],
             per_dataset={d: all(s["per_dataset"].get(d, False) for s in h["h3"]["ladder"].values())
                          for d in arm_b},
             metric="larger beats smaller, within family",
             registered=registration("H3 — Scale")),
        dict(id="h4", section="h4", title="Reading",
             question="Does a better reader get more class information out of the same images?",
             rule=("each step — effort, then capability — wins on at least 9 of the 11 "
                   "arm-B datasets (p < 0.05)"),
             wins=min(h["h4"]["h4a"]["wins"], h["h4"]["h4b"]["wins"]),
             threshold=h["h4"].get("min_wins", 9), n_datasets=len(arm_b),
             p=max(h["h4"]["h4a"]["sign_test_p"], h["h4"]["h4b"]["sign_test_p"]),
             supported=h["h4"]["supported"], per_dataset=h["h4"]["h4a"]["per_dataset"],
             metric="cross-validated probe AUC, thinking step (H4a)",
             registered=registration("H4 — Reading")),
        dict(id="h5", section="h5", title="Complement",
             question="Does the textbook add anything the pixels do not already carry?",
             rule="AUC(C+P) > AUC(P) at n = 50 on at least 10 of the 12 datasets (p < 0.05)",
             wins=h["h5"]["wins"], threshold=h["h5"]["min_wins"], n_datasets=h["h5"]["n_datasets"],
             p=h["h5"]["sign_test_p"], supported=h["h5"]["supported"],
             per_dataset=h["h5"]["per_dataset"], metric="AUC(C+P) > AUC(P) at n = 50",
             registered=registration("H5 — Complement")),
        dict(id="h6", section="h4", title="Effort in the frontier model",
             question="Is H4b's null about the model, or about how hard it was asked to think?",
             rule=("gpt-5.6-terra at low beats the same model at medium on at least 9 of the 11 "
                   "arm-B datasets (p < 0.05)"),
             wins=h["h6"]["wins"], threshold=h["h6"]["min_wins"], n_datasets=h["h6"]["n_datasets"],
             p=h["h6"]["sign_test_p"], supported=h["h6"]["supported"],
             per_dataset=h["h6"]["per_dataset"], metric="probe AUC, low over medium",
             registered=registration("H6 — Effort in the frontier model")),
        dict(id="h7", section="h3", title="Capability inside the frontier family",
             question="Does a more capable closed model read cited features better?",
             rule=("gpt-5.6-sol beats gpt-5.6-luna, both at low, on at least 9 of the 11 arm-B "
                   "datasets (p < 0.05)"),
             wins=h["h7"]["wins"], threshold=h["h7"]["min_wins"], n_datasets=h["h7"]["n_datasets"],
             p=h["h7"]["sign_test_p"], supported=h["h7"]["supported"],
             per_dataset=h["h7"]["per_dataset"], metric="probe AUC, top of the price ladder over bottom",
             registered=registration("H7 — Capability inside the frontier family")),
    ]:
        spec["rule_precedes_numbers"] = precedes(spec["registered"])
        spec["verdict"] = "supported" if spec["supported"] else "not supported"
        verdicts.append(spec)

    # --- per-dataset payload. Everything the site draws, keyed by dataset.
    ds_meta, per_dataset = [], {}
    for i, d in enumerate(datasets):
        rel = release["datasets"][d]
        got = per[d]
        method, best = ceiling_of(literature, d)
        own_largest = max(got["curve_n"])
        ds_meta.append({
            "name": d,
            "modality": banks[d]["modality"],
            "task": banks[d]["task"],
            "medmnist_task": rel["medmnist_task"],
            "source_dataset": banks[d].get("source_dataset"),
            "multi_label": got["multi_label"],
            "has_arm_b": d in arm_b,
            "n_classes": got["n_classes"],
            "classes": got["classes"],
            "n_channels": rel["n_channels"],
            "split_sizes": rel["n_samples"],
            "test_n": min(config["sample"]["test_n"], rel["n_samples"]["test"]),
            "pool_n": min(config["sample"]["pool_n"], rel["n_samples"]["train"]),
            "curve_n": got["curve_n"],
            "n_concepts": len(banks[d]["concepts"]),
            "colour": DATASET_HUES[i % len(DATASET_HUES)],
            "colour_dark": DATASET_HUES_DARK[i % len(DATASET_HUES_DARK)],
            "marker": DATASET_MARKERS[i % len(DATASET_MARKERS)],
        })
        per_dataset[d] = {
            "auc": got["auc"],
            "curve": got["curve"],
            "curve_n": got["curve_n"],
            "differences": got["differences"],
            "controls": got["controls"],
            "n_b": got.get("n_b"),
            "arm_b_by_model": got.get("arm_b_by_model"),
            "h4": got.get("h4"),
            "h6": got.get("h6"),
            "h7": got.get("h7"),
            "complete_frac": got["complete_frac"],
            "incomplete_over_cap": got["incomplete_over_cap"],
            "bootstrap": got["bootstrap"],
            "feature_columns": classify[d].get("feature_columns"),
            "ceiling": {"method": method, "auc": best["auc"], "acc": best.get("acc"),
                        "methods": literature["datasets"][d]},
            "largest_n": own_largest,
        }

    # --- the published ceiling read against the arms, exactly as priors/report.py's macros do.
    gaps = {"zero": [], "concept": [], "pixel": []}
    ceiling_rows = []
    for d in datasets:
        top = ceiling_of(literature, d)[1]["auc"]
        own = max(per[d]["curve_n"])
        row = {"dataset": d, "ceiling": top,
               "pixel": per[d]["curve"][f"P__n{own}"]["point"],
               "concept": per[d]["curve"][f"C__n{own}"]["point"], "largest_n": own}
        gaps["concept"].append(top - row["concept"])
        gaps["pixel"].append(top - row["pixel"])
        if "A" in per[d]["auc"]:
            row["zero"] = max(per[d]["auc"]["A"], per[d]["auc"][f"B__{primary}"])
            gaps["zero"].append(top - row["zero"])
        ceiling_rows.append(row)

    # --- the archive, counted from its own manifests.
    chunks = sorted(glob.glob(str(ROOT / "results/score/*.json")))
    by_model: dict[str, dict] = {}
    calls = 0
    written = []
    for path in chunks:
        chunk = json.loads(Path(path).read_text())
        calls += chunk["calls"]
        slot = by_model.setdefault(chunk["model"], {"calls": 0, "chunks": 0, "served": set()})
        slot["calls"] += chunk["calls"]
        slot["chunks"] += 1
        slot["served"].add(chunk["served_model"])
        written.append(chunk["manifest"]["written"])
    for slot in by_model.values():
        slot["served"] = sorted(slot["served"])

    smoke = read_text("logs/smoke.log")
    tests = int(m.group(1)) if (m := re.search(r"(\d+) passed", smoke)) else None

    stages = [
        {"id": "smoke", "name": "Smoke", "jobs": 1, "unit": "job"},
        {"id": "sample", "name": "Sample", "jobs": len(datasets), "unit": "datasets"},
        {"id": "score", "name": "Score",
         "jobs": len(glob.glob(str(ROOT / "results/prompts/*.json"))) + len(chunks),
         "unit": "prompt renders + archived chunks"},
        {"id": "features", "name": "Features",
         "jobs": len(glob.glob(str(ROOT / "results/features/*.json"))), "unit": "datasets"},
        {"id": "classify", "name": "Classify",
         "jobs": len(glob.glob(str(ROOT / "results/classify/*.json"))), "unit": "datasets"},
        {"id": "evaluate", "name": "Evaluate", "jobs": len(datasets) + 1,
         "unit": "datasets + the across-dataset job"},
        {"id": "report", "name": "Report", "jobs": 3, "unit": "tables, figures, the PDF"},
    ]

    return {
        "provenance": {
            "run_git_commit": run["git_commit"],
            "exported": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "source_files": list(SOURCES),
            "redactions": REDACTIONS,
        },
        "run": {
            "git_commit": run["git_commit"], "git_dirty": run.get("git_dirty"),
            "written": run["written"], "host": redact_host(run.get("host")),
            "versions": run["versions"],
            "wall_seconds": run.get("wall_seconds"),
        },
        "study": {
            "datasets": datasets, "arm_b_datasets": arm_b, "primary": primary,
            "alpha": across["alpha"], "size": config["size"], "sample": config["sample"],
            "curve": config["curve"], "bootstrap": per[datasets[0]]["bootstrap"],
            "models": {m: {k: v for k, v in spec.items() if k in ("family", "params_b", "splits")}
                       for m, spec in config["vlm"]["models"].items()},
            "readers": {r: {k: v for k, v in spec.items()
                            if k in ("model", "effort", "api", "subsample")}
                        for r, spec in config["vlm"]["readers"].items()},
            "model_table": model_table(
                config, by_model, primary,
                [config["vlm"]["readers"][r]["model"] for r in h["h7"]["ladder"]]),
            "model_facts_source": MODEL_FACTS_SOURCE,
            "zenodo_record": release["zenodo_record"],
            "medmnist_version": release["medmnist_version"],
            "literature": {"citation": literature["citation"], "title": literature["source_title"],
                           "url": literature["source_url"], "table": literature["source_table"]},
        },
        "style": {"arms": ARM_STYLE, "literature": LIT_STYLE},
        "datasets": ds_meta,
        "verdicts": verdicts,
        "across": h,
        "per_dataset": per_dataset,
        "ceiling": {
            "rows": ceiling_rows,
            "median_gap": {k: (median(v) if v else None) for k, v in gaps.items()},
            "largest_n": max(config["curve"]["n"]),
            "pixel_within_two_points": sum(1 for g in gaps["pixel"] if round(g, 3) <= 0.02),
            "zero_within_five_points": sum(1 for g in gaps["zero"] if round(g, 3) <= 0.05),
            "pixel_at_or_above": sum(1 for g in gaps["pixel"] if round(g, 3) <= 0.0),
        },
        "archive": {
            "chunks": len(chunks), "calls": calls, "by_model": by_model,
            "first_written": min(written), "last_written": max(written),
        },
        "stages": stages,
        "ledger": {
            "calls": calls, "chunks": len(chunks), "datasets": len(datasets),
            "tests": tests, "hypotheses": len(verdicts),
            "supported": sum(1 for v in verdicts if v["supported"]),
            "arms": len(ARM_STYLE), "readers": len(per[arm_b[0]]["h4"]["probe_auc"]),
            "figures": len(figures["files"]),
            "session_log_entries": len(TIMELINE_KINDS),
            "work_dates": work_dates(),
            "catches": CATCHES,
        },
        "figures": figures["files"],
    }


def export_banks(datasets: list[str]) -> None:
    for d in datasets:
        bank = read_yaml(f"data/concepts/{d}.yaml")
        write_json(f"data/bank/{d}.json", {
            "dataset": d, "modality": bank["modality"], "task": bank["task"],
            "source_dataset": bank.get("source_dataset"),
            "provenance": bank["provenance"],
            "concepts": bank["concepts"],
            "classes": bank["classes"],
        })


def export_prompts(datasets: list[str]) -> None:
    dest = PUBLIC / "data" / "prompts"
    dest.mkdir(parents=True, exist_ok=True)
    for d in datasets:
        (dest / f"{d}.txt").write_text(read_text(f"results/prompts_txt/{d}.txt"))


def export_samples(datasets: list[str], per_class: int, cap: int, names: dict) -> dict:
    """Two test images per class, capped per dataset, straight out of the cached sample arrays.

    These are the images the arms were actually scored on - the same seeded sample, by position -
    so what the audience sees on the page is what the model saw.
    """
    index = {}
    for d in datasets:
        arrays = np.load(ROOT / f"data/cache/sample/{d}.npz")
        note(f"data/cache/sample/{d}.npz")
        images, labels = arrays["test_images"], arrays["test_labels"]
        rows = []
        if labels.ndim == 2:                      # chestmnist: fourteen co-occurring findings
            groups = {"any finding": np.flatnonzero(labels.any(axis=1)),
                      "no finding": np.flatnonzero(~labels.any(axis=1))}
        else:
            groups = {names[d][c]: np.flatnonzero(labels == c)
                      for c in sorted(set(labels.tolist()))}
        budget = max(1, cap // max(1, len(groups)))
        for name, positions in groups.items():
            for k, pos in enumerate(positions[:min(per_class, budget)]):
                rel = f"img/samples/{d}/{re.sub(r'[^a-z0-9]+', '-', name.lower())}_{k}.png"
                save_png(images[int(pos)], PUBLIC / rel)
                rows.append({"class": name, "position": int(pos), "file": rel})
        index[d] = rows
    return index


def export_archive(datasets: list[str], per_dataset: int, primary: str) -> dict:
    """A handful of real archived calls, with the image, both answers and the chunk's manifest.

    The site draws an image at random and shows the two answers it got - the feature scores
    and the class distribution - side by side, so the speaker can show real answers without
    buying a call. The two prompts are archived in separate chunks but cover the same test
    positions, so the records pair up on (dataset, position). Only chunk 00 of each dataset is
    read, and only the primary model's: two positions is enough, and the archive is
    write-protected and read here and nowhere else.
    """
    records, manifests = [], {}
    for d in datasets:
        arrays = np.load(ROOT / f"data/cache/sample/{d}.npz")
        images = arrays["test_images"]
        for prompt in ("concept", "zero_shot"):
            rel = f"results/score/{d}__{primary}__test__{prompt}__chunk00.json"
            if not (ROOT / rel).exists():
                continue
            chunk = read_json(rel)
            key = f"{d}__{prompt}"
            manifests[key] = {
                "file": Path(rel).name,
                "served_model": chunk["served_model"],
                "prompt_sha256": chunk["manifest"]["params"]["prompt_sha256"],
                "bank_sha256": chunk["manifest"]["params"].get("bank_sha256"),
                "git_commit": chunk["manifest"]["git_commit"],
                "slurm_job": chunk["manifest"]["slurm_job"],
                "host": redact_host(chunk["manifest"].get("host")),
                "written": chunk["manifest"]["written"],
                "temperature": chunk["manifest"]["params"].get("temperature"),
                "reasoning": chunk["manifest"]["params"].get("reasoning"),
                "max_tokens": chunk["manifest"]["params"].get("max_tokens"),
                "calls": chunk["calls"], "complete": chunk["complete"],
                "seconds_per_call": chunk["seconds_per_call"],
                "manifest": strip_private(chunk["manifest"]),
            }
            step = max(1, len(chunk["records"]) // per_dataset)
            for rec in chunk["records"][::step][:per_dataset]:
                reply = rec["replies"][-1] if rec["replies"] else {}
                img_rel = f"img/archive/{d}_{rec['position']:03d}.png"
                if not (PUBLIC / img_rel).exists():
                    save_png(images[int(rec["position"])], PUBLIC / img_rel)
                records.append({
                    "id": f"{key}__{rec['position']}",
                    "dataset": d, "prompt": prompt, "manifest_key": key,
                    "position": rec["position"], "index": rec["index"],
                    "label": rec["label"] if not isinstance(rec["label"], list) else rec["label"],
                    "image": img_rel,
                    "answers": rec.get("answers"), "parsed": rec.get("parsed"),
                    # The zero-shot reply is a number per class, parsed by the score stage
                    # against the release's own class names. Carrying it here is what lets
                    # the page show the answer as a table of names and numbers instead of
                    # the reply text, which no reader should have to decode.
                    "scores": rec.get("scores"),
                    "complete": rec.get("complete"), "invalid": rec.get("invalid"),
                    "text": reply.get("text"), "served_model": reply.get("served_model"),
                    "finish_reason": reply.get("finish_reason"),
                    "from_reasoning": reply.get("from_reasoning"),
                    "elapsed_s": reply.get("elapsed_s"),
                    "usage": {k: reply.get("usage", {}).get(k) for k in
                              ("prompt_tokens", "completion_tokens", "total_tokens")}
                    if reply.get("usage") else None,
                })
    return {"manifests": manifests, "records": records}


HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}) — (.+)$")

_MD_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
_MD_MARK = re.compile(r"(\*\*|\*|`|__|_)")
_SENTENCE = re.compile(r"(?<=[.!?])\s")


def _lead(text: str) -> str:
    """One plain sentence of a session-log entry, for the timeline card.

    The log is Markdown and the card renders text, so backticks and asterisks would be printed
    verbatim. Four to six hundred characters ending on an ellipsis is a wall on a phone, so the
    lead is cut at a sentence boundary instead: the first sentence, or as many whole sentences as
    fit in 220 characters.
    """
    plain = _MD_MARK.sub("", _MD_LINK.sub(r"\1", text)).strip()
    if not plain:
        return ""
    parts = [s.strip() for s in _SENTENCE.split(plain)]
    parts = [s for s in parts if s.strip(".…·-— ")]
    if not parts:
        return ""
    out = parts[0]
    for part in parts[1:]:
        if len(out) + 1 + len(part) > 220:
            break
        out = f"{out} {part}"
    if len(out) > 220:
        out = out[:219].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return out


def export_timeline() -> dict:
    """Every timestamped SESSION_LOG.md heading, with its first paragraph.

    The four-day strip and the one-day timeline are both this file: one tick per prompt that
    materially directed the work, because that is what the log records.
    """
    text = read_text("SESSION_LOG.md")
    entries, current, body = [], None, []
    for line in text.splitlines():
        m = HEADING.match(line)
        if m:
            if current:
                current["lead"] = " ".join(body).strip()
                entries.append(current)
            date, time, title = m.groups()
            current = {"date": date, "time": time, "title": title,
                       "kind": TIMELINE_KINDS.get(f"{date} {time}", "build")}
            body = []
        elif current is not None and not body:
            if line.strip():
                body.append(line.strip())
        elif current is not None and body and line.strip():
            body.append(line.strip())
        elif current is not None and body and not line.strip():
            current.setdefault("_done", True)
    if current:
        current["lead"] = " ".join(body).strip()
        entries.append(current)
    for e in entries:
        e.pop("_done", None)
        e["lead"] = _lead(e["lead"])
    # The log is written newest-appended but a day's entries are not always in clock order, and
    # the strip and the screen-reader list both read it straight through.
    entries.sort(key=lambda e: (e["date"], e["time"]))
    days = sorted({e["date"] for e in entries})
    return {"source": "SESSION_LOG.md", "days": days, "entries": entries,
            "kinds": [{"id": "direct", "label": "I set the direction"},
                      {"id": "build", "label": "code was written"},
                      {"id": "run", "label": "jobs were submitted"},
                      {"id": "decide", "label": "a choice was made"},
                      {"id": "catch", "label": "something wrong was found"},
                      {"id": "rewind", "label": "work was removed"}],
            "kind_note": ("Only the kind of each entry was assigned by hand; the rest is the "
                          "file's own heading and first paragraph.")}


# ---------------------------------------------------------------------------------------------
# The project timeline: what happened, when, in lanes over one clock.
#
# Four lanes, two of instants and two of intervals, and the difference between them is the point:
# the record dates a prompt and a commit to the minute but says nothing about how long either
# took, while a job manifest states its own duration. So prompts and commits are exported as
# points and jobs as spans, and nothing is given a width it cannot support.
#
# What the repository can and cannot tell us about who did the work:
#
#   prompts   SESSION_LOG.md's headings. One per prompt that materially directed the work. An
#             instant. No duration is recorded anywhere and none is inferred here.
#   commits   `git log`. Every commit in this project is authored by the owner, so authorship
#             cannot separate agent work from hand work - but the Co-Authored-By trailer can, and
#             it is on all but two of them. That trailer is the lane's honest claim: not "the AI
#             did this" but "an agent co-authored this commit, and the commit says so".
#   jobs      the manifests, which carry `written` and `wall_seconds`, so each is an interval.
#   calls     the archive under results/score/. A chunk records how many calls it made and, in
#             its manifest, the interval it ran in; an individual response carries the seconds it
#             took (`replies[].elapsed_s`) but no wall-clock time of its own. So a call cannot be
#             placed on the clock and 58,409 marks are not drawable. What is drawable is the rate:
#             a chunk's calls spread evenly across the chunk's own span, summed over chunks. That
#             is a rate, not a set of events, and the lane is drawn and captioned as one.
#
# The CPU/GPU split, and why this file does not make one: no rule in this workflow requests a GPU.
# `res()` in the Snakefile passes mem_mb, runtime and cpus_per_task and nothing else, the Palmetto
# profile names one partition for everything, and there is no gres or gpu key anywhere in the
# Snakefile, config/ or profiles/. The split the jobs actually have is declared instead by the
# `llm_*` throttle token the score rules hold: those jobs spent their wall time waiting on a
# remote model service, and the GPU that answered them is not this project's to meter. The other
# jobs computed here. That is the line the two job lanes draw, and `cpu_hours` on each says how
# much of this cluster's CPU each side actually consumed.
# ---------------------------------------------------------------------------------------------

# The stage that talks to the model service. Its rules are the ones holding an `llm_*` resource in
# the Snakefile; everything else runs its own arithmetic on the node it landed on.
LLM_STAGES = {"score"}


def _machine_jobs() -> list[dict]:
    """Every job that left a manifest: its rule, when it started and when it finished.

    `written` is the moment the job wrote its output and `wall_seconds` how long it had been
    running, so the pair is an interval and no clock beyond the manifests is consulted.
    """
    jobs = []
    for path in sorted((ROOT / "results").rglob("*.json")):
        try:
            payload = json.loads(path.read_text())
        except (ValueError, OSError):
            continue
        manifest = payload.get("manifest") if isinstance(payload, dict) else None
        if not isinstance(manifest, dict):
            continue
        written, wall = manifest.get("written"), manifest.get("wall_seconds")
        if not written or wall is None:
            continue
        end = datetime.fromisoformat(written)
        jobs.append({"stage": manifest.get("stage", "?"), "wall": float(wall),
                     "start": end - timedelta(seconds=float(wall)), "end": end,
                     # a score chunk knows how many calls it made; no call knows its own clock
                     "calls": int(payload.get("calls") or 0)})
    note("results/**/*.json (job manifests)")
    return sorted(jobs, key=lambda j: j["start"])


def _cpu_hours() -> dict[str, float]:
    """CPU time from Snakemake's own benchmarks, split the same way the job lanes are."""
    total = {"llm": 0.0, "local": 0.0}
    for path in sorted((ROOT / "benchmarks").rglob("*.tsv")):
        side = "llm" if path.parent.name in LLM_STAGES else "local"
        for row in csv.DictReader(path.read_text().splitlines(), delimiter="\t"):
            value = row.get("cpu_time")
            if value not in (None, "", "-"):
                total[side] += float(value) / 3600
    note("benchmarks/**/*.tsv")
    return total


def _agent_commits() -> list[dict]:
    """Every commit, when it landed, and whether an agent co-authored it.

    The author of every commit here is the owner, so the Co-Authored-By trailer is the only thing
    in the repository that distinguishes a commit an agent wrote from one it did not.
    """
    out = subprocess.run(
        ["git", "log", "--format=%ct%x1f%s%x1f%(trailers:key=Co-Authored-By,valueonly)%x1e"],
        cwd=ROOT, capture_output=True, text=True).stdout
    commits = []
    for record in out.split("\x1e"):
        record = record.strip("\n")
        if not record.strip():
            continue
        when, subject, trailers = (record.split("\x1f") + ["", ""])[:3]
        commits.append({"t": datetime.fromtimestamp(int(when)), "subject": subject,
                        "agent": "Claude" in trailers})
    commits.sort(key=lambda c: c["t"])
    return commits


def _blocks(spans: list[tuple[datetime, datetime]]) -> list[tuple[datetime, datetime, int]]:
    """Overlapping job intervals merged into the periods at least one of them was running, with
    how many fell in each. A lane's bar is a period the work occupied, not a single job."""
    merged: list[list] = []
    for start, end in sorted(spans):
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
            merged[-1][2] += 1
        else:
            merged.append([start, end, 1])
    return [(a, b, n) for a, b, n in merged]


def export_effort(study: dict) -> dict:
    """The project's timeline in lanes: prompts and commits as instants, jobs as spans.

    Reads timestamps and nothing else. Positions are exported as minutes from the start of the
    span so the site does no date arithmetic and the lanes cannot drift apart.
    """
    jobs = _machine_jobs()
    commits = _agent_commits()
    prompts = []
    for line in read_text("SESSION_LOG.md").splitlines():
        m = HEADING.match(line)
        if m:
            date, time, title = m.groups()
            prompts.append({"at": datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M"),
                            "title": title})
    prompts.sort(key=lambda p: p["at"])

    start = min([j["start"] for j in jobs] + [p["at"] for p in prompts]
                + [c["t"] for c in commits])
    finish = max([j["end"] for j in jobs] + [p["at"] for p in prompts]
                 + [c["t"] for c in commits])
    minutes = lambda t: round((t - start).total_seconds() / 60, 2)  # noqa: E731

    llm = [j for j in jobs if j["stage"] in LLM_STAGES]
    local = [j for j in jobs if j["stage"] not in LLM_STAGES]
    cpu = _cpu_hours()
    wall = {"llm": sum(j["wall"] for j in llm) / 3600,
            "local": sum(j["wall"] for j in local) / 3600}
    blocks = {side: _blocks([(j["start"], j["end"]) for j in group])
              for side, group in (("llm", llm), ("local", local))}
    busy = {side: sum((b - a).total_seconds() for a, b, _ in bs) / 3600
            for side, bs in blocks.items()}

    agent_commits = [c for c in commits if c["agent"]]
    machine_h = wall["llm"] + wall["local"]

    # The calls, binned. A chunk knows how many calls it made and when it ran, so its calls are
    # spread evenly over its own span and summed into fixed fifteen-minute bins. The bin width is
    # fixed here rather than left to the drawing so that the peak is one quotable number and not a
    # function of how wide someone's browser happens to be.
    CALL_BIN = 15
    call_spans = [(j["start"], j["end"], j["calls"]) for j in llm if j["calls"]]
    calls_total = sum(n for _, _, n in call_spans)
    bins: dict[int, float] = {}
    for a, b, n in call_spans:
        span_min = max((b - a).total_seconds() / 60, 1e-9)
        per_min = n / span_min
        lo_m, hi_m = minutes(a), minutes(b)
        i = int(lo_m // CALL_BIN)
        while i * CALL_BIN < hi_m:
            lo = max(lo_m, i * CALL_BIN)
            hi = min(hi_m, (i + 1) * CALL_BIN)
            if hi > lo:
                bins[i] = bins.get(i, 0.0) + per_min * (hi - lo)
            i += 1
    peak_bin = max(bins.values()) if bins else 0.0
    peak_rate = peak_bin * (60 / CALL_BIN)

    lanes = [
        {"id": "prompts", "kind": "point", "label": "a prompt",
         "count": len(prompts),
         "note": "one per entry in the session log; we know when it was, not how long it "
                 "took"},
        {"id": "commits", "kind": "point", "label": "code written",
         "count": len(commits), "agent_count": len(agent_commits),
         "note": (f"{len(agent_commits)} of {len(commits)} name an agent as co-author, which is "
                  "the only sign in the record that an agent wrote it")},
        {"id": "calls", "kind": "rate", "label": "calls to the RCD LLM service",
         "count": calls_total, "chunks": len(call_spans),
         "peak_per_hour": round(peak_rate), "peak_per_bin": round(peak_bin),
         "bin_minutes": CALL_BIN,
         "mean_per_hour": round(calls_total / busy["llm"]) if busy["llm"] else 0,
         "unit": "calls per hour",
         "note": ("a chunk records how many calls it made and when it ran, but no reply "
                  "carries a time of its own, so each chunk's calls are spread evenly across "
                  "its own span and counted in 15-minute steps: a rate, not one mark per "
                  "call")},
        {"id": "llm_jobs", "kind": "span",
         "label": "jobs waiting on the RCD LLM service",
         "count": len(llm), "hours": round(wall["llm"], 2),
         "cpu_hours": round(cpu["llm"], 2), "busy_hours": round(busy["llm"], 2),
         "blocks": len(blocks["llm"]),
         "note": ("the scoring jobs; their time is spent waiting on the RCD LLM service, whose "
                  "GPU time this project never measures")},
        {"id": "local_jobs", "kind": "span",
         "label": "jobs computing on the cluster",
         "count": len(local), "hours": round(wall["local"], 2),
         "cpu_hours": round(cpu["local"], 2), "busy_hours": round(busy["local"], 2),
         "blocks": len(blocks["local"]),
         "note": "sampling, features, the fits, the tests, the figures and the tables"},
    ]

    days = []
    cursor = start.replace(hour=0, minute=0, second=0, microsecond=0)
    while cursor <= finish:
        days.append({"date": cursor.strftime("%Y-%m-%d"), "minute": minutes(cursor)})
        cursor += timedelta(days=1)

    edges = sorted([(j["start"], 1) for j in jobs] + [(j["end"], -1) for j in jobs])
    live = peak = 0
    for _, delta in edges:
        live += delta
        peak = max(peak, live)

    calls = study["archive"]["calls"]
    headline = (f"{len(prompts)} prompts set off {len(jobs)} jobs, {calls:,} calls to the RCD "
                f"LLM service and {machine_h:.0f} hours of machine time.")

    return {
        "span": {"from": start.isoformat(timespec="minutes"),
                 "to": finish.isoformat(timespec="minutes"),
                 "minutes": minutes(finish)},
        "days": days,
        "lanes": lanes,
        "points": {
            "prompts": [{"minute": minutes(p["at"]), "at": p["at"].isoformat(timespec="minutes"),
                         "title": p["title"]} for p in prompts],
            "commits": [{"minute": minutes(c["t"]), "at": c["t"].isoformat(timespec="minutes"),
                         "title": c["subject"], "agent": c["agent"]} for c in commits],
        },
        # [start minute, end minute, jobs in the block] - the periods each kind of job occupied.
        "spans": {f"{side}_jobs": [[minutes(a), minutes(b), n] for a, b, n in bs]
                  for side, bs in blocks.items()},
        # [bin start minute, calls in the bin], fifteen minutes wide. The site draws these; it
        # does not choose the bin, so the peak the lane names is the peak the lane draws.
        "rates": {"calls": [[i * CALL_BIN, round(v, 1)] for i, v in sorted(bins.items())]},
        "counts": {"calls_peak_per_hour": round(peak_rate),
                   "prompts": len(prompts), "commits": len(commits),
                   "agent_commits": len(agent_commits), "jobs": len(jobs), "calls": calls,
                   "machine_hours": round(machine_h, 1),
                   "days_with_prompts": len({p["at"].date() for p in prompts})},
        "machine": {"wall_hours": round(machine_h, 3),
                    "cpu_hours": round(cpu["llm"] + cpu["local"], 3),
                    "busy_wall_hours": round(busy["llm"] + busy["local"], 3),
                    "mean_concurrency": round(machine_h / (busy["llm"] + busy["local"]), 2),
                    "peak_concurrency": peak,
                    "first_job": min(j["start"] for j in jobs).isoformat(timespec="minutes"),
                    "last_job": max(j["end"] for j in jobs).isoformat(timespec="minutes")},
        "headline": headline,
        "method": [
            "A job is the interval its own manifest states: `written` less `wall_seconds`. Where "
            "jobs of the same lane overlap, the lane draws the period they occupied between them "
            "rather than one bar per job.",
            "A prompt is the timestamp on its SESSION_LOG.md heading, and a commit its commit "
            "date - instants, not durations.",
            "A commit counts as an agent's where it carries a Co-Authored-By: Claude trailer; "
            "the author of every commit in this repository is the owner.",
            f"The call rate is each score chunk's own call count spread evenly across the "
            f"interval that chunk ran in, summed over chunks into {CALL_BIN}-minute bins.",
        ],
        "caveats": [
            "No archived response carries a wall-clock time of its own - only the seconds it "
            "took - so the calls are dated to the chunk that recorded them and spread evenly "
            f"across it in {CALL_BIN}-minute bins. The lane is a rate, not 58,409 placed events, "
            "and a wave's shape within a chunk is smoother than the truth.",
            "Prompts and commits are marked as moments because that is all the record holds. "
            "Nothing here measures human time, and no duration is inferred from the gaps.",
            "No rule in this workflow asks for a GPU - the Snakefile passes only memory, runtime "
            "and CPUs - so the jobs are split by what they waited on instead. The model service "
            f"answered {calls:,} calls on GPUs this project never meters; its jobs cost this "
            f"cluster {cpu['llm']:.1f} h of CPU against {wall['llm']:.0f} h of wall time.",
            "Only surviving results are counted. Work that was rerun or rewound - arm D, the "
            "deleted archive - left no manifest behind and so appears nowhere.",
        ],
    }


def work_dates() -> list[str]:
    """The days the study was worked on, from CHANGELOG.md's own dated entries.

    The change log is the owner's record of understanding and it ends at the report, so its
    distinct dates are the study's working days - which the session log is not, because that file
    keeps growing after the report (this export is written on one of those later days).
    """
    return sorted({m.group(1) for m in
                   re.finditer(r"^## (\d{4}-\d{2}-\d{2})", read_text("CHANGELOG.md"), re.M)})


def copy_figures() -> list[str]:
    dest = PUBLIC / "img" / "figs"
    dest.mkdir(parents=True, exist_ok=True)
    names = []
    for src in sorted((ROOT / "report" / "figs").glob("*.png")):
        shutil.copy2(src, dest / src.name)
        names.append(src.name)
    note("report/figs/*.png")
    return names


def verify(study: dict) -> list[tuple[str, str, str, bool]]:
    """Three exported numbers against the report's own generated tables (talk/PLAN.md section 7).

    The site and the PDF have to be the same run, or the QR audience reads one thing and the
    printed report another.
    """
    checks = []

    def tex(name: str) -> str:
        return read_text(f"report/tables/{name}")

    h1 = tex("h1.tex")
    row = next(l for l in h1.splitlines() if l.startswith("pneumoniamnist"))
    want = row.split("&")[5].strip().split("[")[0].strip()
    got = f"{study['per_dataset']['pneumoniamnist']['differences']['C_minus_P__n50']['median']:.3f}"
    checks.append(("H1 pneumoniamnist C-P at n=50", want, got, want == got))

    h5 = tex("h5.tex")
    want = re.search(r"won on (\d+) of 12", h5).group(1)
    got = str(study["across"]["h5"]["wins"])
    checks.append(("H5 wins", want, got, want == got))

    h67 = tex("h6h7.tex")
    row = next(l for l in h67.splitlines() if l.startswith("retinamnist"))
    want = row.split("&")[5].strip().rstrip("\\").split("[")[0].strip()
    got = f"{study['across']['h7']['differences']['retinamnist']['median']:.3f}"
    checks.append(("H7 sol-luna on retinamnist", want, got, want == got))
    return checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--per-class", type=int, default=2, help="sample images per class")
    ap.add_argument("--cap", type=int, default=16, help="sample images per dataset")
    ap.add_argument("--archive-records", type=int, default=2,
                    help="archived records per dataset and prompt (four per dataset in all)")
    args = ap.parse_args()

    PUBLIC.mkdir(parents=True, exist_ok=True)
    study = build_study(args)
    datasets = study["study"]["datasets"]

    export_banks(datasets)
    export_prompts(datasets)
    samples = export_samples(datasets, args.per_class, args.cap,
                             {m["name"]: m["classes"] for m in study["datasets"]})
    archive = export_archive(datasets, args.archive_records, study["study"]["primary"])
    timeline = export_timeline()
    figures = copy_figures()

    for meta in study["datasets"]:
        meta["samples"] = samples[meta["name"]]
    study["figures"] = figures
    study["provenance"]["source_files"] = list(SOURCES)

    prov = {"run_git_commit": study["provenance"]["run_git_commit"],
            "exported": study["provenance"]["exported"],
            "redactions": REDACTIONS}
    write_json("data/archive_sample.json", {**archive,
                                            "provenance": {**prov, "source_files": [
                                                "results/score/*__test__concept__chunk00.json",
                                                "results/score/*__test__zero_shot__chunk00.json",
                                                "data/cache/sample/*.npz"]}})
    write_json("data/timeline.json", {**timeline,
                                      "provenance": {**prov, "source_files": ["SESSION_LOG.md"]}})
    write_json("data/contention.json", {**CONTENTION,
                                        "provenance": {**prov, "source_files": ["CHANGELOG.md"]}})
    effort = export_effort(study)
    write_json("data/effort.json", {**effort, "provenance": {
        **prov, "source_files": ["results/**/*.json (job manifests)", "benchmarks/**/*.tsv",
                                 "SESSION_LOG.md"]}})
    write_json("data/study.json", study)

    pdf = ROOT / "report" / "report.pdf"
    if pdf.exists():
        shutil.copy2(pdf, PUBLIC / "report.pdf")

    print(f"wrote {PUBLIC}")
    print(f"  study.json            {len(datasets)} datasets, {len(study['verdicts'])} verdicts, "
          f"{study['archive']['calls']} archived calls")
    print(f"  bank/, prompts/       {len(datasets)} each")
    print(f"  archive_sample.json   {len(archive['records'])} records, "
          f"{len(archive['manifests'])} chunk manifests")
    print(f"  timeline.json         {len(timeline['entries'])} session-log entries")
    print(f"  effort.json           {len(effort['lanes'])} lanes over "
          f"{effort['span']['minutes'] / 1440:.1f} days; {effort['headline']}")
    print(f"  img/figs/             {len(figures)} report figures")
    print(f"  img/samples/          {sum(len(v) for v in samples.values())} images")
    total = sum(f.stat().st_size for f in PUBLIC.rglob("*") if f.is_file())
    print(f"  total                 {total / 1e6:.1f} MB")

    print("\nchecks against report/tables/*.tex (talk/PLAN.md section 7):")
    ok = True
    for name, want, got, passed in verify(study):
        print(f"  [{'ok' if passed else 'FAIL'}] {name:34s} table {want:>8s}  export {got:>8s}")
        ok &= passed
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
