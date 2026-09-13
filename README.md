# Textbook priors over visual features

Can a vision-language model's textbook knowledge of what pathology looks like stand in for
labelled data? On the twelve MedMNIST 2D benchmarks a VLM scores each image against a cited bank
of diagnostic visual features, and four arms — two label-free, two label-matched — say what those
scores are worth in the currency of labelled images. The whole study, from the fixed inputs to the
technical report, is one Snakemake workflow on Palmetto2. The plan and the four hypotheses are
`WORKFLOW.md`; dated findings are `CHANGELOG.md`; the talk narrative is `TALK.md`.

```bash
snakemake --profile profiles/palmetto             # everything, on SLURM
snakemake --profile profiles/palmetto -n          # dry run: inspect the DAG
snakemake --profile profiles/local -j 2 smoke     # the tests, seconds
snakemake --profile profiles/local -j 2 prompts   # one stage by name
snakemake --profile profiles/local -j 2 -F smoke  # re-run the tests after editing a bank file

# opt-in, outside `rule all`: ten images through the service on a compute node
snakemake --profile profiles/palmetto results/probe/pneumoniamnist__qwen3.8-27b-fp8.json

# opt-in, outside `rule all`, no LLM calls: a human-readable txt render of every prompt
snakemake --profile profiles/local -j 2 prompts_txt
```

Every rule takes the `smoke` marker as an input, so nothing is computed on code that fails its
tests. The bank files are deliberately not inputs of `smoke`, so that editing one dataset's bank
invalidates that dataset alone; the last invocation above is how the schema tests are re-run after
such an edit, and the reasoning is in the Snakefile's stage-0 banner.

`rule all` is the technical report. A dry run from a clean clone is 616 jobs, 521 of them the
scoring fan-out; from the owner's checkout, where every result exists, it is nothing to be done.

## The stages

| # | Stage | What happens | Jobs |
|---|---|---|---|
| 0 | **Smoke** | The tests: bank schema, label maps, prompts, the sampler, the estimators, the metric | 1 |
| 1 | **Sample** | A release file missing from storage is fetched first; per dataset: the seeded test sample and labelled pool, capped at the official split | 4 + 12 |
| 2 | **Score** | Per dataset: render both prompts; then the VLM calls, archived raw, including H4's two readers | 12 + 521 |
| 3 | **Features** | Per dataset: ImageNet ResNet-18 penultimate features | 12 |
| 4 | **Classify** | Per dataset: arms A, B, C, P over the curve, the permutation controls, and every reader's probe; C and P alone for the multi-label chestmnist | 12 |
| 5 | **Evaluate** | AUC, the paired bootstrap, n_B; then the sign tests, the ladder and the reader chain | 12 + 1 |
| 6 | **Report** | Five figures, the tables, the technical report PDF | 3 |

## Layout

```
Snakefile              the whole workflow, one file, numbered stages
config/config.yaml     grids, seeds, caps, per-rule cpus / memory / runtime
config/medmnist.yaml   the pinned release: file names, MD5s, split sizes, label maps
profiles/palmetto/     SLURM executor settings (account, partition, job caps)
profiles/local/        run in the current allocation instead of submitting
envs/                  the conda environments the rules run in
priors/                the code the workflow executes, and nothing else
tests/                 the smoke tier: one module per kind of claim
data/concepts/         the concept bank, committed: the project's prior knowledge
data/literature/       the pinned published-benchmark table, committed: cited, not rerun
data/raw               symlink to the raw MedMNIST releases on project storage; gitignored
data/cache/sample/     symlink target: the sampled image arrays, one npz per dataset; gitignored
scripts/link_storage.sh  one-time setup: make those two symlinks
scripts/fetch_medmnist.sh  one release file from the pinned Zenodo record, resumable, MD5-checked
results/               one JSON per unit of work, each with a manifest
results/score/         the raw VLM response archive, write-protected once written
results/prompts_txt/   opt-in: a plain-text render of each prompt, for a human reader; no manifest
benchmarks/            wall time and peak memory per job
report/                report.tex, references.bib, generated tables/ and figs/
logs/                  one log per job
docs/                  reference notes on the LLM service: models, reasoning levels, throughput
CONCEPT_BANK.md        how the bank was built, and the rules the smoke tier enforces
SESSION_LOG.md         timestamped record of how the work was directed
```

## `priors/`: what each module does

| module | role |
|---|---|
| `data.py` | The three fixed inputs — the concept bank, the pinned release and the literature benchmarks — read and hashed in one place. |
| `sample.py` | The seeded samples, and the streaming reader that takes their rows out of a deflated release file without materialising the split. |
| `llm.py` | The boundary: one kind of call, the key read from an owner-only file, the reasoning effort and the API dialect, transport backoff, and what came back recorded verbatim. |
| `score.py` | The deterministic half of scoring: the image as a lossless PNG, and a reply parsed into a validated answer or a recorded absence. |
| `prompts.py` | The concept and zero-shot prompt strings, rendered from the bank and the label map. |
| `features.py` | Arm P's frozen ImageNet encoder, and the preprocessing that does not resize. |
| `classify.py` | Every estimator: the concept vectors, arm B's fingerprint match, the regression behind arms C and P, H4's cross-validated probe, and the two permutation controls. |
| `evaluate.py` | The AUC convention as a rank formula, the shared paired bootstrap, n_B, and the tests the hypotheses are decided by. |
| `report.py` | Every figure, table and number macro, from results/ alone — plus one table that also reads the pinned literature benchmarks. |
| `stages.py` | **The workflow driver.** One entry point per unit of parallel work. |
| `manifest.py` | The run manifest every result carries. |

## `tests/`: the smoke tier

| module | what it holds to what | tests |
|---|---|---|
| `test_bank.py` | the twelve committed bank files to the schema `CONCEPT_BANK.md` defines | 110 |
| `test_release.py` | `config/medmnist.yaml` to the installed `medmnist` package | 38 |
| `test_literature.py` | the pinned literature-benchmark table to the datasets the workflow runs and to `references.bib` | 4 |
| `test_prompts.py` | the two prompts to H2's separation, the renderer to its switches and its gloss, the txt render to the JSON, and the six archived datasets to the prompt hashes that bought them | 104 |
| `test_sample.py` | the streaming reader to a release-shaped fixture whose rows identify themselves, and the sample caps to the split sizes | 15 |
| `test_score.py` | the image encoding, the reply parser, the two retry policies, the exact request body each dialect sends, and the profile's caps against config's | 57 |
| `test_classify.py` | the estimators to fixtures small enough to check by hand, arm B and the one-vs-rest fit included | 21 |
| `test_evaluate.py` | the fast AUC to the package's evaluator on every task type, and the decision rules to the plan | 22 |
| `test_pipeline.py` | the analysis chain end to end, on an archive whose answer is known, single- and multi-label | 4 |
| `test_metrics.py` | the AUC convention to the package that defines it | 3 |

378 tests, run by the `smoke` rule before anything else.

## Where the data comes from

Three inputs are fixed before the workflow runs and no rule refetches, reruns or re-verifies them
(`WORKFLOW.md` §4):

- **The concept bank**, `data/concepts/*.yaml`: built outside the workflow by the procedure in
  `CONCEPT_BANK.md`, with every feature and every class fingerprint carrying a citation. Expert
  review is **simulated** — no clinician has reviewed these files, and each says so.
- **The MedMNIST v2 224-pixel releases** (Zenodo record 10519652), on project storage and reached
  through the `data/raw` symlink. Eight were downloaded before the workflow; the four the talk never
  needed are fetched by `rule fetch` from the same record when missing. `config/medmnist.yaml`
  records each file's name, MD5, size, split sizes and label map, read from the `medmnist` package
  rather than retyped; the smoke target holds that file to the installed package.
- **The published literature benchmarks**, `data/literature/benchmarks.yaml`: AUC and ACC for five
  fully supervised methods on these same twelve tasks, transcribed from Yang et al. 2023's Table 3 and
  cross-checked against that paper's own across-dataset average. Read into the report as a
  reconciliation point (`data/literature/README.md`), not rerun and not a comparison arm.

## Reproducibility

`rule all` builds a technical report, not a manuscript: the question, the provenance, the methods
as executed, every table and figure, the diagnostics and the run record. No number in it is typed
by hand. Every result carries a manifest — parameters, seeds, commit, package versions, host, wall
time — and every VLM response is archived raw with its served model name and prompt hash, so
everything downstream of the model is a deterministic function of the archive.

## Where the workflow runs

**From `~/Code/textbook_priors`, the owner's checkout.** Everything a run produces that is not
committed — `results/`, `benchmarks/`, `logs/` and Snakemake's own `.snakemake/` metadata — lives
in the checkout it ran from, and only that one persists. An agent session works in a throwaway
worktree under the runner's `_sessions/` tree which is recreated without warning, taking every
gitignored path with it; that is the place to edit, commit and push, not to run.

The two heavy directories are shared by every checkout, because `data/raw` and `data/cache` are
symlinks onto `/project/dane2/wficai/textbook_priors` (`scripts/link_storage.sh`). That is why a
lost workspace costs seconds rather than the sampled arrays — and it is also why **only one
checkout runs the workflow at a time**: two Snakemake instances would write the same cached npz.

It matters most for `results/score/`, the VLM response archive: 51,718 calls the plan treats as
fixed from the moment they are written (`WORKFLOW.md` §5, principle 7). A run from a throwaway
worktree would put that archive somewhere that disappears.

## Setup

Snakemake on `PATH` (`conda activate snakemake`); the workflow builds its own environments from
`envs/` on first use. `scripts/link_storage.sh` makes the two symlinks onto the project filesystem
(`data/raw` for the releases, `data/cache` for the sampled arrays) and is the only setup step a
fresh clone needs. `profiles/palmetto/config.yaml` carries the account and partition. The API
key for the VLM service is read from the owner-only file named by `vlm.key_file`, by
`priors/llm.py` and nowhere else: it never reaches a command line, a log or a manifest.
