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
        {"id": "zero_shot_thinking_off", "label": "zero-shot prompt, thinking off",
         "model": "qwen3.8-27b-fp8",
         "points": [{"jobs": 1, "s_per_call": 1.5, "calls_per_s": 0.67},
                    {"jobs": 24, "s_per_call": 42.8, "calls_per_s": 0.56}]},
        {"id": "concept_thinking_off", "label": "concept prompt, thinking off",
         "model": "qwen3.8-27b-fp8",
         "points": [{"jobs": 1, "s_per_call": 4.5, "calls_per_s": 0.22},
                    {"jobs": 48, "s_per_call": 89.0, "calls_per_s": 0.54}]},
        {"id": "concept_thinking_medium", "label": "concept prompt, thinking at medium",
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
    {"what": "An unfair pixel baseline that would have made the headline claim true by construction",
     "caught_by": "a person reading the plan", "source": "CHANGELOG.md 2026-09-09"},
    {"what": "Four generated rules that all ran the last model's command",
     "caught_by": "one chunk run before 270", "source": "CHANGELOG.md 2026-09-11"},
    {"what": "3,000 good answers filed under a third response field and recorded as missing",
     "caught_by": "a probe at the wire", "source": "CHANGELOG.md 2026-09-11"},
    {"what": "A 48-job wave that ran two hours and wrote nothing",
     "caught_by": "a timed call", "source": "CHANGELOG.md 2026-09-12"},
    {"what": "Thinking believed impossible, when the cause was our own 512-token budget",
     "caught_by": "a test at 15:20", "source": "CHANGELOG.md 2026-09-12"},
    {"what": "A second session switching the shared checkout onto its own branch mid-run",
     "caught_by": "a manifest field (git_commit)", "source": "SESSION_LOG.md 2026-09-13 12:25"},
    {"what": "An eleven-chunk thinking wave that would have died at its time limit",
     "caught_by": "one chunk run first, and a timed call", "source": "CHANGELOG.md 2026-09-12"},
]

# The report's own colour tables (priors/report.py), so a listener who has seen the PDF recognises
# them. Read, not re-chosen. The dark-mode steps are the same hues lifted off a dark surface.
ARM_STYLE = [
    {"id": "A", "label": "arm A: zero-shot (no labels)", "colour": "#7f7f7f", "dark": "#a8a8a6",
     "dash": "2 3", "labels": 0},
    {"id": "B", "label": "arm B: textbook only (no labels)", "colour": "#2ca02c", "dark": "#5cc45c",
     "dash": "6 4", "labels": 0},
    {"id": "C", "label": "arm C: concept scores", "colour": "#1f77b4", "dark": "#5aa7dd",
     "dash": None, "labels": "n"},
    {"id": "P", "label": "arm P: ImageNet features", "colour": "#d62728", "dark": "#f2615f",
     "dash": None, "labels": "n"},
    {"id": "CP", "label": "arm C+P: both blocks", "colour": "#762a83", "dark": "#b47ec0",
     "dash": "5 3", "labels": "n"},
]
LIT_STYLE = {"id": "lit", "label": "published ResNet-18 (224), fully supervised (Yang et al. 2023)",
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
    """A handful of real archived calls, with the image, the reply and the chunk's manifest.

    The site draws one at random so the speaker can show a live-looking call without buying one.
    Only chunk 00 of each dataset is read, and only the primary model's: four records is enough to
    show what an archived call is, and the archive is write-protected and read here and nowhere else.
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
            "kinds": [{"id": "direct", "label": "the user set the direction"},
                      {"id": "build", "label": "something was written"},
                      {"id": "run", "label": "compute was submitted"},
                      {"id": "decide", "label": "a choice was settled"},
                      {"id": "catch", "label": "something wrong was found"},
                      {"id": "rewind", "label": "work was removed"}],
            "kind_note": ("Only the kind of each entry was assigned by hand; the rest is the "
                          "file's own heading and first paragraph.")}


# ---------------------------------------------------------------------------------------------
# The effort snapshot: where the recorded work went, split two ways over the same hours.
#
# Two decompositions of one total, so a listener can lay them on top of each other: by lifecycle
# activity, and by who or what was doing it. Every hour in both bands comes from a timestamp in
# a file. The two attribution rules are stated here because neither is a field anyone wrote down:
#
#   machine hours    a job's own manifest: `written` is when it finished and `wall_seconds` how
#                    long it ran, so the pair is an interval. The activity is its Snakemake rule,
#                    through RULE_ACTIVITY below.
#   attended hours   the elapsed window a person and the agent were working: per day, first to
#                    last timestamped mark in that day's record. SESSION_LOG.md's prompt headings
#                    are the mark where they exist; for 2026-09-09, which predates the log, the
#                    day's git commits are. The activity of each interval between two marks is
#                    read off the commits that landed inside it, by the paths they touched
#                    (PATH_ACTIVITY), taking the activity with the most lines changed. An interval
#                    in which nothing was committed is direction and review.
#
# What this cannot do, and what the caption therefore has to say: the attended window cannot be
# split into human time and agent time. Nothing in the repository records which of the two was
# working at a given minute, and the gaps between prompts (median 35 min, longest 5h40m) are
# equally consistent with the person thinking, the agent building, and lunch. The window is an
# upper bound on the person's involvement, not a measurement of it.
# ---------------------------------------------------------------------------------------------

# A Snakemake rule's place in the project's lifecycle. Every rule that writes a manifest appears.
RULE_ACTIVITY = {
    "render_prompts": "setup", "fetch": "data", "sample": "data",
    "features": "measuring", "score": "measuring",
    "collect_scores": "analysis", "classify": "analysis", "evaluate": "analysis",
    "evaluate_across": "analysis",
    "figures": "reporting", "tables": "reporting",
}

# A changed path's place in the same lifecycle. Longest prefix wins; the fallback is setup,
# which is where the loose configuration of a repository lives.
PATH_ACTIVITY = [
    ("talk/", "reporting"),
    ("report/", "reporting"), ("docs/", "reporting"),
    ("CHANGELOG.md", "reporting"), ("README.md", "reporting"),
    ("TALK.md", "reporting"), ("SESSION_LOG.md", "reporting"),
    ("WORKFLOW.md", "planning"), ("CONCEPT_BANK.md", "planning"),
    ("CLAUDE.md", "planning"), ("data/concepts", "planning"),
    ("priors/", "code"), ("Snakefile", "code"), ("tests/", "code"),
    ("config/", "setup"), ("envs/", "setup"), ("profiles/", "setup"),
    ("scripts/", "setup"), (".github/", "setup"), (".gitignore", "setup"),
]

# Each activity twice: the name a caption uses, and the name that fits on the bar.
ACTIVITIES = [
    ("planning", "planning the study", "planning"),
    ("code", "writing the workflow and its tests", "writing code"),
    ("review", "direction and review", "direction, review"),
    ("reporting", "writing it down: changelog, report, talk", "writing it down"),
    ("setup", "configuration and environments", "config"),
    ("data", "preparing the data", "data prep"),
    ("analysis", "fitting and analysing", "analysis"),
    ("measuring", "the model answering, and the features", "the model answering"),
]


def _path_activity(path: str) -> str:
    for prefix, activity in PATH_ACTIVITY:
        if path.startswith(prefix):
            return activity
    return "setup"


def _commits() -> list[dict]:
    """Every commit, with when it landed and how many lines it changed per activity."""
    out = subprocess.run(["git", "log", "--numstat", "--format=C|%ct"],
                         cwd=ROOT, capture_output=True, text=True).stdout
    commits: list[dict] = []
    cur: dict | None = None
    for line in out.splitlines():
        if line.startswith("C|"):
            cur = {"t": datetime.fromtimestamp(int(line[2:])), "lines": {}, "total": 0}
            commits.append(cur)
            continue
        parts = line.split("\t")
        if len(parts) == 3 and parts[0].isdigit() and cur is not None:
            n = int(parts[0]) + int(parts[1])
            activity = _path_activity(parts[2])
            cur["lines"][activity] = cur["lines"].get(activity, 0) + n
            cur["total"] += n
    commits.sort(key=lambda c: c["t"])
    return commits


def _machine_jobs() -> list[dict]:
    """Every job that left a manifest: its rule, when it ended and how long it ran."""
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
                     "start": end - timedelta(seconds=float(wall)), "end": end})
    note("results/**/*.json (job manifests)")
    return jobs


def _cpu_hours() -> float:
    """Total CPU time Snakemake's own benchmarks recorded, which is not the same as wall time."""
    total = 0.0
    for path in sorted((ROOT / "benchmarks").rglob("*.tsv")):
        rows = list(csv.DictReader(path.read_text().splitlines(), delimiter="\t"))
        for row in rows:
            value = row.get("cpu_time")
            if value not in (None, "", "-"):
                total += float(value)
    note("benchmarks/**/*.tsv")
    return total / 3600


def export_effort(study: dict) -> dict:
    """Where the recorded work went: the same hours split by activity and by who did them.

    Reads only timestamps: job manifests for the machine, SESSION_LOG.md prompt headings and git
    commit times for the window a person and the agent worked in. Nothing here is estimated - the
    one thing the sources cannot do, separate the person from the agent, is left undone and said
    so in `caveats` rather than filled in.
    """
    jobs = _machine_jobs()
    commits = _commits()

    machine = {}
    for job in jobs:
        activity = RULE_ACTIVITY.get(job["stage"], "setup")
        machine[activity] = machine.get(activity, 0.0) + job["wall"] / 3600

    # How much wall clock the jobs actually occupied, which is far less than they consumed: the
    # union of their intervals. The ratio of the two is the mean number of jobs in flight.
    spans = sorted((j["start"], j["end"]) for j in jobs)
    merged: list[list[datetime]] = []
    for start, end in spans:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    busy_h = sum((b - a).total_seconds() for a, b in merged) / 3600
    machine_h = sum(machine.values())

    # The attended window, day by day, from whichever record covers that day.
    prompts: dict[str, list[datetime]] = {}
    for line in read_text("SESSION_LOG.md").splitlines():
        m = HEADING.match(line)
        if m:
            date, time, _ = m.groups()
            prompts.setdefault(date, []).append(
                datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M"))
    commit_days: dict[str, list[datetime]] = {}
    for c in commits:
        commit_days.setdefault(c["t"].strftime("%Y-%m-%d"), []).append(c["t"])

    attended: dict[str, float] = {}
    days, uncommitted = [], 0
    for date in sorted(set(prompts) | set(commit_days)):
        marks = sorted(prompts.get(date) or commit_days.get(date, []))
        source = "SESSION_LOG.md" if prompts.get(date) else "git commits"
        hours = (marks[-1] - marks[0]).total_seconds() / 3600 if len(marks) > 1 else 0.0
        days.append({"date": date, "marks": len(marks), "source": source,
                     "first": marks[0].strftime("%H:%M"), "last": marks[-1].strftime("%H:%M"),
                     "hours": round(hours, 3),
                     "prompts": len(prompts.get(date, []))})
        for a, b in zip(marks, marks[1:]):
            gap = (b - a).total_seconds() / 3600
            if gap <= 0:
                continue
            tally: dict[str, int] = {}
            for c in commits:
                if a <= c["t"] <= b:
                    for k, v in c["lines"].items():
                        tally[k] = tally.get(k, 0) + v
            if tally:
                activity = max(tally.items(), key=lambda kv: kv[1])[0]
            else:
                activity, uncommitted = "review", uncommitted + 1
            attended[activity] = attended.get(activity, 0.0) + gap
    attended_h = sum(attended.values())

    n_prompts = sum(len(v) for v in prompts.values())
    lines = sum(c["total"] for c in commits)
    calls = study["archive"]["calls"]

    activities = [
        {"id": key, "label": label, "short": short,
         "hours": round(machine.get(key, 0.0) + attended.get(key, 0.0), 3),
         "machine_hours": round(machine.get(key, 0.0), 3),
         "attended_hours": round(attended.get(key, 0.0), 3)}
        for key, label, short in ACTIVITIES
    ]
    activities = [a for a in activities if a["hours"] > 0]
    for a in activities:
        a["actor"] = "machine" if a["machine_hours"] > a["attended_hours"] else "attended"

    actors = [
        {"id": "attended", "label": "one person and the coding agent, at the keyboard",
         "short": "person + agent",
         "hours": round(attended_h, 3),
         "detail": f"{n_prompts} prompts, {len(commits)} commits, "
                   f"{lines:,} lines changed across {len(days)} days"},
        {"id": "machine", "label": "the cluster and the model service",
         "short": "the cluster and the model service",
         "hours": round(machine_h, 3),
         "detail": f"{len(jobs)} jobs, {calls:,} model calls, "
                   f"{busy_h:.1f} h of wall clock at {machine_h / busy_h:.1f} jobs at once"},
    ]

    return {
        "total_hours": round(machine_h + attended_h, 3),
        "activities": activities,
        "actors": actors,
        "counts": {"prompts": n_prompts, "commits": len(commits), "lines_changed": lines,
                   "jobs": len(jobs), "calls": calls, "days": len(days),
                   "uncommitted_intervals": uncommitted},
        "machine": {"wall_hours": round(machine_h, 3), "cpu_hours": round(_cpu_hours(), 3),
                    "busy_wall_hours": round(busy_h, 3),
                    "mean_concurrency": round(machine_h / busy_h, 2),
                    "first_job": min(j["start"] for j in jobs).isoformat(timespec="seconds"),
                    "last_job": max(j["end"] for j in jobs).isoformat(timespec="seconds")},
        "attended": {"hours": round(attended_h, 3), "days": days},
        "per_prompt": {"machine_hours": round(machine_h / n_prompts, 2),
                       "calls": round(calls / n_prompts),
                       "jobs": round(len(jobs) / n_prompts, 1),
                       "lines_changed": round(lines / n_prompts)},
        "method": [
            "Machine hours are each job manifest's own wall_seconds, summed; the activity is the "
            "Snakemake rule that wrote it.",
            "Attended hours are, per day, the elapsed time from the first to the last timestamped "
            "mark in that day's record: SESSION_LOG.md's prompt headings, or - for 2026-09-09, "
            "which predates the log - that day's git commits.",
            "An attended interval's activity is the one with the most lines changed by the "
            "commits that landed inside it; an interval that committed nothing is direction and "
            "review.",
        ],
        "caveats": [
            "The attended window cannot be split into human time and agent time. Nothing in the "
            "repository records which of the two was working in a given minute, so the window is "
            "an upper bound on one person's involvement, not a measurement of it.",
            "It also contains breaks: the gaps between prompts run from 3 minutes to 5h40m.",
            "Machine hours are job wall time. The score jobs spent nearly all of it waiting on a "
            f"shared model service, so only {_cpu_hours():.1f} h of it was this project's own CPU "
            "(benchmarks/**/*.tsv) and the service's GPU time is not metered here.",
            "Only surviving results are counted. Work that was rerun or rewound - arm D, the "
            "deleted archive - left no manifest behind and so appears nowhere.",
            "An attended interval takes the activity of whichever commits landed in it, so an "
            "hour that wrote a long changelog entry alongside a short rule counts as writing it "
            "down. The prose-heavy activities are flattered by that rule.",
            "2026-09-09, the planning day, predates SESSION_LOG.md, so its window is that day's "
            "first-to-last commit rather than its first-to-last prompt.",
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
                                 "SESSION_LOG.md", "git log --numstat"]}})
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
    print(f"  effort.json           {effort['machine']['wall_hours']:.0f} h machine + "
          f"{effort['attended']['hours']:.0f} h attended, {len(effort['activities'])} activities")
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
