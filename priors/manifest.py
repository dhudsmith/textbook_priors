"""The run manifest every result file carries.

Scripts that embed their seeds in the source are reproducible but not recordable: nothing in the
output says which seed, which package versions, which commit. Every stage writes
`{"manifest": {...}, ...payload}` so the numbers can be traced (WORKFLOW.md section 5, principle 5).
"""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Distribution names, looked up without importing anything: importing torch to read a version
# string would cost seconds and memory in the light tier, where it is not installed anyway.
DISTS = ("numpy", "scipy", "pandas", "scikit-learn", "matplotlib", "torch", "torchvision",
         "openai", "medmnist", "pillow", "PyYAML")


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True, cwd=ROOT).stdout.strip()
    except Exception:
        return None


def package_versions() -> dict:
    versions = {"python": platform.python_version()}
    for dist in DISTS:
        try:
            versions[dist] = version(dist)
        except PackageNotFoundError:
            pass
    return versions


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if hasattr(x, "tolist"):
        return x.tolist()
    if isinstance(x, Path):
        return str(x)
    if isinstance(x, float) and x != x:      # NaN is not JSON; null is
        return None
    return x


class Run:
    """Context for one stage invocation.

        with Run("score", dict(dataset=ds, model=m), seeds=None) as run:
            ...
            run.write(out, dict(rows=rows), extra=dict(served_model=...))
    """

    def __init__(self, stage: str, params: dict, seeds=None, deterministic: bool | None = None):
        self.stage, self.params, self.seeds, self.deterministic = stage, params, seeds, deterministic
        self.t0 = time.time()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def manifest(self, extra: dict | None = None) -> dict:
        head = _git("rev-parse", "HEAD")
        m = {
            "stage": self.stage,
            "params": jsonable(self.params),
            "seeds": jsonable(self.seeds),
            "deterministic": self.deterministic,
            "git_commit": head,
            "git_dirty": bool(_git("status", "--porcelain")) if head else None,
            "versions": package_versions(),
            "host": platform.node(),
            "slurm_job": os.environ.get("SLURM_JOB_ID"),
            "threads": {k: os.environ.get(k) for k in ("OMP_NUM_THREADS", "MKL_NUM_THREADS", "OPENBLAS_NUM_THREADS")},
            "argv": sys.argv,
            "wall_seconds": round(time.time() - self.t0, 2),
            "written": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }
        if extra:
            m.update(jsonable(extra))
        return m

    def write(self, path, payload: dict, extra: dict | None = None) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps({"manifest": self.manifest(extra), **jsonable(payload)}, indent=1))
        tmp.replace(path)
