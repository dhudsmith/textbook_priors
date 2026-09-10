#!/usr/bin/env bash
# Runs once, inside the freshly created environment (Snakemake sets CONDA_PREFIX). medmnist 3.0.2
# without its torch/torchvision requirements: only medmnist.info and medmnist.evaluator are used
# here, and `import medmnist` tolerates the missing Dataset dependencies (it prints one line).
set -euo pipefail
"$CONDA_PREFIX/bin/pip" install --no-deps "medmnist==3.0.2"
