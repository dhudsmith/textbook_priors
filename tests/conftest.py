import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

CONFIG = yaml.safe_load((ROOT / "config/config.yaml").read_text())
RELEASE = yaml.safe_load((ROOT / CONFIG["release"]).read_text())
DATASETS = list(CONFIG["datasets"])


@pytest.fixture(scope="session")
def cfg():
    return CONFIG


@pytest.fixture(scope="session")
def release():
    return RELEASE
