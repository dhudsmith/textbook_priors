# Textbook priors over visual features

A reproducible medical-imaging study, built as one Snakemake workflow on Palmetto2 with an AI
coding agent, and the running example for *Reproducible scientific computing with AI coding
agents* (Clemson HPC Day).

**The question.** A multimodal language model carries textbook knowledge about what pathology
looks like. Can that knowledge stand in for labelled data? On the twelve MedMNIST 2D benchmarks,
a vision-language model (VLM) hosted on Clemson's RCD LLM Service scores each image against a
curated bank of diagnostic visual features. Classifiers built on those scores are compared with
convolutional networks trained on pixels, across training-set size, image resolution and VLM size.

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
  provenance (sources, method, reviewer). Produced by the procedure in `CONCEPT_BANK.md`. Each
  concept carries a `question`, an ordered `scale` of two to five levels, and an `anchors` block
  giving every level a described visual referent with its own source keys — so the model is told
  what `mild` looks like rather than left to invent the threshold. Each class carries a
  `fingerprint` naming every concept with a level or `any`. A smoke test validates the schema, the
  completeness of every `anchors` block, and the class names against the MedMNIST label maps.
  `data/concepts/README.md` records the method, the simulated-review statement and the bank's
  known limits, including the concepts whose anchors cannot be applied at 224 pixels.
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
| A zero-shot | no | the VLM's class distribution from the image and class names |
| B textbook-only | no | concept scores matched to the bank's class fingerprints; no training |
| C concept regression | yes | logistic regression on the concept-score vector, n labelled images |
| D description embedding | yes | logistic regression on the embedding of the VLM's free-text description |
| E pixel network | yes | ResNet-18 per resolution and seed on the full training split |
| F pixel network + prior | yes | E with concept scores fused late, and with zero-shot probabilities as a soft label; the learning-curve arm |

Four figures: the learning curve of E against F (how many labelled images is the textbook
worth); A and B against VLM size; E against resolution and GPU minutes; the per-modality gap
between concept-based and pixel-based accuracy. If time is short, D is dropped first.

## 7. Stages

```
0  SMOKE      bank schema and anchors, prompt rendering, metric conventions, client retry  seconds
1  FETCH      MedMNIST from the pinned release, checksummed; data/raw on scratch           1 job
2  CACHE      per dataset x size: uint8 arrays, labels, the seeded samples                 48 CPU
3  TRAIN      per dataset x size x seed, and the learning-curve grid at one size           GPU
4  SCORE      per dataset x VLM x chunk of ~100 images: concept scores, zero-shot          CPU,
              distribution, description; raw responses archived                            throttled
5  EMBED      per dataset: embeddings of the descriptions                                  CPU
6  CLASSIFY   per dataset x arm x n x seed: arms B, C, D; arm F training                   CPU / GPU
7  EVALUATE   every arm on the test sample; medmnist evaluator; paired bootstrap           CPU
8  REPORT     reconciliation against the published table; tables, macros, figures; the
              technical report                                                            local
```

Targets: `all` (the technical report), `smoke`, `cache`, `train`, `score`, `classify`, `evaluate`,
`report`. Opt-in diagnostics outside `all`: `reasoning_sweep` (does a reasoning level help a
model look at a picture, at what cost per image), `prompt_ablation` (how much of arm B is the
bank and how much the model, including anchored scale levels against bare ones),
`vlm_utilisation` (calls per minute per model against the caps).

## 8. The scoring stage

The one stage type not seen in earlier projects, and the one that tests principle 9.

- **Unit**: one dataset, one VLM, one chunk. Output `results/score/<dataset>__<model>__<split>__chunk<k>.json`:
  per image the concept scores as integers on the bank's scales, the zero-shot distribution, the
  description, and the raw response. The manifest adds the served model name from the response,
  the prompt-template hash, the concept-bank file hash, temperature, reasoning level, timestamp.
- **Prompt**: rendered from the bank by a pure function, tested in `smoke`; the image at 224
  pixels; structured JSON requested and validated against the scales; one retry on a malformed
  answer, then recorded as missing, never guessed. The renderer emits each concept's question, its
  ordered levels, and — when `vlm.prompt.anchors` is true, the default — the anchor text for every
  level, which is what makes an ordinal answer mean the same thing to the model as it did to the
  source. The model still answers with the bare level token, so the parser and the archive format
  do not change. Rendering bare from an anchored file leaves the concept-bank file hash identical
  and moves only the prompt-template hash, so the manifest already distinguishes the two
  renderings without a second copy of the bank.
- **Throttling**: `resources: llm_<model>=1` on the rule, caps below each model's published
  concurrency in the profile, so the workflow is never the noisy neighbour while GPU training runs
  unconstrained beside it.
- **Client**: the `openai` package against `https://llm.rcd.clemson.edu/v1`; backoff on 429 and
  5xx; raw response archived before parsing. The key is read from an owner-only file whose path is
  in config; it is never in config, the repository, a command line or a log.
- **Environment**: its own file, so the client never invalidates the numpy or torch tiers.
- **Reasoning level**: a per-model config knob, `none` by default; swept only in the diagnostic.

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
  prompt: {anchors: true}   # render each scale level with its anchor text; false = bare tokens
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
   reaches the service, the archive and manifest are right, a malformed response is handled. Then
   the full fan-out under the caps.
5. Arms A to D; evaluate; the size and modality figures.
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
- Whether to re-score with bare scale levels to measure what the anchors buy. Anchors change the
  concept scores themselves, so this is a second archive for the arms that read them, not a
  reporting choice — principle 9 says that is a deliberate act. Default: run it as a
  `prompt_ablation` subset on two or three datasets before considering a full re-score. The bare
  bank is committed history, so the contrast is available without re-authoring anything.
- Total call volume, roughly 120,000 at the default samples, against the allocation.
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
data/raw -> scratch       MedMNIST files; data/cache the arrays; gitignored
results/                  one JSON per unit of work; results/score/ is the response archive
benchmarks/  logs/        per job
report/                   report.tex, references.bib; tables/ and figs/ generated
README.md  CHANGELOG.md  CLAUDE.md  CONCEPT_BANK.md  WORKFLOW.md
```
