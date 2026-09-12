# Textbook priors over visual features

A small, reproducible medical-imaging study, built as one Snakemake workflow on Palmetto2 with an
AI coding agent, and the running example for *Reproducible scientific computing with AI coding
agents* (Clemson HPC Day). This file is the scientific and engineering plan; `TALK.md` carries the
talk narrative; `CONCEPT_BANK.md` the procedure that built the bank. Workflow conventions are the
`research-workflow` skill (`~/.claude/skills/research-workflow/SKILL.md`).

This is the **talk version**: six datasets, four vision-language models, two label-free arms and
two label-matched arms, and a report a person can read in one sitting. The full version (twelve
datasets, the from-scratch CNN ceiling with its reconciliation against the published table, the
blocked ANOVA over the model ladder) lives on branch `claude/textbook-priors-workflow-2kdgap`; §10
lists what was cut and why.

---

## 1. The question

A multimodal language model carries textbook knowledge about what pathology looks like. **Can
that knowledge stand in for labelled data?**

On six MedMNIST 2D benchmarks spanning six modalities, a vision-language model (VLM) scores each
image against a cited bank of diagnostic visual features (the *concept bank*, built outside the
workflow and committed as an input). We ask what those scores are worth, measured in the currency
a practitioner cares about: labelled images.

## 2. The hypotheses

Three, each with a decision rule fixed before the numbers exist. Everything that serves none of
them is an extension in §10, not part of `all`.

Primary metric throughout: **test AUC** from the `medmnist` evaluator (macro one-vs-rest). Every
arm predicts on the **same seeded 500-image test sample** per dataset, so every comparison is
paired, and each has a 95% interval from a paired bootstrap over the test images. Across datasets
we use a one-sided sign test rather than pooling incommensurable AUCs. With six datasets that
test is coarse: 6 of 6 wins is p = 0.016 and 5 of 6 is p = 0.11, so a hypothesis is *supported*
only when it wins on every dataset, and the per-dataset paired differences with their intervals
are what a reader should look at.

**H1 — Substitution.** *Textbook features are worth a measurable number of labelled images.*

- Compare, at equal labels and with an identical classifier, concept-score features (arm C)
  against ImageNet pixel-embedding features (arm P) over n = 50…2000 labelled images.
- Headline number: **n_B**, the smallest grid n at which the seed-mean AUC of the pixel probe
  reaches AUC(B), the *zero-label* textbook arm: "this many labels is what the textbook was
  worth." Coded `<=50` when arm P is already above at the first grid point and `>2000` when it
  never crosses, with a 95% interval from the same bootstrap (resample test images, recompute
  AUC(B) and every AUC(P, n), take the crossing).
- Supported if median n_B ≥ 100 **and** AUC(C) > AUC(P) at n = 50 on all six datasets.

**H2 — The bank, not just the model.** *Directing the VLM at cited visual features beats asking
it for the diagnosis, and the bank's structure carries the difference.*

- AUC(B) > AUC(A), the zero-shot class distribution, on all six datasets. A and B are separate
  calls on separate prompts: the concept prompt never names a class and the zero-shot prompt never
  mentions a concept, so the comparison cannot be circular.
- Both B and C lose AUC under the permutation controls on every dataset: fingerprints permuted
  across classes (B), concept columns permuted across images (C). Free re-analyses of the archive.

**H3 — Scale.** *The prior gets better with a bigger model.* Four models, two per family (qwen at
9B and 27B, gemma at 12B and 31B), all scoring arm B on the same test samples. Read within
family, since size and training data are confounded across families: supported if the larger
model has the higher AUC(B) on at least 5 of 6 datasets in **both** families. That threshold is
descriptive (p = 0.11), which six datasets cannot improve on; the ladder figure and a Friedman
test over the four models are reported alongside. Both size steps also change quantisation
(qwen 27B is fp8, gemma 31B is served as NVFP4) and the qwen step changes generation (3.5 → 3.8),
so "larger" moves together with "newer" and "quantised"; stated as a limit, not analysed away.

What no arm here can separate: every source dataset is public and labelled, so "the model carries
textbook knowledge" and "the model has seen this benchmark" are not distinguishable with these data.
Not claimed: that the concept scores are clinically valid, that the simulated review substitutes
for a clinician, or that any arm is state of the art.

## 3. Arms

Four, all predicting on the shared test sample. A and B use no labels; C and P are the same
regularised logistic regression on different features.

| arm | labels | features | what it establishes |
|---|---|---|---|
| A zero-shot | 0 | — | the VLM's class distribution from the image and the class names, in its own prompt: the undirected baseline for H2 (primary model) |
| B textbook-only | 0 | concept scores | nearest class fingerprint from the bank; the zero-label prior, and the line that defines n_B |
| C concept regression | n | concept scores | what the prior is worth once a few labels exist (H1) |
| P pixel probe | n | ImageNet ResNet-18 penultimate features | the label-matched pixel baseline (H1): transfer learning without the textbook |

A VLM is an enormous pretrained model, so the fair pixel baseline is also pretrained: frozen
ImageNet features under the same classifier, the same regularisation search and the same nested
subsets as arm C, so features are the only difference.

**Estimators**, fixed here because "nearest fingerprint" is not self-explanatory:

- *Concept vector*: each concept's ordered scale maps to equally spaced values on [0, 1]; a missing
  answer becomes the labelled-pool median plus a missing-indicator column (dropped where constant).
  Equal spacing weights concepts by scale length: an adjacent miss costs 1.0 on a two-level scale
  and 0.25 on a five-level one. A consequence of the mapping, stated so nobody reads a
  per-concept contribution as an importance.
- *Arm B*: a class's fingerprint maps the same way with `any` masked; the class score is the
  negative mean absolute difference over the concepts the fingerprint commits to and the image
  answered. AUC reads that score directly, no softmax.
- *Arms C and P*: multinomial logistic regression, L2 strength by 5-fold CV **inside the n
  labelled images**, features standardised on those n. No validation set: n labels means n labels.
  Subsets are class-stratified nested prefixes of the labelled pool with a floor of one image per
  class; the fold count is `min(5, smallest class count)`; a class absent from a subset scores 0.
- *Evaluation*: `medmnist.evaluator.getAUC`, the package's own convention, on the 500-image sample.
  An image with any missing concept answer counts as incomplete; a dataset-model cell more than 5%
  incomplete is flagged in the report and excluded from the headline.
- *The test sample is drawn at random, not stratified, and a rare class is thin.* Measured on the
  drawn samples (2026-09-11): dermamnist holds 6 dermatofibromas and 5 vascular lesions of its 500,
  organamnist 21 femur-left, pathmnist 24 debris. Since the AUC is the unweighted mean of
  one-vs-rest columns, a column built on five positives counts as much as one built on 337, and the
  paired bootstrap will show that as a wide interval on every arm at once. Equal-as-possible
  stratification was considered and rejected: it would raise those columns only to 23, 46 and 56 -
  the splits themselves hold little more - while making each column's negatives a uniform mixture
  rather than the dataset's own, and the study's three hypotheses are paired differences on the
  same images, where the thin columns are common mode. Matching the split's proportions, the other
  reading of "stratify", reproduces what the seed already drew and buys nothing. So the sample
  stays as §4 fixes it, the absolute per-dataset AUCs are read with this in mind, and the report
  states it as a limit.

## 4. Scope, and the call budget

| dimension | value | why not more |
|---|---|---|
| datasets | pathmnist, dermamnist, octmnist, pneumoniamnist, bloodmnist, organamnist | one per modality: histology, dermoscopy, OCT, chest X-ray, blood smear, CT; the full version has twelve |
| resolution | 224 | what the VLM sees and what the ImageNet encoder wants |
| VLMs | 4, two per family | H3 needs the pairs; more buy nothing |
| test sample | 500 per dataset, seed 0 | shared by every arm; every dataset has ≥ 624 test images |
| labelled pool | 2000 per dataset, seed 0, from the official train split | the largest curve point; every dataset has ≥ 4708 train images |
| curve | n = 50, 100, 200, 500, 1000, 2000 × 3 seeds | CPU-cheap; the resolution of n_B is the grid |

Only the primary model scores the labelled pool; arm B is training-free, so the ladder models need
the 500 test images and nothing else.

**Completed prior work: the data are already on disk, and the workflow does not fetch it.** Like
the concept bank, the download was done before the workflow, verified once, and is not redone —
there is no `fetch` rule or stage. The six 224-pixel release files sit in
`/project/dane2/wficai/textbook_priors/raw/` (project storage, not purged), confirmed present on
2026-09-11 at the exact size and against the MD5 that `medmnist` 3.0.2 records in
`medmnist.INFO[<dataset>]["MD5_224"]`:

| file | MD5 | size |
|---|---|---|
| `pathmnist_224.npz` | `2c51a510bcdc9cf8ddb2af93af1eadec` | 11.8 GB |
| `dermamnist_224.npz` | `8974907d8e169bef5f5b96bc506ae45d` | 1.0 GB |
| `octmnist_224.npz` | `abc493b6d529d5de7569faaef2773ba3` | 3.7 GB |
| `pneumoniamnist_224.npz` | `d6a3c71de1b945ea11211b03746c1fe1` | 0.2 GB |
| `bloodmnist_224.npz` | `b718ff6835fcbdb22ba9eacccd7b2601` | 1.4 GB |
| `organamnist_224.npz` | `50747347e05c87dd3aaf92c49f9f3170` | 1.7 GB |

The same directory also holds files the full version fetched (the 28-pixel files and other 224
datasets); the talk version ignores them. `data/raw` is a symlink into that directory (§11,
gitignored); the sample stage reads the six files straight from it. Provenance — the pinned
Zenodo record (10519652) and the MD5 check above — is recorded here for the reader, not
re-verified by any rule.

| model | family | role | concept calls | zero-shot calls |
|---|---|---|---|---|
| `qwen3.8-27b-fp8` | qwen | primary | 15,000 (test + pool) | 3,000 (test) |
| `qwen3.5-9b` | qwen | ladder | 3,000 (test) | — |
| `gemma-4-12b` | gemma | ladder | 3,000 (test) | — |
| `gemma-4-31b` | gemma | ladder | 3,000 (test) | — |

**27,000 calls** in 270 chunk jobs of 100 images. Two measurements, because they disagree and the
second is the one to plan with. On 2026-09-09, with thinking off and no image attached, 0.1 to
0.4 s per call on every model. On 2026-09-11 the `probe` rule measured the call this workflow
actually makes - a 224-pixel PNG and a rendered prompt of about 1,300 tokens, on the primary model:
median 3.6 s, range 1.2 to 5.2 s. A chunk of 100 images is therefore about six minutes, not twenty
seconds, and a chunk rule's `runtime` has to say so. The conclusion survives the correction: each
model's jobs run to its own cap, so the primary's 18,000 calls at 48 concurrent are about
25 minutes and the ladder models are shorter still - the fan-out is tens of minutes of wall clock,
not hours.

## 5. Principles

Each names the failure it prevents; `TALK.md` argues them.

1. **The workflow is the documentation.** Numbered stages with prose; a dry run prints the plan.
2. **Every number has a rule.** No ad hoc scripts; the report is built from generated tables.
3. **Inputs are pinned.** The concept bank and the raw MedMNIST releases are fixed inputs
   completed before the workflow runs, with recorded checksums; no rule re-fetches or
   re-verifies them.
4. **Dependencies are explicit.** Modules are inputs via `code()`, config values are `params`.
5. **Every result carries a manifest.** Parameters, seeds, commit, versions, host, wall time.
6. **Randomness is owned per cell.** No module-level RNG.
7. **The LLM boundary is explicit.** Every response archived raw with the served model name and
   the prompt hash; everything downstream is a deterministic function of the archive; the archive
   is write-protected, so re-querying is a deliberate act.
8. **Resources are measured.** `benchmark:` and `log:` on every submitted rule.
9. **Structure and history live apart.** README for structure, CHANGELOG for dated findings.
10. **Direction is recorded, timestamped.** SESSION_LOG.md logs, to the minute, what the user
    asked for and why it changed the work; it is talk material, not a substitute for CHANGELOG.md,
    which stays the owner's record of understanding rather than of agent activity.

## 6. Stages

```
0  SMOKE      bank schema and anchors, label maps against the pinned release, both prompts,
              the arm-B estimator on a fixture, metric conventions, client retry      seconds
1  SAMPLE     per dataset: the seeded 500-image test sample and 2000-image labelled pool,
              streamed out of the compressed npz without loading it (the raw releases are
              prior work, §4 — no fetch rule)                                           6 CPU
2  SCORE      per dataset: render the concept and zero-shot prompts from the bank; then,
              per model x split x prompt x chunk of 100: concept levels, or the zero-shot
              distribution; every raw response archived and protected  6 local + 270 throttled
3  FEATURES   per dataset: ImageNet ResNet-18 penultimate features of the sampled images  6 CPU
4  CLASSIFY   per dataset: arms A, B, C, P at every n and seed, and the permutation controls 6 CPU
5  EVALUATE   AUC per arm; the paired bootstrap; n_B; then the sign tests and the ladder
              across datasets                                                             6 + 1
6  REPORT     three figures, tables, number macros, the technical report PDF              local
```

Targets: `all` (the report), `smoke`, `sample`, `score`, `features`, `classify`, `evaluate`,
`report`. Three figures: the learning curve with arm B's line (H1), n_B per dataset (H1 detail),
the model ladder (H3). H2 is a table of paired differences and permutation drops.

## 7. The scoring stage

The one stage type not seen in earlier projects, and the one that tests principle 7.

- **Unit**: one dataset, one model, one split, one prompt, one chunk of 100 images. Output
  `results/score/<dataset>__<model>__<split>__<prompt>__chunk<k>.json`: per image the parsed
  answer and every raw reply. The manifest adds the served model name, the prompt hash, the
  bank-file hash, temperature and reasoning setting.
- **Two prompts, both pure functions of the bank and the label map, both tested in `smoke`**: the
  concept prompt asks for a level per concept, renders every level's cited anchor text, and never
  names a class; the zero-shot prompt asks for a distribution over the class names and never
  mentions a concept.
- **Rendering is its own rule, not inline in the score loop.** `render_prompts`, one per dataset
  (6 local jobs, no LLM calls, no throttling), turns the bank and the label map into both prompt
  strings and writes `results/prompts/<dataset>.json` (the rendered concept prompt with its
  anchors, the rendered zero-shot prompt, the bank-file hash). Every `score_*` rule takes that file
  as an input instead of re-deriving the prompt, so the string sent to the model, the one hashed
  into the manifest, and the one the report or the demo shows are the same artifact.
- **Per call**: the 224-pixel PNG; JSON requested and validated against the scales; one retry with
  a doubled token budget on a malformed answer, then recorded as missing, never guessed.
- **Thinking off.** With reasoning left on, the primary model spends its whole token budget in
  `reasoning_content` and returns nothing; `chat_template_kwargs.enable_thinking: false` is in
  config and recorded in every manifest. One served model files its answer under
  `reasoning_content` even so; the client reads `content` and falls back to it.
- **Throttling**: one rule per model, each holding one unit of an `llm_<model>` resource capped in
  the profile below the service's published concurrency.
- **Client**: the `openai` package against `https://llm.rcd.clemson.edu/v1`; backoff on 429 and
  5xx. The key is read from an owner-only file whose path is in config; it appears nowhere else.

## 8. Config, environments, resources

```yaml
datasets: [pathmnist, dermamnist, octmnist, pneumoniamnist, bloodmnist, organamnist]
size: 224
sample: {test_n: 500, pool_n: 2000, seed: 0}
curve:  {n: [50, 100, 200, 500, 1000, 2000], seeds: [0, 1, 2]}
vlm:
  primary: qwen3.8-27b-fp8
  models:                       # concurrency published, cap ours, splits = what it scores
    qwen3.5-9b:      {family: qwen,  params_b: 9,  concurrency: 128, cap: 96, splits: [test]}
    gemma-4-12b:     {family: gemma, params_b: 12, concurrency: 32,  cap: 24, splits: [test]}
    qwen3.8-27b-fp8: {family: qwen,  params_b: 27, concurrency: 64,  cap: 48, splits: [test, pool]}
    gemma-4-31b:     {family: gemma, params_b: 31, concurrency: 16,  cap: 12, splits: [test]}
  chunk: 100
  prompt: {anchors: true}
  temperature: 0.0
  reasoning: none               # transmitted as chat_template_kwargs.enable_thinking: false
  retries: 1
  base_url: https://llm.rcd.clemson.edu/v1
  key_file: ~/.config/rcd_llm/key
features: {arch: resnet18, weights: imagenet1k_v1}
classify: {l2_grid: [0.01, 0.1, 1, 10, 100], cv_folds: 5, missing_max_frac: 0.05, permute: {seeds: [0, 1, 2]}}
evaluate: {bootstrap: 10000, ci: 0.95, h3_min_wins: 5}
resources: {...}                # first guesses, then set from benchmarks/ with the reasoning
```

Two environments: `envs/priors.yml` (numpy, scipy, scikit-learn, matplotlib, pyyaml, pytest,
openai, pillow; `medmnist` for its evaluator, installed without its torch requirement) and
`envs/priors_torch.yml` (plus torch and torchvision, for the features stage only).

## 9. Order of work

1. Skeleton and the bank schema test over the six files.
2. Point the sample stage straight at the six on-disk releases (§4 — prior work, no fetch rule);
   extract the samples; check counts and the class balance of each sample.
3. The ten-image probe on the primary model (rule `probe`, outside `all`): a compute node reaches
   the service, the archive and manifest are right, a malformed response is handled.
4. The primary fan-out under its cap, then the ladder models; features; classify; evaluate.
5. The three figures, the tables, the report; a CHANGELOG entry per milestone.
6. Demo rehearsal (`TALK.md`).

Commit after each coherent change. Dry-run and lint before every submission; ask before more than
50 CPU jobs.

## 10. Decisions, and what was cut for the talk

Kept from the full plan, so they stop being open questions: one resolution, 224; the pretrained
linear probe as the fair pixel baseline; the learning curve as C against P with arm B as the
horizontal line; separate prompts for A and B; the rendered anchors; the ladder scores the test
split only.

Cut for the talk, each with what it supported, and all still built on the full branch:

- *Arm E, the ResNet-18 trained from scratch on the official splits*, its 72 GPU jobs, the
  28-pixel data and the reconciliation against the published MedMNIST table. It was the
  fully supervised ceiling and the check that the pipeline reproduces a known number; it tests no
  hypothesis here, and it was half the Snakefile and the only GPU.
- *Six of the twelve datasets*, among them chestmnist, the one multi-label task, which carried its
  own code path through every stage (one-vs-rest fitting, multi-label AUC, exclusion from A and B).
- *ACC*: reported alongside in the full plan, deciding nothing.
- *The blocked ANOVA, the log₁₀-parameter contrast and the Nemenyi post-hoc for H3*: with six
  datasets the within-family sign tests and the ladder figure say what can be said.
- *A separate environment for the LLM client*: `openai` is not a heavy toolchain.

Extensions, outside `all`, each one rule and a config block when wanted: `bare_levels` (the
concept prompt without anchors, a re-score into a second archive), `generic_prompt` (a
non-diagnostic question set), `primary_upgrade` (the pool on `gemma-4-31b`).

## 11. Layout

```
Snakefile                 one file, seven labelled stages
config/config.yaml        every grid and knob; per-rule resources
config/medmnist.yaml      the pinned release: file names, MD5s, sizes, split sizes, label maps
profiles/palmetto/        SLURM executor; job, core and per-model llm_* caps
profiles/local/           dry runs, smoke, touch
envs/                     priors.yml  priors_torch.yml
priors/                   data sample prompts llm score features classify evaluate report stages manifest
data/concepts/            the concept-bank files and their README, committed
data/raw, data/cache      symlinks into storage_root on the project filesystem; gitignored
results/                  one JSON per unit of work; results/score/ is the response archive
benchmarks/  logs/        per job
report/                   report.tex, references.bib; tables/ and figs/ generated
README.md  CHANGELOG.md  SESSION_LOG.md  CLAUDE.md  CONCEPT_BANK.md  WORKFLOW.md  TALK.md
```
