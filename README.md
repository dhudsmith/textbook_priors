# Textbook priors over visual features

Can a vision-language model's textbook knowledge of what pathology looks like stand in for
labelled images? On the twelve MedMNIST v2 2D benchmarks, a VLM scores every image of a seeded
test sample against a cited bank of diagnostic visual features (`data/concepts/`, built outside
the workflow and committed as an input). Five arms predict on the same sample: the model's
zero-shot class distribution (A), the nearest textbook fingerprint with no labels (B), a logistic
regression on the concept scores with n labels (C), the same regression on frozen ImageNet
ResNet-18 features with the same n labels (P), and a ResNet-18 trained from scratch on the full
official split (E). Three pre-registered hypotheses with fixed decision rules (WORKFLOW.md §2):
substitution (the labels the pixel probe needs to reach the textbook), the bank against the
undirected model, and scale across four models. The whole analysis, from the pinned MedMNIST
release to the technical report PDF, is one Snakemake workflow on Palmetto2.

```bash
snakemake --profile profiles/palmetto                 # everything, on SLURM: the report
snakemake --profile profiles/palmetto -n              # dry run: inspect the DAG
snakemake --profile profiles/local -j 2 smoke         # the tests, seconds
snakemake --profile profiles/palmetto cache           # one stage by name
snakemake --profile profiles/palmetto results/score_probe/probe.json   # the ten-image probe
```

A fresh clone carries no data: `data/raw/` is fetched from the pinned Zenodo record on the first
run (`scripts/fetch_medmnist.sh`, MD5-checked) into `/scratch/$USER`, and the ImageNet weights
from their pinned URL. Scoring needs the RCD LLM key in `~/.config/rcd_llm/key` (owner-only;
the path is `vlm.key_file` in the config and the key appears nowhere else).

## The stages

The `Snakefile` reads top to bottom. Each stage is a labelled section.

| # | Stage | What happens | Jobs |
|---|---|---|---|
| 0 | **Smoke** | The tests: bank schema and anchors, label maps against the release pin, both prompts, the arm-B estimator, metric conventions, client retry; the torch tier's checks separately | 2 |
| 1 | **Fetch** | MedMNIST v2 from Zenodo record 10519652, one job per file, MD5-checked | 24 |
| 2 | **Cache** | uint8 arrays per official split at 224 and 28, streamed to memory-mappable `.npy`; the seeded test sample and labelled pool at 224 | 24 + 12 |
| 3 | **Score** | One chunk of 100 sampled images through one model with one prompt; every raw reply archived, protected | 477 |
| 4 | **Features** | ImageNet ResNet-18 penultimate features of the sampled images | 12 |
| 5 | **Train** | ResNet-18 from scratch, per dataset x {28, 224} x seed, on one A100 each | 72 |
| 6 | **Classify** | Arms A, B, C, P at every n and seed, and the permutation controls | 12 |
| 7 | **Evaluate** | AUC and ACC through the medmnist evaluator; the paired bootstrap; n_B; then the sign tests and the H3 ladder analysis | 12 + 1 |
| 8 | **Report** | Reconciliation against the published table; tables, number macros, three figures, the PDF | 4 |

Targets: `all` (the report), `smoke`, `cache`, `score`, `features`, `train`, `classify`,
`evaluate`, `report`. The probe is opt-in and outside `all`.

## Layout

```
Snakefile                the whole workflow, one file, nine labelled stages
config/config.yaml       every grid, seed, model and knob; per-rule cpus / memory / runtime; GPU switches
config/medmnist.yaml     the pinned release: file names, MD5s, split sizes, label maps
config/published.yaml    the MedMNIST v2 ResNet-18 rows arm E is reconciled against
profiles/palmetto/       SLURM executor; job, core and per-model llm_* caps
profiles/local/          dry runs, smoke, touch
envs/                    priors.yml (numpy tier)  priors_torch.yml  priors_llm.yml, with post-deploy scripts
priors/                  the code the workflow executes, and nothing else
tests/                   the smoke tier (pytest); test_torch.py runs in the torch environment
scripts/                 fetch_medmnist.sh
data/concepts/           the twelve concept-bank files and their README, committed
data/raw -> scratch      MedMNIST files; data/cache the arrays and samples; both gitignored
results/                 one JSON per unit of work, arrays beside it; results/score/ is the response archive
benchmarks/  logs/       per job
report/                  report.tex, references.bib; tables/ and figs/ are generated
WORKFLOW.md              the scientific and engineering plan; CONCEPT_BANK.md the bank procedure
CHANGELOG.md             dated findings, decisions and corrections
TALK.md                  the presentation narrative; constrains nothing
```

## `priors/`: what each module does

| module | role |
|---|---|
| `data.py` | The release pin, label maps and task strings; the bank and its validation rules; the seeded sample |
| `cache.py` | npz -> memory-mappable uint8 `.npy` per split, streamed; the sample file |
| `prompts.py` | The concept prompt (anchors rendered, no class named) and the zero-shot prompt (no concept named); parsing that never guesses |
| `llm.py` | The OpenAI-compatible client: key from an owner-only file, backoff, request shape |
| `score.py` | One archive chunk; the opt-in probe |
| `features.py` | ImageNet ResNet-18 penultimate features (arm P) |
| `train.py` | Arm E: ResNet-18 from scratch with the published recipe, evaluated on the full split and the sample |
| `classify.py` | Arms A, B, C, P and the permutation controls; nested stratified subsets; the shared LR |
| `evaluate.py` | AUC/ACC via `medmnist.evaluator`; the paired bootstrap; n_B; sign tests; the ladder ANOVA, trend contrast, Friedman/Nemenyi |
| `report.py` | Reconciliation, every table and number macro, the three figures, from results/ alone |
| `stages.py` | **The workflow driver.** One entry point per unit of parallel work |
| `manifest.py` | The run manifest every result carries |

## Where the data comes from

MedMNIST v2 (Yang et al. 2023), Zenodo record 10519652, data version 3, at 28 and 224 pixels,
downloaded by file name and verified against the MD5 the `medmnist` package (3.0.2) records; the
smoke test holds `config/medmnist.yaml` to the installed package. The concept bank's provenance is
`data/concepts/README.md`. The ImageNet ResNet-18 weights are torchvision's IMAGENET1K_V1, pinned
by URL and hash prefix. The VLMs are served by the RCD LLM service; every response is archived
with the served model name and the prompt and bank hashes.

## Reproducibility

Every number in `report/report.pdf` is generated into `report/tables/` from `results/`; the
report cannot state a value the run did not produce. Every result carries a manifest: parameters,
seeds, commit and dirty flag, package versions, host, thread pins, wall time. The response archive
is written once, protected, and read deterministically by everything downstream; re-scoring is a
deliberate act.

## Setup

Snakemake on `PATH` (`conda activate snakemake`); the workflow builds its three environments from
`envs/` on first use. `profiles/palmetto/config.yaml` carries the account, partition and the
per-model throttles. The LLM key lives in `~/.config/rcd_llm/key`.
