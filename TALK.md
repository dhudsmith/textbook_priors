# Reproducible scientific computing with AI coding agents

The talk narrative for Clemson HPC Day, using this repository as the running example. The
scientific and engineering plan is `WORKFLOW.md`; this file carries only the argument and the
demo. Nothing here is a requirement on the workflow.

## 1. Before and after

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

## 2. Why this works with an AI coding agent

The workflow and the agent reinforce each other, in both directions.

- **The workflow is the context.** A Snakefile with stage prose, a config with commented grids and
  a README with the layout express the project more precisely than any prompt. The agent reads the
  same document the human reads, and it is machine-checked: a dry run and a lint tell both of us
  whether an edit fits.
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

## 3. What is specific to science

Software engineering has its own literature on working with coding agents. Science adds an
asymmetry: the code is not the product, the claim is, and a claim rests on understanding what was
done. That produces one opportunity and one challenge that are not the general case.

**The opportunity: the recipe becomes cheap to write and cheap to keep honest.** The work of making
a study reproducible (fetch rules, manifests, declared environments, generated tables, a complete
technical report) is exactly the work researchers skip under deadline. An agent does it without
complaint, and a convention makes it do it the same way every time. Reproducibility stops being a
virtue practised after the fact and becomes the default shape of the project. What the agent
produces is the evidence base; the paper, the interpretation and the claim remain the authors'
work, written from a record that is complete.

**The challenge: understanding debt.** An agent can produce a working stage faster than its owner
can understand it. Every such stage is a loan against future comprehension: the numbers exist, the
paper cites them, and the person whose name is on the paper cannot say from memory how they were
made. Technical debt slows the next change; understanding debt undermines the claim itself. The two
questions it raises are *what did the agent do* and *how do I know it is right*.

**What the workflow repays.** Snakemake expresses the work as a recipe, and a recipe is inspectable
in ways a transcript is not.

- *What was done* is answered by the DAG. Every computation is a rule with declared inputs,
  declared code, a log and a manifest. There is no hidden step, because a hidden step would have no
  rule and so no place to put its output.
- *In what order and from what* is answered by a dry run, which prints the plan before a job runs
  and the rerun reasons after an edit.
- *With which code and settings* is answered by the manifest: commit, parameters, seeds, versions.
- *Why* is answered by prose the agent is required to write: the stage banner states the scientific
  question and the reason for each non-obvious choice. A wrong explanation is visible in a way a
  wrong line of code is not, and writing it forces the agent to have one.
- *Whether the numbers are plausible* is answered by reconciliation against the published table and
  by the smoke tests, which are the parts of the recipe that check the recipe.

**What it does not repay.** A rule can be structurally perfect and scientifically wrong: the right
metric on the wrong split, a leak between train and test, an evaluator that silently handles
multi-label as multi-class, a baseline so weak that the headline claim is true by construction. The
DAG shows that a stage exists and what it depends on; it does not show that the stage computes the
right thing. That remains the owner's job, and the workflow's contribution is to make the job
tractable: one stage at a time, small before large, with a test or a published number to check
against, and a change log that records what was understood and when. The practices that pay the
debt down:

- Read every rule the agent writes before it runs at scale, as one would a student's code.
- Run one cell first and check it by hand against a known answer; only then fan out.
- Ask the agent to explain a stage in the banner, then judge the explanation, not the code.
- Keep the CHANGELOG as the owner's record of understanding, not the agent's record of activity.
- Treat any number without a reconciliation or a test as provisional, in the report and in anything
  written from it.

The honest summary for a slide: the workflow converts hidden work into inspectable work. It does
not inspect it for you.

**A worked example of the last point.** The first version of this project's plan compared a
zero-shot vision-language model against a ResNet-18 trained from scratch on as few as 50 images.
Every rule would have been correct and every number reproducible, and the headline claim would have
been an artefact of an unfair baseline. What caught it was a person reading the plan, not the DAG.
The fix is in `WORKFLOW.md` §3 and the first entry of `CHANGELOG.md`.

## 4. The demo

Everything runs before the talk; the response archive is the fixed input. Live, and reversible:

- Add a fifth VLM to the config. The dry run lists exactly the new scoring chunks, the classify
  jobs that read them and the tables downstream, and nothing else.
- Ask the agent to make the reasoning level a wildcard of the score rule; watch it change the
  config, the rule, the entry point and the resource cap together, then dry-run.
- Show a scoring log where the cap held, and the calls-per-minute summary against the published
  concurrency.

Record each beforehand as a fallback for a slow queue or a sleeping model.
