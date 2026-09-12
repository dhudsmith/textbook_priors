"""Fixtures for the smoke tier: the repository's fixed inputs, loaded once.

The tests read the bank and the release through `priors.data`, the same loader the rules use, so a
rule and its test cannot disagree about what an input says.
"""
import contextlib
import io
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from priors import data  # noqa: E402  (after the path insert)

CONFIG = yaml.safe_load((ROOT / "config/config.yaml").read_text())

# Every bank file in the repository, not only the six the talk version scores: they are committed
# inputs, and a schema rule that held on six files and failed on twelve would be no rule at all.
BANK_DATASETS = sorted(p.stem for p in (ROOT / CONFIG["conceptdir"]).glob("*.yaml"))

# The datasets this workflow actually runs (config/config.yaml), which is what the prompts,
# the label maps in config/medmnist.yaml and every later stage are defined over.
RUN_DATASETS = list(CONFIG["datasets"])

# `medmnist` is installed without its torch requirement (envs/priors.yml), and its __init__ prints
# an install hint when that import fails; the tests want INFO and the evaluator, both pure python.
with contextlib.redirect_stdout(io.StringIO()):
    import medmnist  # noqa: E402
    from medmnist import evaluator as medmnist_evaluator  # noqa: E402

INFO = medmnist.INFO


@pytest.fixture(scope="session")
def config():
    return CONFIG


@pytest.fixture(scope="session")
def release():
    return data.load_release(ROOT / CONFIG["release"])


@pytest.fixture(scope="session")
def literature():
    return data.load_literature(ROOT / CONFIG["literature"])


@pytest.fixture(scope="session")
def banks():
    """Every bank file, keyed by dataset."""
    return {d: data.load_bank(d, ROOT / CONFIG["conceptdir"]) for d in BANK_DATASETS}


@pytest.fixture(scope="session")
def evaluator():
    return medmnist_evaluator
