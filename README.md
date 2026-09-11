# Textbook priors over visual features

Can a vision-language model's textbook knowledge of what pathology looks like stand in for
labelled data? On six MedMNIST 2D benchmarks a VLM scores each image against a cited bank of
diagnostic visual features, and four arms — two label-free, two label-matched — say what those
scores are worth in the currency of labelled images. The whole study, from the fixed inputs to the
technical report, is one Snakemake workflow on Palmetto2. The plan and the three hypotheses are
`WORKFLOW.md`; dated findings are `CHANGELOG.md`; the talk narrative is `TALK.md`.

```bash
snakemake --profile profiles/palmetto            # everything, on SLURM
snakemake --profile profiles/palmetto -n         # dry run: inspect the DAG
snakemake --profile profiles/local -j 2 prompts  # one stage by name
```

The workflow is being built one stage at a time; the foot of the `Snakefile` lists the rules still
to come, and the table below marks what exists today.

## The stages

| # | Stage | What happens | Jobs | Built |
|---|---|---|---|---|
| 0 | **Smoke** | The tests: bank schema, label maps, prompts, the arm-B estimator, the metric | 1 | |
| 1 | **Sample** | Per dataset: the seeded 500-image test sample and 2000-image labelled pool | 6 | |
| 2 | **Score** | Per dataset: render both prompts; then the VLM calls, archived raw | 6 + 270 | prompts |
| 3 | **Features** | Per dataset: ImageNet ResNet-18 penultimate features | 6 | |
| 4 | **Classify** | Per dataset: arms A, B, C, P over the curve, and the permutation controls | 6 | |
| 5 | **Evaluate** | AUC, the paired bootstrap, n_B; then the sign tests and the ladder | 6 + 1 | |
| 6 | **Report** | Three figures, the tables, the technical report PDF | 3 | |

## Layout

```
Snakefile              the whole workflow, one file, numbered stages
config/config.yaml     grids, seeds, caps, per-rule cpus / memory / runtime
config/medmnist.yaml   the pinned release: file names, MD5s, split sizes, label maps
profiles/palmetto/     SLURM executor settings (account, partition, job caps)
profiles/local/        run in the current allocation instead of submitting
envs/                  the conda environments the rules run in
priors/                the code the workflow executes, and nothing else
tests/                 the smoke tier
data/concepts/         the concept bank, committed: the project's prior knowledge
data/raw               symlink to the raw MedMNIST releases on project storage; gitignored
results/               one JSON per unit of work, each with a manifest
results/score/         the raw VLM response archive, write-protected once written
benchmarks/            wall time and peak memory per job
report/                report.tex, references.bib, generated tables/ and figs/
logs/                  one log per job
CONCEPT_BANK.md        how the bank was built, and the rules the smoke tier enforces
SESSION_LOG.md         timestamped record of how the work was directed
```

## `priors/`: what each module does

| module | role |
|---|---|
| `data.py` | The two fixed inputs — the concept bank and the pinned release — read and hashed in one place. |
| `prompts.py` | The concept and zero-shot prompt strings, rendered from the bank and the label map. |
| `stages.py` | **The workflow driver.** One entry point per unit of parallel work. |
| `manifest.py` | The run manifest every result carries. |

## Where the data comes from

Two inputs are fixed before the workflow runs and no rule refetches or re-verifies them
(`WORKFLOW.md` §4):

- **The concept bank**, `data/concepts/*.yaml`: built outside the workflow by the procedure in
  `CONCEPT_BANK.md`, with every feature and every class fingerprint carrying a citation. Expert
  review is **simulated** — no clinician has reviewed these files, and each says so.
- **The MedMNIST v2 224-pixel releases** (Zenodo record 10519652), on project storage and reached
  through the `data/raw` symlink. `config/medmnist.yaml` records each file's name, MD5, size, split
  sizes and label map, read from the `medmnist` package rather than retyped; the smoke target holds
  that file to the installed package.

## Reproducibility

`rule all` builds a technical report, not a manuscript: the question, the provenance, the methods
as executed, every table and figure, the diagnostics and the run record. No number in it is typed
by hand. Every result carries a manifest — parameters, seeds, commit, package versions, host, wall
time — and every VLM response is archived raw with its served model name and prompt hash, so
everything downstream of the model is a deterministic function of the archive.

## Setup

Snakemake on `PATH` (`conda activate snakemake`); the workflow builds its own environments from
`envs/` on first use. `profiles/palmetto/config.yaml` carries the account and partition. The API
key for the VLM service will be read from an owner-only file whose path enters
`config/config.yaml` with the scoring rules, and appears nowhere else.
