# Textbook priors over visual features

A reproducible medical-imaging study, built as one Snakemake workflow on Palmetto2 with an AI
coding agent, and the running example for *Reproducible scientific computing with AI coding
agents* (Clemson HPC Day).

**The question.** A multimodal language model carries textbook knowledge about what pathology
looks like. Can that knowledge stand in for labelled data, and in what form does it have to be
delivered before it helps? On the twelve MedMNIST 2D benchmarks, a vision-language model (VLM)
hosted on Clemson's RCD LLM Service both scores each image against a curated bank of diagnostic
visual features and is asked to name the class outright, with and without that same bank rendered
into its prompt. Classifiers built on the scores are compared with convolutional networks trained
on pixels, across training-set size, image resolution and VLM size.

The concept bank is prepared outside the workflow and committed as an input; see
`CONCEPT_BANK.md`. Conventions for every rule below are the `research-workflow` skill
(`~/.claude/skills/research-workflow/SKILL.md`); the agent loads it before touching the workflow.

---

## 1. Principles

Each principle names the failure it prevents and the mechanism that enforces it here.

1. **The workflow is the documentation.** The Snakefile reads top to bottom through numbered
   stages, each opening with a paragraph of scientific prose. The dependency graph *is* the
   project structure, and a dry run prints it. Nothing about the flow lives only in someone's head.
2. **Every number has a rule.** No ad hoc scripts, no notebook cells, no hand-copied values. If a
   number appears in a table, a figure or the report, a rule produced it from declared inputs. The
   workflow ends in a **technical report**, not a manuscript: the complete record of the question,
   the data provenance, the methods as executed, every table and figure, the reconciliation, the
   diagnostics and the run record, built from generated tables and number macros so it cannot state
   a value the run did not produce. The authors write the paper from it. Interpretation and claims
   stay with them.
3. **Inputs are pinned, not vendored.** Large data is the output of a fetch rule from a pinned
   release with recorded checksums. A fresh clone bootstraps itself, and the exact input version is
   in the repository even though the bytes are not.
4. **Dependencies are explicit and complete.** The modules a rule's numbers depend on are inputs;
   the config values they depend on are params; the environment is declared per rule. Editing any
   of them reruns exactly the jobs whose numbers could have changed, and nothing else.
5. **Every result carries its own provenance.** Each unit of work writes one JSON with a manifest:
   parameters, seeds, git commit and dirty flag, package versions, host, wall time. A result can
   always be traced back to a line in config and a commit.
6. **Randomness is owned per cell.** Each job seeds its own generator from config; there is no
   shared module-level state, so inserting a cell never moves another cell's numbers.
7. **Computation and reporting are separate.** Stages write results; report rules read only
   results. No script prints a table it also computed.
8. **Resources are measured, not guessed.** Every submitted rule records wall time and peak
   memory; requests are set from those measurements with the reasoning written down.
9. **Non-reproducible boundaries are made explicit.** An LLM call cannot be reproduced bit for bit
   once the served model changes. Every response is archived raw with the served model name and
   prompt hash; everything downstream is a deterministic function of the archive; re-querying is a
   deliberate act, not a side effect.
10. **Reconcile, never silently replace.** Regenerated numbers are compared against the published
    benchmark table and written to a report that says what moved and by how much.
11. **Structure and history live apart.** The README describes what the project is; a dated
    change log records what was learned and corrected. The README never becomes a lab notebook.

## 2. Before and after

| before | now |
|---|---|
| a folder of numbered scripts run in an order I remembered | one Snakefile whose dry run prints the order |
| "which version of the data did this come from?" | a fetch rule with a pinned release and checksums |
| editing a module and hoping downstream results were still valid | the module is an input; Snakemake reruns exactly what depends on it |
| a conda env that grew by accretion and could not be rebuilt | three declared environment files, one per toolchain |
| results in folders named by date, seeds set somewhere | one JSON per cell with a manifest and its own seed |
| copying numbers into the manuscript by hand | a generated technical report; the manuscript is written from it and checked against it |
| requesting 8 cores and 64 GB for everything | per-rule requests set from measured usage |
| sbatch scripts in the log directory to redo one thing | a rule; or a gitignored scratch directory that is never cited |
| a README that turned into a notebook | README for structure, CHANGELOG for findings |

## 3. Why this works with an AI coding agent

The workflow and the agent reinforce each other, in both directions.

- **The workflow is the context.** A Snakefile with stage prose, a config with commented grids
  and a README with the layout express the project more precisely than any prompt. The agent
  reads the same document the human reads, and it is machine-checked: a dry run and a lint tell
  both of us whether an edit fits.
- **Conventions replace steering.** The decisions that used to be re-explained every session are
  written once as a skill with templates. The agent applies them; the human reviews the diff. The
  conversation is about the science, not about where the log goes.
- **Structure constrains the agent where it needs constraining.** "Every number has a rule" means
  the agent cannot quietly answer a question with a one-off script. A new computation forces a
  rule, a config entry, a code bundle, a benchmark and a log, and so becomes part of the record.
- **The agent sees what the human sees.** Manifests, logs and benchmarks give the agent the
  evidence to diagnose a failure or right-size a request with the same information a person would
  use, and its reasoning is written into comments and the change log where a person can check it.
- **The dependency graph makes edits safe.** When the agent adds a model or a grid point, the dry
  run shows exactly what will rerun. Surprises are visible before any compute is spent.

## 4. Opportunities and challenges that are specific to science

Software engineering has its own literature on working with coding agents. Science adds an
asymmetry: the code is not the product, the claim is, and a claim rests on understanding what was
done. That produces one opportunity and one challenge that are not the general case.

**The opportunity: the recipe becomes cheap to write and cheap to keep honest.** The work of
making a study reproducible (fetch rules, manifests, declared environments, generated tables, a
complete technical report) is exactly the work researchers skip under deadline. An agent does it
without complaint, and a convention makes it do it the same way every time. Reproducibility stops
being a virtue practised after the fact and becomes the default shape of the project. What the
agent produces is the evidence base; the paper, the interpretation and the claim remain the
authors' work, written from a record that is complete.

**The challenge: understanding debt.** An agent can produce a working stage faster than its owner
can understand it. Every such stage is a loan against future comprehension: the numbers exist, the
paper cites them, and the person whose name is on the paper cannot say from memory how they were
made. Technical debt slows the next change; understanding debt undermines the claim itself. The
two questions it raises are *what did the agent do* and *how do I know it is right*.

**What the workflow repays.** Snakemake expresses the work as a recipe, and a recipe is
inspectable in ways a transcript is not.

- *What was done* is answered by the DAG. Every computation is a rule with declared inputs,
  declared code, a log and a manifest. There is no hidden step, because a hidden step would have no
  rule and so no place to put its output.
- *In what order and from what* is answered by a dry run, which prints the plan before a job runs
  and the rerun reasons after an edit.
- *With which code and settings* is answered by the manifest: commit, parameters, seeds, versions.
- *Why* is answered by prose the agent is required to write: the stage banner states the
  scientific question and the reason for each non-obvious choice. A wrong explanation is visible
  in a way a wrong line of code is not, and writing it forces the agent to have one.
- *Whether the numbers are plausible* is answered by reconciliation against the published table
  and by the smoke tests, which are the parts of the recipe that check the recipe.

**What it does not repay.** A rule can be structurally perfect and scientifically wrong: the right
metric on the wrong split, a leak between train and test, an evaluator that silently handles
multi-label as multi-class. The DAG shows that a stage exists and what it depends on; it does not
show that the stage computes the right thing. That remains the owner's job, and the workflow's
contribution is to make the job tractable: one stage at a time, small before large, with a test
or a published number to check against, and a change log that records what was understood and
when. The practices that pay the debt down:

- Read every rule the agent writes before it runs at scale, as one would a student's code.
- Run one cell first and check it by hand against a known answer; only then fan out.
- Ask the agent to explain a stage in the banner, then judge the explanation, not the code.
- Keep the CHANGELOG as the owner's record of understanding, not the agent's record of activity.
- Treat any number without a reconciliation or a test as provisional, in the report and in
  anything written from it.

The honest summary for a slide: the workflow converts hidden work into inspectable work. It does
not inspect it for you.

## 5. Inputs given at the outset

- **The concept bank**, `data/concepts/<dataset>.yaml`, one file per dataset, committed with
  provenance (sources, method, reviewer). Produced by the procedure in `CONCEPT_BANK.md`. A smoke
  test validates the schema and the class names against the MedMNIST label maps.
- **MedMNIST v2**, through the `medmnist` package at a pinned version, including the 224-pixel
  files. Twelve datasets, official train/validation/test splits, sizes 28/64/128/224. Task types:
  multi-class (pathmnist, dermamnist, octmnist, bloodmnist, tissuemnist, organa/c/smnist), binary
  (pneumoniamnist, breastmnist), multi-label (chestmnist, 14 findings), ordinal (retinamnist). The
  fetch rule records counts and checksums; the `medmnist` evaluator gives comparable metrics.
- **The VLMs** on the RCD LLM Service, by concrete name, never alias: `qwen3.5-9b`,
  `gemma-4-12b`, `qwen3.8-27b-fp8`, `gemma-4-31b`, each with its published concurrency in config.
  Text embeddings from `qwen3-embedding-4b`.

## 6. Arms

All arms predict on the same seeded test sample per dataset, so comparisons are paired.

| arm | labels | what it is |
|---|---|---|
| A1 zero-shot, plain | no | the VLM's class distribution from the image, the class names and a one-sentence statement of the task |
| A2 zero-shot, textbook | no | A1's prompt with the bank's concept questions and class fingerprints rendered into it; the model does the aggregation |
| B textbook-only | no | concept scores matched to the bank's class fingerprints by a deterministic rule; no training |
| C concept regression | yes | logistic regression on the concept-score vector, n labelled images |
| D description embedding | yes | logistic regression on the embedding of the VLM's free-text description |
| E pixel network | yes | ResNet-18 per resolution and seed on the full training split |
| F pixel network + prior | yes | E with concept scores fused late, and with zero-shot probabilities as a soft label; the learning-curve arm |

**A1, A2 and B are a ladder, not three unrelated baselines.** They deliver the same prior in three
forms: absent, as prose, as structure. A1 and A2 differ in exactly one respect, a block of rendered
bank text, so whatever separates them is attributable to the bank rather than to the prompt, the
sample or the parser. A2 and B differ in exactly one respect, whether the model or a deterministic
rule turns visual features into a class. Together they answer not only whether the textbook helps
but in what form it has to be delivered before it does, which is the more useful finding and the
one no single arm can produce.

Two qualifications, stated here and repeated in the report. A1 is not prior-free: a class list
containing `melanocytic_nevus` already carries most of a dermatology textbook, so the contrast is a
structured description on top of class names, not knowledge against ignorance. And A2's prompt is
several times longer than A1's, so a gain could come from the tokens rather than from their
content. The `scrambled` variant of section 8 controls for the second: the same bank text with the
fingerprints permuted across classes, which preserves length, vocabulary and structure while
destroying the mapping. If it scores like A2, the shape of the prompt is doing the work; if it
falls back to A1, the bank's content is.

Four figures: the learning curve of E against F (how many labelled images is the textbook
worth); A1, A2 and B against VLM size; E against resolution and GPU minutes; the per-modality gap
between concept-based and pixel-based accuracy. If time is short, D is dropped first, then the
`scrambled` control.

## 7. Stages

```
0  SMOKE      concept-bank schema, prompt rendering against goldens, metric conventions,
              client retry                                                                 seconds
1  FETCH      MedMNIST from the pinned release, checksummed; data/raw on scratch           1 job
2  CACHE      per dataset x size: uint8 arrays, labels, the seeded samples                 48 CPU
3  TRAIN      per dataset x size x seed, and the learning-curve grid at one size           GPU
4  SCORE      per dataset x VLM x chunk of ~100 images: concept scores, one class          CPU,
              distribution per zero-shot variant, description; responses archived          throttled
5  EMBED      per dataset: embeddings of the descriptions                                  CPU
6  CLASSIFY   per dataset x arm x n x seed: arms B, C, D; arm F training                   CPU / GPU
7  EVALUATE   every arm on the test sample; medmnist evaluator; paired bootstrap           CPU
8  REPORT     reconciliation against the published table; tables, macros, figures; the
              technical report                                                            local
```

Targets: `all` (the technical report), `smoke`, `cache`, `train`, `score`, `classify`, `evaluate`,
`report`. Opt-in diagnostics outside `all`: `reasoning_sweep` (does a reasoning level help a
model look at a picture, at what cost per image), `blind_labels` (A2 with the class names replaced
by neutral letters, separating what the bank's descriptions carry from what the names carry),
`vlm_utilisation` (calls per minute per model against the caps).

## 8. The scoring stage

The one stage type not seen in earlier projects, and the one that tests principle 9.

- **Unit**: one dataset, one VLM, one chunk. Output `results/score/<dataset>__<model>__<split>__chunk<k>.json`:
  per image the concept scores as integers on the bank's scales, one class distribution per enabled
  zero-shot variant, the description, and the raw response behind each call. The manifest adds the
  served model name from the response, the concept-bank file hash, the template hash of every
  prompt rendered, temperature, reasoning level, timestamp.
- **Calls per image**: one for the concept scores, one for the description, and one for each
  variant in `vlm.zero_shot.variants`. They are separate calls, never one response carrying several
  fields, so that no arm's answer can condition on another's and each is archived raw on its own.
- **Prompt**: every prompt in this stage is rendered from the concept-bank file by a pure function
  in `priors/prompts.py`, described below; nothing is written by hand per dataset. The image at 224
  pixels; structured JSON requested and validated against the scales and the medmnist label map;
  one retry on a malformed answer, then recorded as missing, never guessed.
- **Throttling**: `resources: llm_<model>=1` on the rule, caps below each model's published
  concurrency in the profile, so the workflow is never the noisy neighbour while GPU training runs
  unconstrained beside it.
- **Client**: the `openai` package against `https://llm.rcd.clemson.edu/v1`; backoff on 429 and
  5xx; raw response archived before parsing. The key is read from an owner-only file whose path is
  in config; it is never in config, the repository, a command line or a log.
- **Environment**: its own file, so the client never invalidates the numpy or torch tiers.
- **Reasoning level**: a per-model config knob, `none` by default; swept only in the diagnostic.

### The prompt generator

`priors/prompts.py` is the only place a prompt string is built, and the mapping from a bank file to
its text is fixed: the templates are constants in the module, the dataset's file supplies every
varying word, and no branch of the renderer depends on which dataset it was handed. Three entry
points, one template each.

| function | used by | what varies between datasets |
|---|---|---|
| `render_scoring_prompt(bank)` | B, C, D, F | the concept questions and their scales |
| `render_zero_shot_prompt(bank, variant)` | A1, A2 | the class names, and for `textbook` the rendered bank block |
| `render_description_prompt(bank)` | D | the modality line only |

`render_zero_shot_prompt` assembles one string from three parts, and the variant selects only
whether the middle part is present:

1. a task preamble naming the modality and stating that the answer is a probability over the
   classes listed below;
2. **the textbook block**, present for `textbook` and `scrambled`, absent for `plain`: each concept
   as its question and ordered scale, then each class as the levels its fingerprint expects, with
   `any` rendered as an explicit statement that the literature does not commit;
3. the class list in medmnist label-map order, and the output schema.

Everything outside part 2 is byte-identical across variants, which is what makes A1 against A2 a
single-variable contrast rather than two prompts that happen to differ. `scrambled` renders part 2
from the same bank with the fingerprints permuted across classes by a seeded permutation recorded
in the manifest, so it matches `textbook` in length, vocabulary and structure and differs only in
whether the mapping is the real one. Class order is the label map's and is fixed rather than
shuffled, so whatever position bias a model has is at least the same bias in every variant.

The renderer takes an already-parsed bank and returns a string: it opens no files, reads no config
and consults no clock, so its output can be pinned. `smoke` renders every variant for all twelve
datasets and diffs against committed goldens under `tests/goldens/`. A template edit is therefore a
visible change to those goldens, and it moves the template hash, which reruns exactly the scoring
jobs whose numbers could have changed.

## 9. Config, environments, resources

```yaml
datasets: [pathmnist, chestmnist, dermamnist, octmnist, pneumoniamnist, retinamnist,
           breastmnist, bloodmnist, tissuemnist, organamnist, organcmnist, organsmnist]
sizes: [28, 64, 128, 224]
seeds: [0, 1, 2]
learning_curve: {n: [50, 100, 200, 500, 1000, 2000], size: 224, seeds: [0, 1, 2]}
sample: {test_n: 500, train_n: 2000, seed: 0, cache_cap_224: 60000}
vlm:
  models:
    qwen3.5-9b:      {concurrency: 128, cap: 96}
    gemma-4-12b:     {concurrency: 32,  cap: 24}
    qwen3.8-27b-fp8: {concurrency: 64,  cap: 48}
    gemma-4-31b:     {concurrency: 16,  cap: 12}
  chunk: 100
  temperature: 0.0
  reasoning: none
  zero_shot:
    variants: [plain, textbook]   # add `scrambled` to run the prompt-length control
    scramble_seed: 0              # permutation of fingerprints across classes, in the manifest
  base_url: https://llm.rcd.clemson.edu/v1
  key_file: ~/.config/rcd_llm/key
  embedding_model: qwen3-embedding-4b
train: {arch: resnet18, epochs: 100, gpu: {enabled: true, type: a100, cpus: 8, mem_mb: 32000, runtime: 240}}
published: config/published.yaml
resources: {...}      # first guesses, then set from benchmarks/ with the reasoning in comments
```

Environments: `envs/priors.yml` (numpy, scipy, pandas, scikit-learn, matplotlib, pyyaml, pytest,
medmnist), `envs/priors_torch.yml` (plus the CUDA torch wheel), `envs/priors_llm.yml` (openai,
pyyaml, numpy, pillow). Loose floors; exact versions in every manifest.

Resources to measure before trusting: 28-pixel training leaves an A100 nearly idle, so pack
cells per GPU job once a utilisation sample says so and record the number; scoring jobs are
network-bound and need one core; the cache for tissuemnist and the 224 files scales with the
array size; profile `cores` and `jobs` sized so the widest fan-out runs as one wave against the
per-model caps.

## 10. Order of work

1. Skeleton from the skill's templates; the concept-bank schema test with the twelve files.
2. Fetch and cache at 28 and 224; verify counts and checksums.
3. Arm E on one dataset at 28; benchmark; set resources; the full resolution sweep; reconcile 28
   and 224 against the published table before anything else is trusted.
4. The client and one scoring chunk of ten images on one dataset and model: confirm a compute node
   reaches the service, the archive and manifest are right, a malformed response is handled, and
   each zero-shot variant left its own archived call. Then the full fan-out under the caps.
5. Arms A1, A2, B, C and D; evaluate; the size and modality figures. Read one rendered `textbook`
   prompt end to end before the fan-out: that text is the arm, and a wrong one is not visible in
   the numbers it produces.
6. The learning curve, E then F; the crossing figure.
7. Tables, figures, the technical report; a CHANGELOG entry per milestone; the README stage
   table with job counts.
8. Demo rehearsal.

Commit after each coherent change with a descriptive imperative sentence. Dry-run and lint before
every submission; ask before any GPU jobs or more than 50 CPU jobs.

## 11. The demo

Everything runs before the talk; the response archive is the fixed input. Live, and reversible:

- Add a fifth VLM to the config. The dry run lists exactly the new scoring chunks, the classify
  jobs that read them and the tables downstream, and nothing else.
- Ask the agent to make the reasoning level a wildcard of the score rule; watch it change the
  config, the rule, the entry point and the resource cap together, then dry-run.
- Show a scoring log where the cap held, and the calls-per-minute summary against the published
  concurrency.

Record each beforehand as a fallback for a slow queue or a sleeping model.

## 12. Open decisions

- Learning-curve resolution: 224 matches what the VLM saw (default); 64 buys more points and seeds.
- How the prior enters arm F: late fusion, soft label, or both (default both).
- ChestMNIST in all arms, or A and E only (default all).
- Total call volume against the allocation. One call per image per model per dataset is 24,000 at
  the default sample (500 test images x 12 datasets x 4 models), so A2 adds 24,000 to the roughly
  120,000 of the original plan and `scrambled` another 24,000 if enabled.
- Whether `scrambled` runs on all twelve datasets or a subset. Its job is to rule out a length
  effect, which three datasets across three modalities may settle as well as twelve (default:
  three, chosen before the numbers are seen).
- Acceptable-use confirmation for de-identified public medical images; one sentence on a slide.

## 13. Layout

```
Snakefile                 one file, nine labelled stages
config/config.yaml        every grid and knob; per-rule resources
config/published.yaml     the MedMNIST v2 benchmark table
profiles/palmetto/        SLURM executor; job, core and per-model llm_* caps
profiles/local/           dry runs, smoke, touch
envs/                     priors.yml  priors_torch.yml  priors_llm.yml
priors/                   data cache models train prompts llm score classify evaluate report stages manifest
data/concepts/            the twelve concept-bank files, committed
tests/goldens/            every rendered prompt, one per dataset x variant; smoke diffs against these
data/raw -> scratch       MedMNIST files; data/cache the arrays; gitignored
results/                  one JSON per unit of work; results/score/ is the response archive
benchmarks/  logs/        per job
report/                   report.tex, references.bib; tables/ and figs/ generated
README.md  CHANGELOG.md  CLAUDE.md  CONCEPT_BANK.md  WORKFLOW.md
```
