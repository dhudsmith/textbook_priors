"""The workflow's computations, one entry point per unit of parallel work.

Each stage is a pure function of `config/config.yaml`, its command-line cell and the seed it
derives from them, and writes ONE JSON file: {"manifest": {...}, ...payload}. Nothing here prints
a table; tables and figures are drawn from those files by the report stages.

    sample DATASET --out FILE --arrays FILE     the test sample and the labelled pool (stage 1)
    render-prompts DATASET --out FILE            the two prompt strings for one dataset (stage 2)
    probe DATASET MODEL --out FILE               ten images through the service (stage 2, opt-in)

Run with  python -m priors.stages <stage> [args]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import yaml

from . import data, llm, prompts, sample as sampling, score
from .manifest import Run

CONFIG = yaml.safe_load(Path(os.environ.get("PRIORS_CONFIG", "config/config.yaml")).read_text())


def sample(dataset: str, out: str, arrays: str) -> None:
    """Draw one dataset's test sample and labelled pool out of its release file.

    Two outputs, not one: the JSON is the unit of work (the drawn indices, the labels, the counts a
    reader should check) and the images ride in an .npz beside the cache, not in results/, because
    a quarter of a gigabyte of pixels per dataset is an input to later stages rather than a result
    anything reads. `data/cache` is a symlink onto the project filesystem (WORKFLOW.md 11)."""
    spec = CONFIG["sample"]
    release = data.load_release(CONFIG["release"])
    described = release.dataset(dataset)
    path = Path(CONFIG["rawdir"]) / described["file"]

    with Run("sample", dict(dataset=dataset, **spec), seeds=[spec["seed"]]) as run:
        drawn = {"test": sampling.draw(path, "test", spec["test_n"], spec["seed"]),
                 "pool": sampling.draw(path, "train", spec["pool_n"], spec["seed"])}

        Path(arrays).parent.mkdir(parents=True, exist_ok=True)
        np.savez(arrays, **{f"{split}_{key}": drawn[split][key]
                            for split in drawn for key in ("images", "labels", "indices")})

        run.write(out, dict(
            dataset=dataset,
            source_file=str(path),
            md5_224=described["md5_224"],      # recorded from the pinned release, not recomputed
            release_sha256=release.sha256,
            size=CONFIG["size"],
            arrays={"file": arrays,
                    "images": {split: {"shape": list(drawn[split]["images"].shape),
                                       "dtype": str(drawn[split]["images"].dtype)}
                               for split in drawn}},
            splits={split: {k: v for k, v in drawn[split].items() if k != "images"}
                    for split in drawn},
        ))


def render_prompts(dataset: str, out: str) -> None:
    """Turn one dataset's concept bank and label map into both prompt strings.

    No LLM call, no image, no randomness: the output is a deterministic function of the two fixed
    inputs and three config values, and it carries the hash of each input and of each rendered
    prompt so that a score archive can be traced to the exact strings that produced it."""
    size, anchors = CONFIG["size"], CONFIG["vlm"]["prompt"]["anchors"]
    bank = data.load_bank(dataset, CONFIG["conceptdir"])
    release = data.load_release(CONFIG["release"])
    classes = release.class_names(dataset)
    data.check_classes(bank, classes)

    with Run("render_prompts", dict(dataset=dataset, size=size, anchors=anchors)) as run:
        payload = prompts.render(bank, classes, size=size, anchors=anchors)
        run.write(
            out,
            dict(
                dataset=dataset,
                bank_file=bank.file,
                bank_sha256=bank.sha256,
                release_file=release.file,
                release_sha256=release.sha256,
                **payload,
            ),
        )


def probe(dataset: str, model: str, out: str) -> None:
    """Ten images of one dataset through one model, on a compute node, outside `rule all`.

    What it is for (WORKFLOW.md section 9, step 3): that a compute node reaches the service at all,
    that the archive and the manifest carry what they promise - the served model name, the prompt
    hash, the temperature and the reasoning setting - and that a malformed answer is recorded as
    missing rather than guessed. The last is not simulated: one extra call is made with a token
    budget of one, which truncates the reply, and the result shows the content retry firing and the
    answer ending up empty.

    It writes no response archive. `results/score/` is written by the scoring rules alone and is
    fixed from the moment it exists (CLAUDE.md); a probe that wrote into it would make re-scoring
    an accident rather than a decision.
    """
    vlm = CONFIG["vlm"]
    spec = vlm["probe"]
    rendered = json.loads(Path(f"{CONFIG['outdir']}/prompts/{dataset}.json").read_text())
    arrays = np.load(f"{CONFIG['cachedir']}/{dataset}.npz")
    images = arrays["test_images"][: spec["n"]]

    client = llm.Client(model=model, base_url=vlm["base_url"], key_file=vlm["key_file"],
                        temperature=vlm["temperature"], reasoning=vlm["reasoning"],
                        retries=vlm["transport_retries"], timeout=vlm["timeout"])

    params = dict(dataset=dataset, model=model, n=spec["n"], temperature=vlm["temperature"],
                  reasoning=vlm["reasoning"], max_tokens=vlm["max_tokens"], retries=vlm["retries"],
                  concept_prompt_sha256=rendered["prompts"]["concept"]["sha256"],
                  zero_shot_prompt_sha256=rendered["prompts"]["zero_shot"]["sha256"],
                  bank_sha256=rendered["bank_sha256"], key_file=vlm["key_file"])

    with Run("probe", params) as run:
        records = []
        for position, image in enumerate(images):
            url = score.png_data_url(image)
            records.append({
                "position": position,
                "index": int(arrays["test_indices"][position]),
                "label": int(arrays["test_labels"][position]),
                "concept": score.ask_one(client, rendered["prompts"]["concept"], url, "concept",
                                         rendered["concepts"], vlm["max_tokens"], vlm["retries"]),
                "zero_shot": score.ask_one(client, rendered["prompts"]["zero_shot"], url,
                                           "zero_shot", rendered["classes"], vlm["max_tokens"],
                                           vlm["retries"]),
            })

        # The malformed path, against the real service rather than a fixture: one token cannot hold
        # a JSON object, so the reply is truncated, the content retry fires, and the answer is
        # recorded missing. `complete: false` here is the probe passing, not failing.
        truncated = score.ask_one(client, rendered["prompts"]["concept"],
                                  score.png_data_url(images[0]), "concept", rendered["concepts"],
                                  spec["malformed_max_tokens"], vlm["retries"])

        complete = [r for r in records if r["concept"]["complete"]]
        latencies = sorted(reply["elapsed_s"] for r in records for kind in ("concept", "zero_shot")
                           for reply in r[kind]["replies"])
        run.write(out, dict(
            dataset=dataset, model=model,
            served_model=records[0]["concept"]["replies"][0]["served_model"],
            n=len(records),
            calls=len(latencies),
            seconds_per_call={"median": latencies[len(latencies) // 2],
                              "min": latencies[0], "max": latencies[-1],
                              "total": round(sum(latencies), 2)},
            concept_complete=len(complete),
            zero_shot_complete=sum(r["zero_shot"]["complete"] for r in records),
            zero_shot_sums_to_one=sum(bool(r["zero_shot"]["sums_to_one"]) for r in records),
            malformed_check={"requested_max_tokens": spec["malformed_max_tokens"],
                             "content_attempts": truncated["content_attempts"],
                             "complete": truncated["complete"],
                             "recorded_missing": not truncated["complete"],
                             "replies": truncated["replies"]},
            records=records,
        ))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("sample"); p.add_argument("dataset")
    p.add_argument("--out", required=True); p.add_argument("--arrays", required=True)
    p = sub.add_parser("render-prompts"); p.add_argument("dataset"); p.add_argument("--out", required=True)
    p = sub.add_parser("probe"); p.add_argument("dataset"); p.add_argument("model")
    p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.stage == "sample":
        sample(a.dataset, a.out, a.arrays)
    elif a.stage == "render-prompts":
        render_prompts(a.dataset, a.out)
    elif a.stage == "probe":
        probe(a.dataset, a.model, a.out)
    else:
        raise SystemExit(f"stage {a.stage} not implemented yet")


if __name__ == "__main__":
    main()
