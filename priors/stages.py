"""The workflow's computations, one entry point per unit of parallel work.

Each stage is a pure function of `config/config.yaml`, its command-line cell and the seed it
derives from them, and writes ONE JSON file: {"manifest": {...}, ...payload}. Nothing here prints
a table; tables and figures are drawn from those files by the report stages.

    render-prompts DATASET --out FILE   the two prompt strings for one dataset (stage 2)

Run with  python -m priors.stages <stage> [args]
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

import yaml

from . import data, prompts
from .manifest import Run

CONFIG = yaml.safe_load(Path(os.environ.get("PRIORS_CONFIG", "config/config.yaml")).read_text())


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
    p = sub.add_parser("render-prompts"); p.add_argument("dataset"); p.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.stage == "render-prompts":
        render_prompts(a.dataset, a.out)
    else:
        raise SystemExit(f"stage {a.stage} not implemented yet")


if __name__ == "__main__":
    main()
