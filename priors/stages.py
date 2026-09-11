"""The workflow's computations, one entry point per unit of parallel work.

Each stage is a pure function of `config/config.yaml`, its command-line cell and the seed it
derives from them, and writes ONE JSON file: {"manifest": {...}, ...payload}. Nothing here prints
a table; tables and figures are drawn from those files by the report stages.

    sample DATASET --out FILE --arrays FILE   the test sample and the labelled pool (stage 1)
    render-prompts DATASET --out FILE          the two prompt strings for one dataset (stage 2)

Run with  python -m priors.stages <stage> [args]
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
import yaml

from . import data, prompts, sample as sampling
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


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("sample"); p.add_argument("dataset")
    p.add_argument("--out", required=True); p.add_argument("--arrays", required=True)
    p = sub.add_parser("render-prompts"); p.add_argument("dataset"); p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.stage == "sample":
        sample(a.dataset, a.out, a.arrays)
    elif a.stage == "render-prompts":
        render_prompts(a.dataset, a.out)
    else:
        raise SystemExit(f"stage {a.stage} not implemented yet")


if __name__ == "__main__":
    main()
