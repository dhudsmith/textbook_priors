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
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
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


def strip_private(manifest: dict) -> dict:
    """A manifest as the site may see it: the owner-only key path never leaves the archive."""
    out = json.loads(json.dumps(manifest))
    out.get("params", {}).pop("key_file", None)
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
            "test_n": len(classify[d]["index"]) if isinstance(classify[d].get("index"), list) else None,
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
         "jobs": len(glob.glob(str(ROOT / "results/features/*.npz"))), "unit": "datasets"},
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
        },
        "run": {
            "git_commit": run["git_commit"], "git_dirty": run.get("git_dirty"),
            "written": run["written"], "host": run["host"], "versions": run["versions"],
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


def export_samples(datasets: list[str], per_class: int, cap: int) -> dict:
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
            groups = {str(c): np.flatnonzero(labels == c) for c in sorted(set(labels.tolist()))}
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
                "host": chunk["manifest"]["host"],
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
        lead = e["lead"]
        e["lead"] = lead if len(lead) <= 600 else lead[:597].rsplit(" ", 1)[0] + "…"
    days = sorted({e["date"] for e in entries})
    return {"source": "SESSION_LOG.md", "days": days, "entries": entries,
            "kinds": [{"id": "direct", "label": "the user set the direction"},
                      {"id": "build", "label": "something was written"},
                      {"id": "run", "label": "compute was submitted"},
                      {"id": "decide", "label": "a choice was settled"},
                      {"id": "catch", "label": "something wrong was found"},
                      {"id": "rewind", "label": "work was removed"}],
            "kind_note": ("The kind of each entry is the one hand-assigned field in this export "
                          "(talk/scripts/export_talk_data.py); everything else is the file's own "
                          "heading and first paragraph.")}


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
    samples = export_samples(datasets, args.per_class, args.cap)
    archive = export_archive(datasets, args.archive_records, study["study"]["primary"])
    timeline = export_timeline()
    figures = copy_figures()

    for meta in study["datasets"]:
        meta["samples"] = samples[meta["name"]]
    study["figures"] = figures
    study["provenance"]["source_files"] = list(SOURCES)

    prov = {"run_git_commit": study["provenance"]["run_git_commit"],
            "exported": study["provenance"]["exported"]}
    write_json("data/archive_sample.json", {**archive,
                                            "provenance": {**prov, "source_files": [
                                                "results/score/*__test__concept__chunk00.json",
                                                "results/score/*__test__zero_shot__chunk00.json",
                                                "data/cache/sample/*.npz"]}})
    write_json("data/timeline.json", {**timeline,
                                      "provenance": {**prov, "source_files": ["SESSION_LOG.md"]}})
    write_json("data/contention.json", {**CONTENTION,
                                        "provenance": {**prov, "source_files": ["CHANGELOG.md"]}})
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
