"""The run manifest every result file carries.

Scripts that embed their seeds in the source are reproducible but not recordable: nothing in the
output says which seed, which package versions, which commit. Every stage writes
`{"manifest": {...}, ...payload}` so the numbers can be traced.
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _git(*args: str) -> str | None:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, check=True, cwd=ROOT).stdout.strip()
    except Exception:
        return None


def package_versions() -> dict:
    versions = {"python": platform.python_version()}
    # stdout is redirected because `medmnist` is installed without its torch requirement (see
    # envs/priors.yml) and its __init__ prints an install hint when that import fails; every log
    # would otherwise open with a line telling the reader to install packages they do not need.
    with contextlib.redirect_stdout(io.StringIO()):
        for name in ("numpy", "scipy", "sklearn", "matplotlib", "PIL", "yaml", "openai",
                     "medmnist", "torch", "torchvision"):
            try:
                versions[name] = getattr(__import__(name), "__version__", "?")
            except Exception:
                pass
    return versions


def _jsonable(x):
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if hasattr(x, "tolist"):
        return x.tolist()
    if isinstance(x, Path):
        return str(x)
    return x


class Run:
    """Context for one stage invocation.

        with Run("fit", dict(model=model, seed=seed), seeds=[seed]) as run:
            ...
            run.write(out, dict(rows=rows))
    """

    def __init__(self, stage: str, params: dict, seeds=None, deterministic: bool | None = None):
        self.stage, self.params, self.seeds, self.deterministic = stage, params, seeds, deterministic
        self.t0 = time.time()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def manifest(self) -> dict:
        head = _git("rev-parse", "HEAD")
        return {
            "stage": self.stage,
            "params": _jsonable(self.params),
            "seeds": _jsonable(self.seeds),
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

    def write(self, path, payload: dict) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"manifest": self.manifest(), **_jsonable(payload)}, indent=1))
