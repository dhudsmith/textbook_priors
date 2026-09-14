# Textbook priors over visual features

A small, reproducible medical-imaging study, built as one Snakemake workflow on Palmetto2 with an
AI coding agent, and the running example for *Reproducible scientific computing with AI coding
agents* (Clemson HPC Day). This file is the scientific and engineering plan; `TALK.md` carries the
talk narrative; `CONCEPT_BANK.md` the procedure that built the bank. Workflow conventions are the
`research-workflow` skill (`~/.claude/skills/research-workflow/SKILL.md`).

Twelve datasets - every MedMNIST v2 2D benchmark - four vision-language models, two label-free
arms and two label-matched arms, and a report a person can read in one sitting. The study was built
and run on six datasets first, one per modality, for the talk; on 2026-09-13 it was extended to all
twelve, with the six results already in hand (§2 says what that does to the rules). An earlier full
plan with a from-scratch CNN ceiling and a blocked ANOVA over the model ladder lives on branch
`claude/textbook-priors-workflow-2kdgap`; §10 lists what was cut from it and what came back.

---

## 1. The question

A multimodal language model carries textbook knowledge about what pathology looks like. **Can
that knowledge stand in for labelled data?**

On the twelve MedMNIST 2D benchmarks - histology, dermoscopy, OCT, chest X-ray, fundus, breast
ultrasound, blood smear, kidney microscopy, and abdominal CT in three planes - a vision-language
model (VLM) scores each image against a cited bank of diagnostic visual features (the *concept
bank*, built outside the workflow and committed as an input). We ask what those scores are worth,
measured in the currency a practitioner cares about: labelled images.

## 2. The hypotheses

Seven, each with a decision rule fixed before the numbers exist. Everything that serves none of
them is an extension in §10, not part of `all`. H1 to H3 were registered before any call was
bought; H4 was added on 2026-09-12 and H5, H6 and H7 on 2026-09-13, each after the earlier ones had
been decided and each before a single call of its own was bought — which is the distinction arm D
could not make for itself, and the reason arm D is gone (§10).

Primary metric throughout: **test AUC** from the `medmnist` evaluator (macro one-vs-rest over
classes; the mean over the fourteen findings for chestmnist). Every arm predicts on the **same
seeded test sample** per dataset - 500 images, or the whole official test split where that is
smaller (§4) - so every comparison is paired, and each has a 95% interval from a paired bootstrap
over the test images. Across datasets we use a one-sided sign test rather than pooling
incommensurable AUCs, and every rule is held to **one level, p < 0.05**: an arm must win on the
smallest number of datasets whose sign test reaches it. That is 6 of 6 when the study had six
datasets, and now 10 of 12 (p = 0.019) for a rule over all twelve or 9 of 11 (p = 0.033) for one
over the eleven that have an arm B. Five of six was p = 0.11 and never counted; neither does 9 of
12 or 8 of 11. The per-dataset paired differences with their intervals are what a reader should
look at.

**Which datasets each rule covers.** chestmnist is multi-label - fourteen findings that co-occur -
and a nearest fingerprint or a distribution over class names is not defined over such a label
space (§3). It runs in the two labelled arms only, so it counts for H1's C-against-P comparison and
for nothing else; H2, H3 and H4 are read over the other eleven, and n_B's median over those eleven.

**Two honest limits on the counts.** organa/c/smnist are the same LiTS volumes in three planes, so
twelve datasets are at most ten independent units and eleven are nine; the report gives the win
count and the paired differences so a reader can recount with the organ triple as one vote (9 of
10 is p = 0.011). And the rules were restated at this level on 2026-09-13, when six of the twelve
verdicts were already known and six were not: the level reproduces the six-dataset rule exactly
(6 of 6), so nothing already decided moves, but the twelve-dataset thresholds are pre-registered
only with respect to the six new datasets.

**H1 — Substitution.** *Textbook features are worth a measurable number of labelled images.*

- Compare, at equal labels and with an identical classifier, concept-score features (arm C)
  against ImageNet pixel-embedding features (arm P) over n = 50…2000 labelled images.
- Headline number: **n_B**, the smallest grid n at which the seed-mean AUC of the pixel probe
  reaches AUC(B), the *zero-label* textbook arm: "this many labels is what the textbook was
  worth." Coded `<=50` when arm P is already above at the first grid point and `>2000` when it
  never crosses, with a 95% interval from the same bootstrap (resample test images, recompute
  AUC(B) and every AUC(P, n), take the crossing).
- Supported if median n_B ≥ 100 over the eleven arm-B datasets **and** AUC(C) > AUC(P) at n = 50
  on at least 10 of the 12 datasets (p = 0.019).

**H2 — The bank, not just the model.** *Directing the VLM at cited visual features beats asking
it for the diagnosis, and the bank's structure carries the difference.*

- AUC(B) > AUC(A), the zero-shot class distribution, on at least 9 of the 11 arm-B datasets
  (p = 0.033). A and B are separate calls on separate prompts: the concept prompt never names a
  class and the zero-shot prompt never mentions a concept, so the comparison cannot be circular.
  retinamnist's class names are the digits 0 to 4, which are not a diagnosis question, so its
  zero-shot listing glosses each digit with the ICDR grade it stands for; the JSON keys stay the
  release names.
- Both B and C lose AUC under the permutation controls on every dataset they run on: fingerprints
  permuted across classes (B, eleven datasets), concept columns permuted across images (C, all
  twelve). Free re-analyses of the archive.

**H3 — Scale.** *The prior gets better with a bigger model.* Four models, two per family (qwen at
9B and 27B, gemma at 12B and 31B), all scoring arm B on the same test samples of the eleven arm-B
datasets. Read within family, since size and training data are confounded across families:
supported if the larger model has the higher AUC(B) on at least 9 of 11 datasets in **both**
families (p = 0.033). With six datasets the rule was 5 of 6 and descriptive (p = 0.11), which six
datasets could not improve on; eleven can, and the rule is now held to the same level as the
others. The ladder figure and a Friedman test over the four models are reported alongside. Both
size steps also change quantisation
(qwen 27B is fp8, gemma 31B is served as NVFP4) and the qwen step changes generation (3.5 → 3.8),
so "larger" moves together with "newer" and "quantised"; stated as a limit, not analysed away.

**H4 — Reading.** *A better reader gets more class information out of the same images.*

H1 to H3 ask what the textbook is worth. H4 asks the question underneath them: **to what extent
does a vision-language model actually see the visual features that medical image classification
turns on?** The archive already holds the material — every test image scored concept by concept by
four models — and H4 reads it along a chain of *readers*, a reader being a model plus a reasoning
effort. Two steps, each changing exactly one thing:

- **H4a, effort.** `qwen3.8-27b-fp8` at effort `none` (already archived) against the same model at
  `medium`. The model is held fixed, so the step is thinking and nothing else.
- **H4b, capability.** That thinking primary against `gpt-5.6-terra` at `medium`. The effort is
  held fixed, so the step is the model and nothing else. It must be read this way round because the
  frontier model cannot be asked for no reasoning at all (`docs/rcd_llm_service.md`).

- Metric: the **cross-validated probe** (§3) — arm C's classifier fitted *inside* the scored images
  by stratified k-fold, folds fixed by seed and identical across readers, every image scored by a
  fit that never saw it. It measures what the concept answers carry. Arm B would measure it through
  the nearest-fingerprint rule H2 showed to be lossy; arm C would need a labelled pool for every
  reader, which this study does not buy. It is not a point on the learning curve and no n_B reads
  it.
- Every reader is read on the **same 200-image prefix** of the seeded test sample, so the four
  existing models join by being subset rather than re-bought, and every difference is paired. 200
  is measured, not round: below it organamnist's rarest class empties and its AUC column stops
  existing (6 of 11 classes reach five images at 100, 10 at 150, all 11 at 200). dermamnist stays
  thin either way and carries the caveat §3 already gives it. breastmnist has 156 test images in
  all, so its readers read the whole sample.
- Supported if each step wins on at least 9 of the 11 arm-B datasets (p = 0.033), the level H1 and
  H2 are held to. Fewer is reported and called suggestive, never supported.

A null here is a result and not a failure: if thinking does not move the concept answers, the
model's reading of the features is not attention-limited, which is a sharper statement than a rise
would be.

**H5 — Complement.** *The textbook adds something the pixels do not already carry.*

H1 asks whether concept scores can stand in for pixel features at equal labels, and answers no. That
is not the same question as whether they carry anything pixels lack: two feature blocks can be
individually unequal and still complementary. H5 asks the second question directly, with the same
classifier and the same labelled subsets, by giving the regression **both** feature blocks at once.

- **Arm C+P**: the concept vectors of arm C concatenated with arm P's frozen ImageNet features,
  standardised together, one L2 strength for the whole matrix, the same nested subsets and the same
  seeds. Only the features differ from arm P, so the difference is what the textbook adds.
- Primary comparison: AUC(C+P) > AUC(P) at **n = 50**, the smallest labelled subset, where a prior
  has the most room to help and where H1's own comparison is read. Supported if it wins on at least
  10 of the 12 datasets (p = 0.019). Every other grid point is reported and decides nothing.
- **Registered on 2026-09-13, after H1 to H4 were decided and before any C+P number existed.** That
  order is the thing arm D could not claim (§10), and the distinction is not that H5 is uninformed
  by earlier results - it is prompted by H1's failure - but that no result in this study answers it
  and none of its numbers were seen before the rule was written. It costs no calls: the concept
  answers and the pixel features are both already on disk, so the whole test is a re-analysis. The
  git history carries the rule in a commit that precedes the one carrying its numbers.
- **One limit, stated rather than tuned away.** Twelve or so concept columns join 512 pixel columns
  under a single L2 penalty, so a real but small contribution can be regularised away; a per-block
  penalty would test a different, unregistered model. A null here therefore means "no detectable
  gain under the same classifier every other arm uses", not "no information".

**H6 — Effort in the frontier model.** *H4b's null is a statement about the model, not about how
hard it was asked to think.*

H4b compared two readers at matched `medium` and found no clear difference. H4a had already shown
that effort is not monotone: on this task thinking helps a model that reads the concepts badly and
costs one that reads them well. Both readings leave one thing untested — whether `medium` is simply
the wrong operating point for the frontier model, in which case H4b measured a handicap rather than
a capability.

- Same model, same prompt, same images, one setting changed: `gpt-5.6-terra` at `low` against the
  archived `gpt-5.6-terra` at `medium`, read by the same cross-validated probe on the same
  200-image prefix, so the four thinking-off readers and both H4 readers join for nothing.
- `low` is the floor the gateway allows: it rejects `minimal`, which is why H4b could not be run
  against a no-reasoning frontier reader, and why H6 lowers the effort rather than removing it.
- One-sided in the direction the overthinking reading predicts, supported if `low` beats `medium`
  on at least 9 of the 11 arm-B datasets. The count the other way is reported beside it and read as
  reasoning helping; neither is *supported* below the level every other rule uses.
- **The archive already rules out the crude failure and motivates the sharp one.** All 2,156 of the
  `medium` reader's calls finished cleanly, with no truncation and no missing answer, so this is not
  a budget problem. But its reasoning is 41% to 85% of its completion tokens, and on dermamnist —
  where H4b loses hardest, and where a 12B open model at no reasoning beats it 0.741 to 0.554 — it
  commits `pigment_network` to one level on 93% of images against 51% and 53% for the two qwen
  readers. That is what a confidently wrong prior looks like, and only a second effort can say
  whether reasoning produced it.
- **The frontier reader is sampled, not deterministic** (below), so some of any difference H6 finds
  is sampling noise the paired bootstrap cannot see. Two readers of the same model at two efforts
  differ in their effort *and* in their draw. Stated, not corrected.

**H7 — Capability inside the frontier family.** *A more capable closed model reads cited features
better.*

Three models of one family at one effort, `gpt-5.6-luna`, `gpt-5.6-terra` and `gpt-5.6-sol` at
`low`, on the same prefix and the same probe. H3 asks this of open weights, where size is public;
here nothing public orders the models by size, so the ladder is **ordered by price** — output
tokens at 1.20, 12.00 and 20.00 dollars per million — which is the vendor's own ranking and a proxy
for capability, not a parameter count. Supported if the top of the ladder beats the bottom on at
least 9 of the 11 arm-B datasets; the middle rung is reported and decides nothing.

Registered 2026-09-13, both of them, after H4 was decided and before a call of either was bought.
Unlike H5 they are not free: 66 chunks and about 6,500 calls, costed at $53.59 at list and $26.79
at `flex` in `docs/rcd_llm_service.md` before the owner approved the spend.

**Two limits on H4b, both stated rather than analysed away.** The frontier model is closed and of
unknown size, so the step is *capability* and not parameters; it cannot join H3's ladder and does
not. And it **refuses `temperature: 0`** — only its served default is allowed — so it is the one
reader in this study whose answers are sampled rather than deterministic, where every other reader
runs at temperature 0. Its concept answers would differ if re-bought. That widens H4b's step with
sampling noise the paired bootstrap cannot see, because the bootstrap resamples images over answers
that are fixed only in the archive. Read H4b as a difference between two readers as they were
actually asked, not between two models at matched settings.

What no arm here can separate: every source dataset is public and labelled, so "the model carries
textbook knowledge" and "the model has seen this benchmark" are not distinguishable with these data.
Not claimed: that the concept scores are clinically valid, that the simulated review substitutes
for a clinician, or that any arm is state of the art.

## 3. Arms

Five, all pre-registered and all predicting on the shared test sample. A and B use no labels; C, P
and C+P are the same regularised logistic regression on different features. A fifth arm, D, existed
between 2026-09-12 and 2026-09-12 and was removed; §10 records what it measured and why it went.
chestmnist has arms C and P only (below).

| arm | labels | features | what it establishes |
|---|---|---|---|
| A zero-shot | 0 | — | the VLM's class distribution from the image and the class names, in its own prompt: the undirected baseline for H2 (primary model) |
| B textbook-only | 0 | concept scores | nearest class fingerprint from the bank; the zero-label prior, and the line that defines n_B |
| C concept regression | n | concept scores | what the prior is worth once a few labels exist (H1) |
| P pixel probe | n | ImageNet ResNet-18 penultimate features | the label-matched pixel baseline (H1): transfer learning without the textbook |
| C+P complement | n | both blocks concatenated | whether the textbook adds anything the pixels lack (H5); differs from P in its features alone |

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
- *Arm C+P*: arm C's feature matrix and arm P's, concatenated and standardised together inside the
  n labelled images, then the identical regression, grid and cross-validation. No weighting, no
  per-block penalty and no feature selection: the point is that it differs from arm P in the
  presence of the concept columns and in nothing else.
- *chestmnist*: fourteen findings that co-occur, so there is no class to match a fingerprint
  against and "exactly one of these categories" is false of most films. Arms A and B are not
  defined for it and are not run; the ladder models and H4's readers, which exist for arm B and
  the probe, do not score it. Arms C and P fit the same regression **one finding at a time**
  (one-vs-rest), with the subsets stratified on any-finding against no-finding, the L2 strength
  chosen by out-of-fold AUC rather than accuracy (a finding present in two percent of films makes
  "always negative" the most accurate classifier at every strength), and a finding absent from a
  subset scored as a constant. Its AUC is the package's convention for the task: the mean over
  findings of each finding's one-vs-rest AUC.
- *The cross-validated probe* (H4): the same regularised logistic regression as arm C, on the same
  concept vectors, fitted inside the scored images by stratified k-fold rather than on the labelled
  pool. Each fold's held-out images are scored by a fit that never saw them, so every image gets
  exactly one out-of-fold score and the result enters a paired bootstrap like any other arm.
  Missing answers are imputed on **that reader's own** medians over its own images, not the pool's:
  the pool's medians belong to one model at one effort, and using them everywhere would pull every
  reader toward the baseline's habits on precisely the answers H4 compares. It estimates
  information content and is not a learning-curve point — the same images are the training and the
  evaluation material, and no labels were spent to make it.
- *Evaluation*: `medmnist.evaluator.getAUC`, the package's own convention, on the test sample.
  An image with any missing concept answer counts as incomplete; a dataset-model cell more than 5%
  incomplete is flagged in the report and excluded from the headline.
- *The test sample is drawn at random, not stratified, and a rare class is thin.* Measured on the
  drawn samples (2026-09-11): dermamnist holds 6 dermatofibromas and 5 vascular lesions of its 500,
  organamnist 21 femur-left, pathmnist 24 debris. Since the AUC is the unweighted mean of
  one-vs-rest columns, a column built on five positives counts as much as one built on 337, and the
  paired bootstrap will show that as a wide interval on every arm at once. Equal-as-possible
  stratification was considered and rejected: it would raise those columns only to 23, 46 and 56 -
  the splits themselves hold little more - while making each column's negatives a uniform mixture
  rather than the dataset's own, and the study's hypotheses are paired differences on the
  same images, where the thin columns are common mode. Matching the split's proportions, the other
  reading of "stratify", reproduces what the seed already drew and buys nothing. So the sample
  stays as §4 fixes it, the absolute per-dataset AUCs are read with this in mind, and the report
  states it as a limit.

## 4. Scope, and the call budget

| dimension | value | why not more |
|---|---|---|
| datasets | all twelve MedMNIST v2 2D benchmarks; the talk's six were pathmnist, dermamnist, octmnist, pneumoniamnist, bloodmnist, organamnist | there are no more 2D benchmarks in the release |
| resolution | 224 | what the VLM sees and what the ImageNet encoder wants |
| VLMs | 4, two per family | H3 needs the pairs; more buy nothing |
| test sample | 500 per dataset, seed 0, capped at the official test split | shared by every arm; breastmnist has 156 test images and retinamnist 400, and take them all |
| labelled pool | 2000 per dataset, seed 0, from the official train split, capped at it | the largest curve point; breastmnist's 546 and retinamnist's 1080 stop the curve at 500 and 1000 |
| curve | n = 50, 100, 200, 500, 1000, 2000 × 3 seeds, the points a pool can fill | CPU-cheap; the resolution of n_B is the grid |

Only the primary model scores the labelled pool; arm B is training-free, so the ladder models need
the test sample and nothing else. Only the primary model scores chestmnist at all (§3).

**Prior work, and four files fetched by a rule.** Like the concept bank, eight of the twelve
224-pixel release files were downloaded before the workflow, verified once, and are not redone:
they sit in `/project/dane2/wficai/textbook_priors/raw/` (project storage, not purged), the talk's
six confirmed present on 2026-09-11 at the exact size and against the MD5 that `medmnist` 3.0.2
records in `medmnist.INFO[<dataset>]["MD5_224"]`, and breastmnist and retinamnist fetched whole by
the earlier full plan. The other four - chestmnist, organcmnist, organsmnist and tissuemnist - were
left half-fetched by that plan and are completed by `rule fetch` (stage 1) from the same pinned
Zenodo record, in resumable parallel byte ranges because Zenodo serves about 105 KB/s per
connection, and checked against the same MD5s, which `config/medmnist.yaml` carries for all
twelve. A file already on disk is never fetched again.

| file | MD5 | size |
|---|---|---|
| `pathmnist_224.npz` | `2c51a510bcdc9cf8ddb2af93af1eadec` | 11.8 GB |
| `dermamnist_224.npz` | `8974907d8e169bef5f5b96bc506ae45d` | 1.0 GB |
| `octmnist_224.npz` | `abc493b6d529d5de7569faaef2773ba3` | 3.7 GB |
| `pneumoniamnist_224.npz` | `d6a3c71de1b945ea11211b03746c1fe1` | 0.2 GB |
| `bloodmnist_224.npz` | `b718ff6835fcbdb22ba9eacccd7b2601` | 1.4 GB |
| `organamnist_224.npz` | `50747347e05c87dd3aaf92c49f9f3170` | 1.7 GB |

The same directory also holds the 28-pixel files the earlier full plan fetched, which nothing
here reads. `data/raw` is a symlink into that directory (§11, gitignored); the sample stage reads
the twelve files straight from it. Provenance — the pinned Zenodo record (10519652) and the MD5
check — is recorded here and in `config/medmnist.yaml`; only a fetch re-verifies it.

| model | family | role | concept calls | zero-shot calls |
|---|---|---|---|---|
| `qwen3.8-27b-fp8` | qwen | primary | 27,182 (test + pool, twelve datasets) | 5,056 (test, eleven) |
| `qwen3.5-9b` | qwen | ladder | 5,056 (test, eleven) | — |
| `gemma-4-12b` | gemma | ladder | 5,056 (test, eleven) | — |
| `gemma-4-31b` | gemma | ladder | 5,056 (test, eleven) | — |

**47,406 calls** in 477 chunk jobs of 100 images, plus **4,312 for H4's two readers** in 44
chunks — the 200-image prefix per dataset (156 for breastmnist), concept prompt only, no pool and
no zero-shot, because H4 is read through the concept answers alone — plus **6,468 for H6's and
H7's three gateway readers** in 66 chunks, on the same prefix. **58,186 in total**, of which
the talk's six datasets were 29,400 in 294 chunks and the six added on 2026-09-13 are 22,318 in
227; the smoke tier pins both numbers. A further 3,000 were bought for arm D; their archive was
deleted on 2026-09-13 (§10).

H4's thinking reader is the expensive half in wall clock rather than in calls: at effort `medium`
an answer costs about 986 completion tokens against 112 with thinking off, and this endpoint
delivers roughly 63 tokens per second in aggregate however many streams it is given, so its 1,200
calls are about five hours. The gateway reader is somebody else's capacity and answered in 3 to 9
seconds a call, at about 1,684 prompt and 313 completion tokens of which 89% of the prompt comes
back cached (`docs/rcd_llm_service.md`). Run one chunk before the other twenty-three, which is
standing practice here since the generated-rule bug. Two measurements, because they disagree and the
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
3. **Inputs are pinned.** The concept bank, the raw MedMNIST releases and the published literature
   benchmarks (§10) are fixed inputs completed before the workflow runs, with recorded checksums;
   no rule re-fetches, re-derives or re-verifies them.
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
1  SAMPLE     a release file missing from storage is fetched from the pinned record first
              (4 network jobs, once); then per dataset: the seeded test sample and labelled
              pool, capped at the official split, streamed out of the compressed npz
              without loading it                                                  4 + 12 CPU
2  SCORE      per dataset: render the concept and zero-shot prompts from the bank;
              then, per model x split x prompt x chunk of 100: concept levels, or a class
              distribution; every raw response archived and protected 12 local + 521 throttled
3  FEATURES   per dataset: ImageNet ResNet-18 penultimate features of the sampled images 12 CPU
4  CLASSIFY   per dataset: arms A, B, C, P, C+P at every n and seed, the permutation controls,
              and every reader's cross-validated probe on the shared prefix (H4); the labelled
              arms alone for chestmnist                                                  12 CPU
5  EVALUATE   AUC per arm; the paired bootstrap; n_B; a second bootstrap over the prefix for
              H4's readers; then the sign tests, the ladder, the chain and H5            12 + 1
6  REPORT     six figures, tables, number macros, an appendix of every rendered prompt,
              the technical report PDF                                                    local
```

Targets: `all` (the report), `smoke`, `sample`, `score`, `features`, `classify`, `evaluate`,
`report`. The report carries two generated appendices — every dataset's rendered prompts
verbatim, from the same `results/prompts/` files the archive was hashed against, and a montage of
the sampled test images of every class, drawn from the same cached arrays every arm was scored on
— and a table of each arm's design-matrix widths so arm C+P's fusion is a number rather than a
description.
Six figures: the learning curve with arm B's line (H1), n_B per dataset (H1 detail),
the model ladder (H3), the reader chain and thinking's effect against the baseline (H4), and what
the concept block adds on top of the pixels (H5). H2 is a table of paired differences and
permutation drops.

## 7. The scoring stage

The one stage type not seen in earlier projects, and the one that tests principle 7.

- **Unit**: one dataset, one model, one split, one prompt, one chunk of 100 images. Output
  `results/score/<dataset>__<model>__<split>__<prompt>__chunk<k>.json`: per image the parsed
  answer and every raw reply. The manifest adds the served model name, the prompt hash, the
  bank-file hash, temperature and reasoning setting.
- **Two prompts, each a pure function of the bank and the label map, each tested in `smoke`**:
  the concept prompt asks for a level per concept, renders every level's cited anchor text, and
  never names a class; the zero-shot prompt asks for a distribution over the class names and never
  mentions a concept. They are held apart because H2 turns on it.
- **Rendering is its own rule, not inline in the score loop.** `render_prompts`, one per dataset
  (6 local jobs, no LLM calls, no throttling), turns the bank and the label map into both prompt
  strings and writes `results/prompts/<dataset>.json` (the rendered concept prompt with its
  anchors, the rendered zero-shot prompt, the bank-file hash). Every `score_*` rule takes that file
  as an input instead of re-deriving the prompt, so the string sent to the model, the one hashed
  into the manifest, and the one the report or the demo shows are the same artifact.
  `render_prompts_txt` (target `prompts_txt`, opt-in, outside `all`, no LLM calls) formats that
  same file into `results/prompts_txt/<dataset>.txt`, one block per arm, for a person to read
  rather than parse; it decides no hypothesis and no rule below it reads its output.
- **Per call**: the 224-pixel PNG; JSON requested and validated against the scales; one retry with
  a doubled token budget on a malformed answer, then recorded as missing, never guessed.
- **Thinking off**, and for a reason that turned out to be ours rather than the service's.
  `chat_template_kwargs.enable_thinking: false` is in config and recorded in every manifest. The
  original justification here - that with reasoning on the primary model spends its whole token
  budget in `reasoning_content` and returns nothing - was measured against this workflow's own
  `max_tokens: 512`. At 2048 the primary model, gemma-4-12b and gemma-4-31b all answer with
  thinking on, at ten to sixteen times the wall clock; qwen3.5-9b does not finish within 8192
  (measured 2026-09-12, `docs/rcd_llm_service.md`). The archive stays thinking-off, because that is
  what it was bought as and re-scoring is deliberate (section 5, principle 7); a reasoning sweep is
  an extension in section 10, not a correction to this line. One served model files its answer
  under `reasoning` even with thinking off; the client reads `content` and falls back.
- **Throttling**: one rule per model, each holding one unit of an `llm_<model>` resource capped in
  the profile below the service's published concurrency.
- **Client**: the `openai` package against `https://llm.rcd.clemson.edu/v1`; backoff on 429 and
  5xx. The key is read from an owner-only file whose path is in config; it appears nowhere else.

## 8. Config, environments, resources

```yaml
datasets: [pathmnist, dermamnist, octmnist, pneumoniamnist, bloodmnist, organamnist,
           breastmnist, retinamnist, tissuemnist, organcmnist, organsmnist, chestmnist]
size: 224
fetch: {segment_mb: 256, max_segments: 24}   # byte ranges per release file, for rule fetch
sample: {test_n: 500, pool_n: 2000, seed: 0}  # both capped at the official split
curve:  {n: [50, 100, 200, 500, 1000, 2000], seeds: [0, 1, 2]}
vlm:
  primary: qwen3.8-27b-fp8
  models:                       # concurrency published, cap ours, splits = what it scores
    qwen3.5-9b:      {family: qwen,  params_b: 9,  concurrency: 128, cap: 96, splits: [test]}
    gemma-4-12b:     {family: gemma, params_b: 12, concurrency: 32,  cap: 24, splits: [test]}
    qwen3.8-27b-fp8: {family: qwen,  params_b: 27, concurrency: 64,  cap: 24, splits: [test, pool]}
    gemma-4-31b:     {family: gemma, params_b: 31, concurrency: 16,  cap: 12, splits: [test]}
  readers:                      # H4: model + effort, concept prompt on a 200-image prefix of test
    qwen3.8-27b-fp8-medium: {model: qwen3.8-27b-fp8, effort: medium, api: local,   cap: 4,  subsample: 200}
    gpt-5.6-terra-medium:   {model: gpt-5.6-terra,   effort: medium, api: gateway, cap: 12, subsample: 200}
  chunk: 100
  prompt: {anchors: true, class_gloss: {retinamnist: {"0": no apparent diabetic retinopathy, ...}}}
  temperature: 0.0
  reasoning: none               # transmitted as chat_template_kwargs.enable_thinking: false
  retries: 1
  base_url: https://llm.rcd.clemson.edu/v1
  key_file: ~/.config/rcd_llm/key
features: {arch: resnet18, weights: imagenet1k_v1}
classify: {l2_grid: [0.01, 0.1, 1, 10, 100], cv_folds: 5, missing_max_frac: 0.05,
           permute: {seeds: [0, 1, 2]}, probe: {folds: 5, seed: 0}}
evaluate: {bootstrap: 10000, ci: 0.95, seed: 0, alpha: 0.05}   # one level for every rule
h4: {baseline: qwen3.8-27b-fp8, thinking: qwen3.8-27b-fp8-medium, frontier: gpt-5.6-terra-medium,
     subsample: 200}
h5: {n: 50}                                   # the grid point H5 is decided at
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
5. The figures, the tables, the report; a CHANGELOG entry per milestone.
6. Demo rehearsal (`TALK.md`).

Commit after each coherent change. Dry-run and lint before every submission; ask before more than
50 CPU jobs.

## 10. Decisions, and what was cut for the talk

Kept from the full plan, so they stop being open questions: one resolution, 224; the pretrained
linear probe as the fair pixel baseline; the learning curve as C against P with arm B as the
horizontal line; separate prompts for A and B; the rendered anchors; the ladder scores the test
split only.

Cut from the earlier full plan, each with what it supported, and all still built on that branch:

- *Arm E, the ResNet-18 trained from scratch on the official splits*, its 72 GPU jobs, the
  28-pixel data and the reconciliation against the published MedMNIST table. It was the
  fully supervised ceiling and the check that the pipeline reproduces a known number; it tests no
  hypothesis here, and it was half the Snakefile and the only GPU. The published table now enters
  as the literature extension below instead.
- *ACC*: reported alongside in the full plan, deciding nothing.
- *The blocked ANOVA, the log₁₀-parameter contrast and the Nemenyi post-hoc for H3*: the
  within-family sign tests, the Friedman test and the ladder figure say what can be said.
- *A separate environment for the LLM client*: `openai` is not a heavy toolchain.

Cut for the talk and **restored on 2026-09-13**: the other six datasets, chestmnist among them. The
earlier plan had also confined chestmnist to arms C and P; here that is one branch in the classify
and evaluate stages (§3) rather than a code path through every stage, and the report's figures and
tables skip the arms a dataset does not have. The talk's six datasets were decided first and the
twelve-dataset rules restated after (§2).

Extensions, outside `all`, each one rule and a config block when wanted: `bare_levels` (the
concept prompt without anchors, a re-score into a second archive), `generic_prompt` (a
non-diagnostic question set), `primary_upgrade` (the pool on `gemma-4-31b`), and `reasoning_sweep`
(the concept prompt re-scored at each `reasoning_effort` the model's own metadata advertises - four
on the primary model - into a second archive; it was cut as impossible and is merely expensive,
section 7 and `docs/rcd_llm_service.md`).

**Arm D, added 2026-09-12 and removed the same day.** It handed the model the whole bank — every
concept with its anchors, every class's fingerprint — and then asked arm A's zero-shot question, so
that the textbook was integrated inside the model rather than by a distance in concept space. It
cost 3,000 calls and it measured something real: the nearest-fingerprint readout is lossy (D beat B
on 4 of 6, recovering nearly all of pneumoniamnist's deficit), and the bank is not information the
model lacked (D lost to A on 4 of 6). Both readings are in `CHANGELOG.md`, which keeps them.

It was removed because it was designed after seeing the numbers and so could decide nothing, and an
arm that decides nothing has to be labelled post-hoc in every table, figure, macro and paragraph it
touches. That cost every reader of the report a second explanation of why a number was there and
what it was not allowed to mean, on every page it appeared. The study is clearer with four
pre-registered arms and no asterisk. The 30 archived chunks stayed on disk unread until 2026-09-13,
when the owner had them deleted in the cleaning audit; what they measured stays in `CHANGELOG.md`.

The lesson it leaves is the one any replacement has to obey: **a decision rule before the calls.**
An arm worth adding is worth pre-registering, and anything that cannot be is a separate study.

**H5 was added on 2026-09-13, and is a hypothesis rather than an extension**, because its rule was
written and committed before its numbers existed (§2). It costs no calls. What separates it from
arm D is not innocence of the earlier results - it exists because H1 failed - but that the
comparison it makes had never been computed when the rule was fixed.

**Literature reconciliation, another extension inside `all`** (added 2026-09-12, no rerun). The
user asked to pull published results for these six MedMNIST tasks and add them as benchmarks in
the report — verified, not rerun. `data/literature/benchmarks.yaml` pins the AUC and ACC that
Yang et al. 2023 (the same paper the concept bank already cites as its anchor) report for five
fully supervised methods on these six tasks at 224 pixels, transcribed from the published table and
cross-checked against its own across-dataset average as a second read. It decides no hypothesis —
every value in it is trained on a dataset's whole official training split, not this study's
$n \leq 2000$ pool, so it is a ceiling for the task, not a same-conditions arm — and it costs
nothing to compute: the `tables` rule reads it beside results/ already on disk and writes one more
table, `literature`, read in its own report section. It sits inside `rule all` because it is cheap
and costs the reader nothing: unlike arm D it needs no warning label, since a published benchmark
trained on the full split is plainly a ceiling and not a competitor.

## 11. Layout

```
Snakefile                 one file, seven labelled stages (the fetch rule sits in stage 1)
config/config.yaml        every grid and knob; per-rule resources
config/medmnist.yaml      the pinned release: file names, MD5s, sizes, split sizes, label maps
profiles/palmetto/        SLURM executor; job, core and per-model llm_* caps
profiles/local/           dry runs, smoke, touch
envs/                     priors.yml  priors_torch.yml  priors.post-deploy.sh
priors/                   data sample prompts llm score features classify evaluate report stages manifest
scripts/link_storage.sh   one-time setup: the two symlinks below
scripts/fetch_medmnist.sh one release file in resumable byte ranges, MD5-checked (rule fetch)
docs/rcd_llm_service.md   the LLM service as this project found it: models, efforts, throughput
data/concepts/            the concept-bank files and their README, committed
data/literature/          the pinned published-benchmark table and its README, committed
data/raw, data/cache      symlinks into storage_root on the project filesystem; gitignored
results/                  one JSON per unit of work; results/score/ is the response archive;
                          results/prompts_txt/ a human-readable txt render, opt-in, no manifest
benchmarks/  logs/        per job
report/                   report.tex, references.bib; tables/ and figs/ generated
README.md  CHANGELOG.md  SESSION_LOG.md  CLAUDE.md  CONCEPT_BANK.md  WORKFLOW.md  TALK.md
```
