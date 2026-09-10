# Textbook priors over visual features

A reproducible medical-imaging study, built as one Snakemake workflow on Palmetto2 with an AI
coding agent, and the running example for *Reproducible scientific computing with AI coding
agents* (Clemson HPC Day). The talk narrative lives in `TALK.md`; this file is the scientific and
engineering plan. Workflow conventions are the `research-workflow` skill
(`~/.claude/skills/research-workflow/SKILL.md`); the concept-bank procedure is `CONCEPT_BANK.md`.

---

## 1. The question

A multimodal language model carries textbook knowledge about what pathology looks like. **Can
that knowledge stand in for labelled data?**

On the twelve MedMNIST 2D benchmarks, a vision-language model (VLM) scores each image against a
cited bank of diagnostic visual features (the *concept bank*, built outside the workflow and
committed as an input). We ask what those scores are worth, measured in the currency a
practitioner cares about: labelled images.

## 2. The hypotheses

Three, each with a decision rule fixed before the numbers exist. Everything in this plan that
does not serve one of them is an extension in §10, not part of `all`.

Primary metric throughout: **test AUC** from the `medmnist` evaluator (macro one-vs-rest for
multi-class and ordinal; mean over the 14 findings for chestmnist). ACC is reported alongside but
decides nothing. Every arm predicts on the **same seeded 500-image test sample** per dataset, so
every comparison is paired. Across datasets we use a one-sided sign test rather than pooling
incommensurable AUCs. One caveat on those counts: organa/c/smnist are the same LiTS volumes in
three planes, so twelve datasets are at most ten independent units and eleven are nine. The
thresholds below are stated over the nominal counts; the report also gives the win count and the
paired differences, so a reader can recount with the organ triple as a single vote (9 of 10,
p = 0.011) rather than take the verdict alone. The three hypotheses are pre-registered and each is
conjunctive, so no multiplicity correction is applied across them.

**H1 — Substitution.** *Textbook features are worth a measurable number of labelled images.*

- Compare, at equal labels and with an identical classifier, concept-score features (arm C)
  against ImageNet pixel-embedding features (arm P) over n = 50…2000 labelled images.
- Headline number: **n_B**, the smallest grid n at which the seed-mean AUC of the pixel curve
  reaches AUC(B), the *zero-label* textbook arm — "this many labels is what the textbook was
  worth." Coded `<=50` when arm P is already above at the first grid point and `>n_max` when it
  never crosses. Reported per dataset with a 95% interval from the same paired bootstrap that
  serves everything else — resample test images, recompute AUC(B) and every AUC(P, n), take the
  crossing; the predictions are fixed, so it costs nothing extra. The median is the summary, but
  the per-dataset intervals are what the claim rests on, because a shift of 0.02 in the
  horizontal line can move a crossing by a grid step.
- Supported if median n_B over the arm-B datasets is ≥ 100 **and** AUC(C) > AUC(P) at n = 50 in
  ≥ 10 of 12 datasets (one-sided sign test, p = 0.019).

**H2 — The bank, not just the model.** *Directing the VLM at cited visual features beats asking
it for the diagnosis, and the bank's structure carries the difference.*

- AUC(B) > AUC(A) (zero-shot class distribution) in ≥ 9 of the 11 arm-B datasets (p = 0.033).
  Arm A runs on those same 11: chestmnist is excluded from A as well as B, because a distribution
  over class names is not defined for a multi-label task in which most images carry no finding,
  and H2 reads nothing from it.
  **The zero-shot prompt renders clinical class names, not raw label-map keys.** retinamnist's
  label map is the digit strings `"0"`…`"4"`; asking a model to choose among "0, 1, 2, 3, 4" is
  not a diagnosis question, so arm B would beat arm A there by construction and H2 would collect a
  free vote. Config carries a `zeroshot_names` map for any dataset whose keys are not clinical
  terms. The prompt also states the modality, so arm A is not handicapped by not knowing it is
  looking at a fundus photograph — it is the *directing at cited features* that H2 tests, not the
  model's ability to guess the imaging domain.
  A and B come from **separate calls on separate prompts**: one prompt asks for the class, the
  other for the concept levels and never names a class. In one prompt the concept answers could be
  rationalisations of a guess the model had already made, which would make the comparison
  circular.
- Both B and C lose accuracy under the permutation controls (§5, principle 9; a free re-analysis
  of the archive: fingerprints permuted across classes, concept columns permuted across images).
  These test that the **class-to-fingerprint mapping** carries the signal, not that *cited*
  features beat arbitrary ones — permuting columns destroys any informative feature, cited or not.
  The stronger claim is what `generic_prompt` tests, and it is an extension (§10).

**H3 — Scale.** *The prior gets better with a bigger model, within a model family.*

- Two within-family size contrasts on arm B. `gemma-4-12b` → `gemma-4-31b` is clean: same family,
  same generation, size is the only difference. `qwen3.5-9b` → `qwen3.8-27b-fp8` is **larger and
  newer**, and fp8-quantised, so it confounds size with generation in the same way this hypothesis
  refuses to confound it across families; it is read as corroboration, not as a second clean test,
  and H3 rests on the gemma pair. Comparing across families would confound size with training data
  outright, so the ladder is read pairwise, never as one curve. The ladder scores concepts only;
  arm A is a baseline for H2 and runs on the primary model alone.
- Supported if the larger model's AUC(B) exceeds the smaller's in ≥ 9 of 11 datasets in the gemma
  pair, with the qwen pair reported alongside and read as corroboration.

One thing no arm here can separate: every source dataset — HAM10000, ChestX-ray14, the Kermany
OCT and paediatric CXR sets, BUSI — is public and labelled, and MedMNIST itself is widely
redistributed. "The model carries textbook knowledge" and "the model has seen this benchmark" are
not distinguishable with these data, and nothing below should be read as ruling the second out.

What we deliberately do **not** claim: that the concept scores are clinically valid, that the
simulated review substitutes for a clinician, or that any arm is state of the art.

## 3. Arms

Five, all predicting on the shared test sample; arm E additionally on the full official test
split, for the reconciliation only. Arms A and B use no labels; C and P are the same
regularised logistic regression on different feature blocks; E is the fully supervised reference.

| arm | labels | features | what it establishes |
|---|---|---|---|
| A zero-shot | 0 | — | the VLM's class distribution from the image and the class names, asked in its own prompt: the undirected baseline for H2, primary model only |
| B textbook-only | 0 | concept scores | nearest class fingerprint from the bank; the zero-label prior, and the horizontal line that defines n_B |
| C concept regression | n | concept scores | what the prior is worth once a few labels exist (H1) |
| P pixel probe | n | ImageNet ResNet-18 penultimate features | the label-matched pixel baseline (H1) |
| E pixel network | full split | pixels | ResNet-18 from scratch, official splits: the fully supervised ceiling and the reconciliation against the published MedMNIST table. Evaluated **twice** — on the shared sample for the paired comparisons, and on the full official test split for the reconciliation, since the published numbers are computed on the full split |

**Why the pixel baseline is a pretrained probe.** A VLM is an enormous pretrained model; comparing
it against a ResNet-18 trained from scratch on 50 images would make H1 true by construction. Arm
P is the strong, fair, cheap baseline: transfer learning without the textbook. It also makes the
comparison exactly paired — same n, same nested subsets, same classifier, same CV — so the only
thing that differs between C and P is the features. Arm E keeps the from-scratch reference where
it belongs: as the ceiling and as the number we reconcile against the literature.

**Estimator definitions** (fixed here, because "nearest fingerprint" and "logistic regression on
scores" are not self-explanatory):

- *Concept vector*: each concept's ordered scale is mapped to equally spaced values on [0, 1];
  a missing answer becomes the labelled-pool median plus a missing-indicator column.
- *Arm B*: a class's fingerprint maps the same way, with `any` levels masked out; the class score
  is the negative mean absolute difference over the concepts the fingerprint commits to and the
  image answered. **AUC reads that score directly** — no softmax, which would otherwise make one
  class's ranking depend on every other class's score and on an unstated temperature. ACC takes
  the argmax. Masking `any` cuts both ways for a thin fingerprint: it is scored on fewer concepts,
  so a near miss on any one of them costs it proportionally more, but its score is also noisier
  and takes the argmax more often when there is no signal. That second effect touches ACC, which
  decides nothing, and the fingerprint-permutation control is what would expose it.
- *Equal spacing weights concepts by scale length*: an adjacent miss costs 1.0 on a two-level
  scale and 0.25 on a five-level one, so short scales carry more weight in the mean. That is a
  consequence of the mapping, not a preference, and it is stated so nobody reads a per-concept
  contribution as a per-concept importance.
  Arm B needs single-label fingerprints, so it covers **11 datasets** — chestmnist (multi-label)
  is in A, C, P and E only.
- *Arms C and P*: multinomial logistic regression (one-vs-rest per finding for chestmnist), L2
  strength chosen by 5-fold CV **inside the n labelled images**, features standardised on those
  same n. No separate validation set is used, so "n labels" means n labels.
- *Small-n mechanics*: subsets are drawn with a floor of one image per class; the CV fold count
  is `min(5, smallest class count)` in that subset; a class absent from a subset gets probability
  zero. The missing-indicator column is dropped where it is constant, which under the 5%
  completeness gate is most subsets.
- *Evaluation*: AUC and ACC come from `medmnist.evaluator.getAUC`/`getACC` rather than
  `Evaluator`, which asserts on the full test length and so cannot read a 500-image sample. Arm P
  replicates greyscale to three channels and applies ImageNet normalisation. "More than 5%
  incomplete" counts images with any missing concept answer.
- *Nested subsets*: for each dataset and subsample seed, class-stratified nested subsets of the
  scored labelled pool at each n, shared by C and P. Seeds collapse at the largest n a dataset
  supports, where the subset is the whole pool.

## 4. Scope, and the call budget

The grid is set by the hypotheses and nothing else.

| dimension | value | why not more |
|---|---|---|
| datasets | all 12 MedMNIST 2D | breadth across modalities is the generality claim, and the sign tests need the 12 |
| resolution | **224** for every arm | it is what the VLM sees and what the ImageNet encoder wants; a resolution sweep tests no hypothesis |
| resolution, arm E only | 28 and 224 | the two sizes with published ResNet-18 numbers, for reconciliation |
| VLMs | 4, as two within-family pairs | H3 needs the pairs; more models buy nothing |
| test sample | `min(500, official test)` per dataset, seed 0 | shared by every arm; per-dataset CIs are wide, which is why the inference is the sign test across datasets |
| labelled pool | `min(2000, official train)` per dataset, seed 0, drawn from the **official train split only** | the largest curve point; the pool is what SCORE must cover beyond the test sample |
| curve | n = 50, 100, 200, 500, 1000, 2000 × 3 seeds | CPU-cheap, so the resolution of n_B is limited only by the grid |

**Only the primary model scores the labelled pool.** Arm B is training-free, so the three ladder
models need the 500 test images and nothing else. That single observation takes the call volume
from 120,000 to under 50,000 without dropping a dataset or a model.

| model | family | role | concept calls | zero-shot calls |
|---|---|---|---|---|
| `qwen3.8-27b-fp8` | qwen | primary | 30,000 (test + pool) | 6,000 (test) |
| `qwen3.5-9b` | qwen | ladder | 6,000 (test) | — |
| `gemma-4-12b` | gemma | ladder | 6,000 (test) | — |
| `gemma-4-31b` | gemma | ladder | 6,000 (test) | — |

49,406 calls in total. **Two datasets are smaller than the nominal sample**: breastmnist has 156
test and 546 train images, retinamnist 400 and 1,080. Both are capped by the `min()` rule above,
so breastmnist's curve stops at n = 500 and retinamnist's at n = 1000, and curve points above a
dataset's pool are dropped rather than repeated. Every count below is the capped
figure. The zero-shot prompt is short and its output is a class distribution, so
the 6,000 extra calls that keep A independent of B are the cheapest part of the budget.

`qwen3.8-27b-fp8` is primary for throughput per unit capability (cap 48 against `gemma-4-31b`'s
12); at ten seconds a call under its cap the primary fan-out is a couple of hours of wall clock,
the largest model would have been most of a day. If the ladder shows `gemma-4-31b` clearly ahead
on arm B, scoring its labelled pool is a documented extension (+21,626 calls), not
a silent change. All wall-clock numbers here are estimates until the first chunk is benchmarked.

If the allocation bites, the documented contingency is a six-dataset core spanning the modalities
— pathmnist, dermamnist, octmnist, pneumoniamnist, bloodmnist, organamnist — at 27,000 calls, with
the sign-test thresholds restated for six.

## 5. Principles

Each names the failure it prevents. `TALK.md` argues them; here they are the contract.

1. **The workflow is the documentation.** Numbered stages, each opening with prose; a dry run
   prints the plan.
2. **Every number has a rule.** No ad hoc scripts, no notebook cells, no hand-copied values. The
   workflow ends in a technical report built from generated tables and macros; the paper is
   written from it, and interpretation stays with the authors.
3. **Inputs are pinned, not vendored.** Large data is a fetch rule from a pinned release with
   recorded checksums.
4. **Dependencies are explicit.** Modules are inputs via `code()`, config values are `params`,
   environments are per rule; an edit reruns exactly what could have changed.
5. **Every result carries a manifest.** Parameters, seeds, commit and dirty flag, versions, host,
   wall time.
6. **Randomness is owned per cell.** No module-level RNG; inserting a cell never moves another
   cell's numbers.
7. **Computation and reporting are separate.** Report rules read only results.
8. **Resources are measured.** `benchmark:` and `log:` on every submitted rule; requests set from
   the measurements with the reasoning in a comment.
9. **The LLM boundary is explicit.** Every response is archived raw with the served model name and
   prompt hash; everything downstream is a deterministic function of the archive; re-querying is a
   deliberate act. The permutation controls of H2 are re-analyses of the archive and cost nothing.
10. **Reconcile, never silently replace.** Arm E is compared against the published table and the
    differences are written down.
11. **Structure and history live apart.** README for structure, CHANGELOG for dated findings.

## 6. Stages

```
0  SMOKE      bank schema, anchors and label maps, both prompt templates, arm-B
              estimator on a fixture, metric conventions, client retry                seconds
1  FETCH      MedMNIST from the pinned release, checksummed; data/raw on scratch       1 job
2  CACHE      per dataset x {224, 28}: uint8 arrays and labels for the full official
              splits; the seeded test sample and labelled pool at 224                 24 CPU
3  SCORE      per dataset x model x split x prompt x chunk of 100: concept levels, or the
              zero-shot distribution; raw response archived                           540, throttled
4  FEATURES   per dataset: ImageNet ResNet-18 penultimate features for the sampled
              images at 224                                                           12 short GPU
5  TRAIN      per dataset x {224, 28} x seed: ResNet-18 from scratch on the official
              split, best epoch by validation AUC                                     72 GPU
6  CLASSIFY   per dataset, grouped: arms A, B, C, P at every n and seed, plus the
              permutation controls; predictions on the shared test sample             12 CPU
7  EVALUATE   every arm through the medmnist evaluator; paired bootstrap per dataset;
              n_B; the sign tests                                                     12 CPU
8  REPORT     reconciliation against the published table; three figures, tables,
              number macros, the technical report                                     local
```

Targets: `all` (the report), `smoke`, `cache`, `score`, `features`, `train`, `classify`,
`evaluate`, `report`. Nine stages, one rule family each; FETCH has no target of its own, being
pulled in as an input of CACHE; A and B enter through CLASSIFY as
parameter-free predictors so EVALUATE is uniform over arms.

Three figures, two for H1 and one for H3; H2 and the reconciliation are tables: the learning
curve with arm B's line
and arm E's ceiling (H1); the two within-family size contrasts (H3); n_B per dataset ordered by
modality — where the textbook pays (H1 detail). H2 is a table of paired differences and the
permutation drops.

## 7. The scoring stage

The one stage type not seen in earlier projects, and the one that tests principle 9.

- **Unit**: one dataset, one model, one split, one prompt, one chunk. Output
  `results/score/<dataset>__<model>__<split>__<prompt>__chunk<k>.json`: per image the parsed
  answer — concept levels on the bank's scales, or the zero-shot class distribution — and the raw
  response. The manifest adds the served model name from the response, the prompt-template hash,
  the concept-bank file hash, temperature, reasoning level, timestamp.
- **Two prompts, both pure functions of the bank and the label map, both tested in `smoke`**: the
  concept prompt asks for a level per concept and never names a class; the zero-shot prompt asks
  for a distribution over the class names and never mentions a concept. Keeping them in separate
  calls is what makes H2 a comparison rather than a tautology.
- **The concept prompt renders each level's anchor.** Every concept in the bank carries an
  `anchors` block giving each scale level a described visual referent with its own source keys, and
  the renderer emits them alongside the question when `vlm.prompt.anchors` is set, which is the
  default. Without them the model is sent a bare token like `mild` and invents the threshold it
  means, which is not the threshold the source intended — and since the levels are mapped to
  equally spaced values in §3, an invented threshold is an invented number. The model still answers
  with the bare token, so the parser, the archive format and the estimators are unchanged.
- **Per call**: the image at 224 pixels; structured JSON requested and validated against the
  scales; one retry on a malformed answer, then recorded as missing, never guessed. A
  dataset-model cell whose images are more than 5% incomplete is flagged in the report and
  excluded from the headline.
- **Throttling**: `resources: llm_<model>=1` with caps below each model's published concurrency in
  the profile, so the workflow is never the noisy neighbour while GPU jobs run beside it.
- **Client**: the `openai` package against `https://llm.rcd.clemson.edu/v1`; backoff on 429 and
  5xx; raw response archived before parsing. The key is read from an owner-only file whose path is
  in config; it is never in config, the repository, a command line or a log.
- **Environment**: its own file, so the client never invalidates the numpy or torch tiers.
- **No free-text description is requested.** The arm that used it was cut (§10), and prose we do
  not analyse would cost tokens and latency on all 49,406 calls.

## 8. Config, environments, resources

```yaml
datasets: [pathmnist, chestmnist, dermamnist, octmnist, pneumoniamnist, retinamnist,
           breastmnist, bloodmnist, tissuemnist, organamnist, organcmnist, organsmnist]
size: 224                       # every arm sees this
recon_sizes: [28, 224]          # TRAIN only; the sizes with published ResNet-18 numbers
sample: {test_n: 500, pool_n: 2000, seed: 0}   # both capped at the official split size;
                                              # breastmnist and retinamnist are the two that cap
curve:  {n: [50, 100, 200, 500, 1000, 2000], seeds: [0, 1, 2]}
vlm:
  primary: qwen3.8-27b-fp8
  models:                       # concurrency published, cap ours, splits = what it scores
    qwen3.5-9b:      {family: qwen,  params_b: 9,  concurrency: 128, cap: 96, splits: [test]}
    gemma-4-12b:     {family: gemma, params_b: 12, concurrency: 32,  cap: 24, splits: [test]}
    qwen3.8-27b-fp8: {family: qwen,  params_b: 27, concurrency: 64,  cap: 48, splits: [test, pool]}
    gemma-4-31b:     {family: gemma, params_b: 31, concurrency: 16,  cap: 12, splits: [test]}
  chunk: 100
  prompts: [concept, zeroshot]  # separate calls; zeroshot only for vlm.primary
  zeroshot_names:               # clinical names where the label map is not clinical (§2)
    retinamnist: {"0": no diabetic retinopathy, "1": mild non-proliferative,
                  "2": moderate non-proliferative, "3": severe non-proliferative,
                  "4": proliferative}
  prompt: {anchors: true}       # render each scale level's anchor text; false = bare tokens
  temperature: 0.0
  reasoning: none               # fixed, not swept; the reasoning sweep was cut (§10)
  retries: 1
  base_url: https://llm.rcd.clemson.edu/v1
  key_file: ~/.config/rcd_llm/key
features: {arch: resnet18, weights: imagenet1k_v1, layer: penultimate}
classify:
  l2_grid: [0.01, 0.1, 1, 10, 100]
  cv_folds: 5                   # reduced to min(5, smallest class count) in a subset
  missing_max_frac: 0.05        # the §7 completeness gate
  bootstrap: 10000
  permute: {seeds: [0, 1, 2]}   # the H2 controls; seeded per cell, like every other draw
train: {arch: resnet18, pretrained: false, epochs: 100, select_on: val_auc, seeds: [0, 1, 2],
        gpu: {enabled: true, type: a100, cpus: 8, mem_mb: 32000, runtime: 240}}
published: config/published.yaml
resources: {...}                # first guesses, then set from benchmarks/ with the reasoning
```

Environments: `envs/priors.yml` (numpy, scipy, pandas, scikit-learn, matplotlib, pyyaml, pytest,
medmnist), `envs/priors_torch.yml` (plus the CUDA torch wheel), `envs/priors_llm.yml` (openai,
pyyaml, numpy, pillow). Loose floors; exact versions in every manifest.

Resources to measure before trusting: 28-pixel training leaves an A100 nearly idle, so pack cells
per GPU job once a utilisation sample says so, and record the number where the packing is
configured; scoring jobs are network-bound and need one core; the 224 cache scales with the array
size, and tissuemnist and pathmnist are the large ones. Cache the full training split at both
sizes — a cap on the cached array would change what arm E trains on and quietly break the
reconciliation.

## 9. Order of work

1. Skeleton from the skill's templates; the bank schema test over the twelve files.
2. Fetch and cache at 224 and 28; verify counts and checksums.
3. Arm E on one dataset at 28; benchmark; set resources; then the full 72 jobs, and **reconcile
   against the published table before anything else is trusted**.
4. One scoring chunk truncated to ten images with a `--config chunk=10` override, one dataset,
   the primary model: a compute node reaches the
   service, the archive and manifest are right, a malformed response is handled. Then the primary
   fan-out under its cap, then the ladder.
5. FEATURES and CLASSIFY; arms A, B, C, P; EVALUATE with the paired bootstrap; H2 and its
   permutation controls, which need no new calls.
6. The learning curve and n_B; the three figures.
7. Tables, macros, the technical report; a CHANGELOG entry per milestone; the README stage table
   with job counts.
8. Demo rehearsal (`TALK.md`).

Commit after each coherent change with a descriptive imperative sentence. Dry-run and lint before
every submission; ask before any GPU jobs or more than 50 CPU jobs.

## 10. Decisions, and what was cut

Resolved, so they stop being open questions:

- **One resolution, 224, for every arm**; 28 survives only inside arm E for the reconciliation.
- **The curve's pixel baseline is a pretrained linear probe**, not a from-scratch CNN, and it
  shares the classifier and the subsets with arm C. This removes the GPU learning-curve grid
  entirely: the curve is CPU logistic regressions over features computed once.
- **The learning curve compares C against P**, with arm B as the horizontal line that defines the
  headline number. The earlier plan compared E against F, which measures whether a prior helps a
  supervised model — a different question from whether it substitutes for labels.
- **chestmnist stays in A, C, P and E and leaves arm B**, because fingerprint matching is not
  defined for 14 co-occurring findings. The sign tests are stated over 11 or 12 datasets
  accordingly.
- **The ladder scores the test split only**, which is what pays for keeping all twelve datasets.
- **H3 is read within family**, because size and training data are confounded across families.
- **The concept prompt renders each scale level's anchor** (§7), so an ordinal answer means what
  the cited source meant rather than what the model guessed.

Cut from the plan, each with the claim it would have supported:

- *The free-text description field on every call*: it fed arm D only, and asking for prose we do
  not analyse would have cost tokens and latency on every one of 49,406 calls.
- *Arm D, description embedding* (and the whole EMBED stage, and the embedding model): a control
  for structured versus free-text elicitation. The permutation controls test the bank's structure
  for free, so D is an extension, not a hypothesis.
- *Arm F, prior fused into a supervised network*: tests complementarity, not substitution. Its
  design was itself an open question (late fusion, soft label, or both).
- *The 64- and 128-pixel sweep and the GPU-minutes figure*: no hypothesis, half the training grid.
- *`reasoning_sweep`*: a cost curve for the service, not a result about priors.
- *`prompt_ablation` and `vlm_utilisation`*: the first is subsumed by the permutation controls
  except for a generic-question prompt (an extension at ~1,500 calls); the second is two lines in
  the report from the scoring logs.

Extensions, outside `all`, each one rule and a config block: `fusion` (F), `description_embedding`
(D), `generic_prompt` (a non-diagnostic question set on three datasets), `primary_upgrade` (the
labelled pool on `gemma-4-31b` if the ladder demands it), `bare_levels` (the concept prompt with
`vlm.prompt.anchors: false`, to measure what the anchors buy). `bare_levels` is a re-score, not a
re-report: anchors change the concept scores themselves, so it writes a second archive that arms
B and C read, which principle 9 makes a deliberate act. Two or three datasets on the primary model
is enough to size the effect, and the pre-anchor bank is committed history, so the contrast costs
no re-authoring.

Still open, and needing a person:

- Total volume of 49,406 image calls against the allocation, confirmed with the service owners.
- Acceptable-use confirmation for de-identified public medical images; one sentence on a slide.

## 11. Layout

```
Snakefile                 one file, nine labelled stages
config/config.yaml        every grid and knob; per-rule resources
config/published.yaml     the MedMNIST v2 benchmark table
profiles/palmetto/        SLURM executor; job, core and per-model llm_* caps
profiles/local/           dry runs, smoke, touch
envs/                     priors.yml  priors_torch.yml  priors_llm.yml
priors/                   data cache features train prompts llm score classify evaluate report
                          stages manifest
data/concepts/            the twelve concept-bank files and their README, committed
data/raw -> scratch       MedMNIST files; data/cache the arrays; gitignored
results/                  one JSON per unit of work; results/score/ is the response archive
benchmarks/  logs/        per job
report/                   report.tex, references.bib; tables/ and figs/ generated
README.md  CHANGELOG.md  CLAUDE.md  CONCEPT_BANK.md  WORKFLOW.md  TALK.md
```
