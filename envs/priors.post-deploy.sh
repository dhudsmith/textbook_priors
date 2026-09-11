#!/usr/bin/env bash
# Runs once, inside the environment envs/priors.yml just created, before any job uses it.
#
# `medmnist` is used for two pure-python things: the `INFO` label maps that the smoke target holds
# config/medmnist.yaml to, and `evaluator.getAUC`, this project's AUC convention (WORKFLOW.md
# section 3). The package declares torch and torchvision, which nothing in this environment
# imports - torch lives in envs/priors_torch.yml and is wanted in the features stage alone - so it
# is installed with --no-deps. That is an option to pip rather than a requirement, so it cannot be
# expressed in the `pip:` section of the environment file, which is why this script exists.
set -euo pipefail
pip install --no-deps --no-cache-dir medmnist==3.0.2
