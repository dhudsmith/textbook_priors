# Reproducible scientific computing with AI coding agents

The talk narrative for Clemson HPC Day, using this repository as the running example. The
scientific and engineering plan is `WORKFLOW.md`; this file carries only the argument and the
demo. Nothing here is a requirement on the workflow.

## 1. Before and after

| before | now |
|---|---|
| a folder of numbered scripts run in an order I remembered | one Snakefile whose dry run prints the order |
| "which version of the data did this come from?" | a pinned release and a recorded checksum, verified once and treated as a fixed input |
| editing a module and hoping downstream results were still valid | the module is an input; Snakemake reruns exactly what depends on it |
| a conda env that grew by accretion and could not be rebuilt | two declared environment files, one per toolchain |
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
a study reproducible (pinned inputs, manifests, declared environments, generated tables, a complete
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

## 4. The demo: recorded, not live

Twenty-five minutes with a second keynote following leaves no room for a queue or a sleeping
model. Everything is recorded beforehand and played as a clip, at most two of them:

- `snakemake -n` after editing one bank file: exactly one job reruns, with Snakemake's reason.
- The reader wildcard added to the score rule: config, rule, entry point and cap change together,
  then the dry run lists the twenty-four new chunks and nothing else. This is the refactor that H4
  actually needed, so the clip shows work that happened rather than work staged for a talk.

## 5. The talk, slide by slide

Twenty-five minutes, five for questions. Fixed 2026-09-12 with the owner. The H4 chain landed that
evening on all 200 images and the pattern scene 6 describes held (`CHANGELOG.md`, 2026-09-12, "H4
decided"), so nothing below is provisional.

**The refrain**, said four times in slightly different words: *the workflow turns hidden work into
inspectable work. It does not inspect it for you.* Beneath it, the two questions every scene comes
back to: *what did the agent do?* and *how do I know it is right?*

**Style**: one idea per slide, a picture on every slide, almost no bullet lists, numbers only where
a number changes what the audience believes. The project is the running example throughout and is
never the subject.

| # | minutes | scene | what is on the screen |
|---|---|---|---|
| 1 | 2 | **Cold open.** One chest X-ray at 224 pixels beside the textbook's checklist of what to look for. The question: how much of that does a vision-language model actually see? Then the turn: this talk is not about the answer. It is about how I could trust an answer when an AI agent wrote most of the code in three days. | the image; the concept bank rendered as a paper checklist with citations; the refrain, first time |
| 2 | 3 | **The old way and the new way.** Nine before/after pairs from §1, shown as pictures not a table: a folder of numbered scripts against one Snakefile whose dry run prints the order; a README that became a notebook against README, CHANGELOG and SESSION_LOG each doing one job. | two desks side by side, then two or three pairs picked out |
| 3 | 4 | **The recipe.** Seven stages, one file, every number has a rule. The agent reads the same document I read, and a dry run checks us both. | the DAG collapsed to stages; a terminal capture of `snakemake -n` after a bank edit, one job and its reason; one manifest with `served_model` and the prompt hash highlighted |
| 4 | 7 | **Three scenes where it nearly went wrong**, told in order, each ending on what caught it. *(a) The unfair baseline*: a ResNet trained from scratch on fifty images against a model with billions of parameters of pretraining. Every rule correct, the claim worthless. A person reading the plan caught it; the DAG could not have. Refrain, second time. *(b) One chunk before 270*: rules generated in a loop all shared the last model's command. The first chunk came back with gemma's answers under qwen's file name, and the only trace was one manifest field disagreeing with the file it sat in. *(c) The wave that wrote nothing*: forty-eight jobs, two hours, zero output, because a call that takes 1.5 seconds alone takes 43 under our own load and 134 under eleven thinking chunks. Concurrency buys no throughput on a saturated endpoint; a cap is politeness, and the time limit is what decides whether anything is saved. | (a) the two plans side by side, one word changed; (b) the manifest and the filename, the disagreement circled, then the rule written out four times; (c) the contention chart: seconds per call against jobs in flight, and aggregate calls per second flat across it |
| 5 | 4 | **What the evidence says.** Three hypotheses, rules fixed before any number existed, three verdicts computed rather than chosen: all unsupported, on six datasets and again on twelve. The honest headline: the textbook prior is worth fewer than fifty labelled images on nine tasks of eleven. And the twist the controls supply: the concept answers carry real class information; the textbook's own readout throws it away, except where the model cannot name the class at all: on kidney cell types its own guess is at chance and the checklist still ranks. Then the comparison the plan never named, read off the same figure: the concept regression against the model's own zero-shot guess, the dotted line. It crosses at fifty labels on seven datasets, at a thousand on one, and never on three: on pneumoniamnist the regression is flat at 0.73 across the whole curve while zero-shot sits at 0.92, so the model knows more about those films than its concept answers carry. Not a hypothesis and not pre-registered; a reading of a figure the rules already made. A negative result you can stand behind is what the recipe is for. | the learning curve, six panels or three, with the zero-shot line picked out; a verdict slide with three rows and three "not supported"; the permutation drop in one bar |
| 6 | 4 | **What if we added reasoning?** The workflow in practice, over one day. The question had shifted: not whether the textbook substitutes for labels, but how much of the features the model *sees*. So: a *reader* is a model plus a reasoning effort; the four models already archived are readers at effort none. 15:20, a test overturns a standing claim (thinking never worked here, and the cause was our own 512-token budget). 16:00, a decision rule is written before a call is bought: six of six or nothing. 16:12, one chunk runs first and the gateway model refuses temperature zero. 17:35, eleven chunks at once and a timed call says 134 seconds; cancelled, capped at four, same finish time, no chunk near its limit. Then the result: a frontier model reads cited features no better than a 27B open model, and thinking is not "help" or "no help" but conditional: it costs the tasks the model already read well and rescues the ones it read badly. The next morning the study grew to twelve datasets and the pattern held on eleven: the three worst baselines took the three clear gains. One beat of contrast: an arm added after seeing the numbers was removed the same day, because it could decide nothing; this one was kept because it was pre-registered. | a one-day timeline with the session log's timestamps as the ticks; the reader-chain figure; the scatter of thinking's effect against the baseline's probe AUC, one point per dataset, the line sloping down |
| 7 | 1 | **Close.** The recipe and the transcript, side by side: the Snakefile and the session log. One is what was done; the other is why. You need both, and the workflow gives you the first for free. Refrain, last time. Hands-on at 3:35. | Snakefile header beside SESSION_LOG.md, same font, same size |

**Visual assets.** Already generated by the workflow, in `~/Code/textbook_priors`, now over all
twelve datasets (the six the talk was built on are the first six panels and rows; CHANGELOG.md,
2026-09-13, carries both readings): the five figures under `report/figs/` (the learning curve, the
n_B plot, the model ladder, the reader chain, and the scatter of thinking's effect against baseline
probe AUC that scene 6 ends on), every table
under `report/tables/`, the report PDF, the manifests, the rendered prompts under
`results/prompts/`, a concept-bank file, the Snakefile header, the session log. To make for the
talk, none of them a computation:

1. The DAG, rendered by Snakemake and collapsed to stages.
2. The before/after pairs as pictures.
3. The contention chart, from measurements already in CHANGELOG.md: 1.5 s at one stream, 16.7 s for
   one thinking chunk alone, 52 s at four, 134 s at eleven, 43 s at twenty-four, 89 s at forty-eight.
4. The one-day timeline for scene 6, ticks from SESSION_LOG.md.
5. Two terminal captures: the one-job dry run, and the manifest-versus-filename disagreement.
6. The verdict slide.

**What was cut from the first draft, and why.** The demo went from live to recorded (no room in
twenty-five minutes). The scenes went from four to three; the two dropped — *the field we did not
read* and *the median that was not a median* — are held as alternates if a scene runs short, and
both fit the refrain. A third alternate arrived after the plan was fixed: the embedding idea of the
same evening, checked at the wire within the hour, found impossible on this service, and rewound
(`SESSION_LOG.md`, 2026-09-12 22:30 to 23:15) — a probe caught it, not the DAG. The results section
shrank from a hypothesis-by-hypothesis walk to one figure and one verdict slide, because the talk is
about the workflow and the science is its example.
