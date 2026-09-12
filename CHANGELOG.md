# Change log

Dated findings, decisions and corrections. Appended, never rewritten. Structure will live in
README.md once the skeleton exists (WORKFLOW.md §9, step 7); the plan lives in WORKFLOW.md.

## 2026-09-11 — Fetch dropped as a rule; prompts get their own rule

Verified today that the six talk-version 224-pixel files on
`/project/dane2/wficai/textbook_priors/raw/` match the sizes and MD5s recorded in WORKFLOW.md §4
exactly (pathmnist 12G, dermamnist 1.1G, octmnist 3.7G, pneumoniamnist 205M, bloodmnist 1.5G,
organamnist 1.7G). On the strength of that, WORKFLOW.md no longer plans a `fetch` rule or stage:
the raw releases are prior work, exactly like the concept bank, reached through the `data/raw`
symlink and read directly by SAMPLE. The Zenodo record and MD5 table stay in §4 as provenance, not
as something a rule re-verifies. Stages renumber down by one (SAMPLE is now stage 1); the `fetch`
target is gone from the target list; TALK.md's two mentions of "a fetch rule" are reworded to
match.

SCORE (now stage 2) gains `render_prompts`, one rule per dataset (6 local jobs, no LLM calls) that
turns the concept bank and label map into both prompt strings and writes
`results/prompts/<dataset>.json`. Every `score_*` rule reads that file rather than re-deriving the
prompt inline, so the string sent to the model, the one hashed into its manifest, and the one a
demo or the report can print are the same artifact.

## 2026-09-09 — Talk branch: the plan cut to six datasets and four arms; the workflow to be rebuilt live

This branch is the version the talk shows. WORKFLOW.md is cut to six datasets (one per modality),
arms A, B, C and P, and 27,000 model calls; §10 lists what was removed and what each supported. A
full implementation of the twelve-dataset plan, including the from-scratch CNN ceiling and the
blocked ladder ANOVA, exists on branch `claude/textbook-priors-workflow-2kdgap`; its skeleton was
removed here so the workflow can be implemented from scratch, with the agent and the
`research-workflow` skill, as the talk's running example. The concept bank, its bibliography and
the plan are kept as the inputs they are.

Two things learned while building the full version carry over as facts, not code. The RCD service
answers only with thinking off (`chat_template_kwargs.enable_thinking: false`): with it on, the
primary model spends its whole token budget in `reasoning_content` and returns nothing, and
`qwen3.5-9b` files its answer under `reasoning_content` even with it off. With thinking off every
model answered in 0.1–0.4 s. And Zenodo serves ~105 KB/s per connection but scales with
connections, so the 224-pixel files are fetched as parallel byte ranges; the six the talk needs are
already on `/project/dane2/wficai/textbook_priors/raw`, MD5-checked against the medmnist package's
values, and need not be downloaded again.

## 2026-09-09 — H3 analysed over all four models rather than as two pairwise contrasts

H3 previously rested on one "clean within-family" contrast, gemma-4-12b against gemma-4-31b, with
the qwen pair demoted to corroboration because it also crosses a model generation and adds fp8.
That threw away half the ladder to protect one comparison, and left the scale claim resting on a
single pair of models over 11 datasets.

The ladder is a complete 4 x 11 repeated-measures design — every dataset is scored by every model
— and is now analysed as one. The four models are a 2 x 2 in disguise: qwen at 9B and 27B, gemma
at 12B and 31B, so family and size tier are crossed rather than confounded, and fitting both
together is what lets a size effect be read as size rather than as one family being better.
Dataset enters as a blocking factor, because AUCs are not commensurable across datasets and
blocking removes exactly that between-dataset level difference; pooling them raw would contradict
the reasoning that put a sign test everywhere else in this plan.

The directional claim is a planned 1-df linear contrast on log10 parameters, not the omnibus F,
which only says that some model differs. A Friedman test with a Nemenyi post-hoc is reported
alongside as a distribution-free check, since normality over 11 blocks is not something to assume.
The generation and quantisation confound in the qwen pair does not disappear under this analysis —
it is carried by the family main effect and the interaction, and is stated as a limit rather than
dissolved. Four models and 11 datasets is 3 degrees of freedom for model and 30 for error, so a
null here is weak evidence of no effect rather than evidence of none.

The H3 figure is now the model ladder: two panels sharing an x axis of the four models ordered by
parameter count, marker shape by family. The left panel shows AUC per dataset as measured, which
makes the incommensurability visible; the right shows the same values centred within dataset with
the across-dataset mean and its interval, and is the only panel from which a trend should be read.

## 2026-09-09 — Concept bank built; audit against the revised plan

The twelve concept-bank files were built, anchored and committed, then audited against the plan
by two reviewers that had not written them. Corrections, in order of how much they mattered.

**The sample sizes did not exist for two datasets, and the call budget was wrong.** The plan fixed
`test_n: 500` and `pool_n: 2000` flat across twelve datasets. breastmnist has 156 test and 546
train images; retinamnist has 400 and 1,080. Both are now capped by `min()` against the official
split, which is stated in §4 and §8; breastmnist's learning curve stops at n = 500 and
retinamnist's at n = 1000, so "seeds collapse at n = 2000" was false for both. **The corrected
total is 49,406 calls, not the 54,000 recorded in the entry below**, and `primary_upgrade` is
+21,626, not +18,000. The pool is drawn from the official train split only, which had not been
said anywhere.

**Arm A was degenerate on retinamnist and would have handed H2 a free vote.** The zero-shot prompt
is a pure function of the label map, and retinamnist's label map is the digit strings "0" to "4".
A distribution over "0, 1, 2, 3, 4" is not a diagnosis question, so arm B would have beaten it by
construction on one of the eleven datasets H2 counts — against a threshold of nine, with no slack.
Config now carries `zeroshot_names` for any dataset whose keys are not clinical terms, and the
zero-shot prompt states the modality so arm A is not handicapped by not knowing what it is looking
at. chestmnist leaves arm A as well as arm B, for the same reason it left arm B.

**n_B was defined on the metric that decides nothing, and had no uncertainty.** It read "reaches
the accuracy of arm B" while the primary metric is AUC. It is now the smallest grid n at which the
seed-mean AUC of arm P reaches AUC(B), with censoring codes and a 95% interval from the same
paired bootstrap — free, since the predictions are fixed. Without the interval the headline was a
threshold on a shallow curve: a 0.02 shift in arm B's line moves the crossing by a grid step.

**One of the two "clean within-family" size contrasts is not clean.** qwen3.5-9b to
qwen3.8-27b-fp8 crosses a model generation and adds fp8 quantisation — the same confound H3
refuses to accept across families. H3 now rests on the gemma pair; the qwen pair is corroboration.

**Three files in the bank had questions that could not be answered honestly.** pathmnist asked
about gland regularity and fibre alignment with no level for "there are no glands" or "there are
no fibres"; bloodmnist asked for chromatin density and nucleus-to-cytoplasm ratio of a platelet,
which has no nucleus. `any` in a fingerprint tells the estimator to ignore an answer, but the model
is still asked and must reply — so the archive would have carried invented levels or missing ones,
and the archive is a fixed input. Floors added, and the affected classes committed to them, which
moved eleven fingerprint cells off `any` and gained signal rather than merely avoiding a failure.

**One scale was nominal while the estimators read it as a number.** dermamnist's `pigment_network`
ran [absent, regular, irregular], and §3 maps scales to equally spaced values — placing "regular
network" exactly halfway between "no network" and "atypical network", which is not what dermoscopy
means. Split into two binary concepts, presence and atypia. `asymmetry` and `border_irregularity`
were merged to hold the twelve-concept cap; they were byte-identical across all seven classes, so
the merge cost no separation and the split raised total pairwise separation from 57 to 58.

Also corrected: arm E is evaluated twice, because the published MedMNIST numbers are computed on
the full test split and cannot be reconciled against a 500-image sample; arm B reads AUC from its
raw score rather than a softmax with an unstated temperature; the sign test's twelve datasets are
at most ten independent units, since organa/c/smnist are the same LiTS volumes in three planes;
and contamination is now stated as something no arm here can rule out, since every source dataset
is public and labelled.

## 2026-09-09 — Validation pass over the plan; scope cut to three hypotheses

No computation yet: this entry records a read-through of the designed workflow before any rule
exists. The plan was internally inconsistent in two places and would have bought a large grid for
questions it had not stated. Findings, in order of how much they mattered.

**The headline comparison was unfair, and would have been true by construction.** The pixel
baseline was a ResNet-18 trained from scratch, compared at 50 labelled images against a
vision-language model with billions of parameters of pretraining. Every rule could have been
correct and the claim still worthless. The label-matched baseline is now arm P, a linear probe on
ImageNet ResNet-18 features: transfer learning without the textbook, sharing the classifier, the
regularisation search and the nested subsets with arm C, so features are the only difference. The
from-scratch network survives as arm E, the fully supervised ceiling and the number reconciled
against the published MedMNIST table.

**The learning curve measured the wrong thing.** It was written as arm E against arm F (a
supervised network with the prior fused in), which asks whether a prior *helps* a supervised
model. The project's question is whether a prior *substitutes* for labels, which is C against P
with arm B's zero-label AUC as the line to cross. The headline number is now n_B: the labels
a pixel model needs to match the textbook.

**Arm B had no estimator.** "Concept scores matched to the bank's class fingerprints" was the
project's only label-free predictor and nowhere defined. It is now specified (scale levels mapped
to equally spaced values, `any` masked, negative mean absolute difference, softmax for AUC), and
it is not defined for chestmnist's fourteen co-occurring findings, so chestmnist leaves arm B and
stays in A, C, P and E.

**No primary metric and no decision rules.** Added: test AUC from the `medmnist` evaluator, ACC
reported but deciding nothing, a shared seeded 500-image test sample so all comparisons are
paired, per-dataset paired bootstrap, and a one-sided sign test across datasets with the counts
written down (10 of 12, or 9 of 11 where arm B is involved) rather than pooling incommensurable
AUCs.

**H3 confounded size with model family.** A single curve over 9b, 12b, 27b and 31b crosses two
families. It is now read as two within-family contrasts, qwen 9b→27b and gemma 12b→31b.

**"n labelled images" was not accounted for.** With 100 fixed epochs and no stated model
selection, a curve point could have quietly used the official validation split on top of its n
labels. Arms C and P now choose their L2 strength by cross-validation inside the n labels and use
no validation set; arm E, which does use the official splits, selects on validation AUC and is
never a curve point.

**A cap on the cached 224 arrays would have broken the reconciliation.** `cache_cap_224: 60000`
was set without a reason; the large training splits exceed it, so arm E would have trained on less
data than the published numbers used. Removed: cache the full split at both sizes.

**A and B would have shared one prompt, which makes H2 circular.** The original scoring unit
returned the concept scores and the zero-shot class distribution from the same call, so the
concept answers could have been rationalisations of a class the model had already committed to,
and the zero-shot guess could have been informed by the feature checklist. They are now separate
calls on separate prompts: the concept prompt never names a class, the zero-shot prompt never
mentions a concept.

**Cost.** 120,000 image calls at the original grid. Arm B needs no labels, so the three
non-primary models only ever need the test sample; that one observation brings the budget to
54,000 calls — 48,000 concept calls plus 6,000 zero-shot calls on the primary model — with all
twelve datasets and all four models intact. A documented six-dataset contingency covers the case
where the allocation is tighter than that.

**Scope removed** (each with the claim it supported, in WORKFLOW.md §10): arm D and the whole
embedding stage, arm F and its open fusion design, the 64- and 128-pixel sweep and the GPU-minutes
figure, the reasoning sweep, and all three opt-in diagnostics. The permutation controls that
replace the prompt ablation are re-analyses of the response archive and cost no calls. Four
figures became three, six arms became five, nine stages stayed nine, and the plan lost the talk
narrative to TALK.md so that what remains is the experiment.

**Still needing a person:** confirmation of the 54,000-call volume with the service owners, and
the acceptable-use statement for de-identified public medical images.

## 2026-09-11 — The prompts are an artifact; one class name survives in a concept prompt

`render_prompts` is built and run for all six datasets (stage 2, 6 local jobs). Both prompt
strings, their hashes, the concept scales a response is validated against, and the class names in
label-index order now live in one file per dataset, `results/prompts/<dataset>.json`, which every
score job will read instead of formatting a prompt where it sends it.

**H2's non-circularity is now a checkable property of the strings, and it holds on five of six
datasets.** The concept prompt contains no class name on pathmnist, dermamnist, pneumoniamnist,
bloodmnist and organamnist, and the zero-shot prompt mentions no concept id or question on any
dataset. The exception is octmnist, where the `retinal_thickness` scale has a level named `normal`
and `normal` is also one of the four classes; the word reaches the concept prompt twice, as a level
name and in the JSON template. Three further apparent hits are substring coincidences and not
occurrences of a class name: pathmnist's concept `necrotic_debris` against the class `debris`,
bloodmnist's `cytoplasm_basophilia` against `basophil`, and octmnist's level `normal_depression`.
A whole-word check separates the two kinds.

Two ways to close the octmnist case, both deliberate: rename that scale level in the bank (and the
fingerprint cells that reference it), which makes "the concept prompt names no class" exact and
needs no exemption in the smoke test; or record the exemption, on the argument that `normal` there
describes a thickness and not a diagnosis. Unresolved as of this entry.

**Class order comes from the release, not the bank.** bloodmnist's bank lists its classes in
reading order, which is not the label-index order the AUC columns and the zero-shot distribution
use. Every artifact that is indexed by class takes its order from `config/medmnist.yaml`.

## 2026-09-11 — octmnist's colliding level names renamed; the concept prompt now names no class

Resolved the open question of the previous entry, in favour of changing the bank. `octmnist`'s
`retinal_thickness: normal` is now `not_increased`, and `foveal_contour: normal_depression` is now
`depressed`, so the word `normal` no longer appears in any of that file's scales and the property
needs no exemption anywhere. Scale order, questions, anchor text and sources are unchanged; the
four fingerprint cells that named those levels were renamed with them, so no class's expected
level changed, and the estimators index a scale by position, so no number would move even once
there are numbers. The correction is recorded in the file's own header and in
`data/concepts/README.md`.

**The concept prompt now names no class on any of the six datasets, and the zero-shot prompt
mentions no concept on any of them.** The check is a whole-word match of each class name against
the rendered strings, which treats an identifier such as `necrotic_debris` as one word; on that
reading `pathmnist`'s `necrotic_debris` (class `debris`), `bloodmnist`'s `cytoplasm_basophilia`
(class `basophil`) and `organamnist`'s left/right levels (classes `lung-left`, `lung-right`) are
shared words rather than leaks, and were left alone.

Snakemake rebuilt exactly one prompt file from the bank edit, which is the input trigger doing its
job: the other five were left untouched because their inputs did not change.

## 2026-09-11 — The smoke tier: 173 tests, and what the AUC convention actually is

Stage 0 is built and passes in under a second: 110 tests over the bank, 20 over the pinned
release, 40 over the prompts, 3 over the metric.

**The bank passes every rule `CONCEPT_BANK.md` states as machine-checkable, on all twelve files** —
class names and task strings against the installed `medmnist`, concept ids and two-to-five-level
scales, one sourced anchor per level with no anchor restating its own token or repeating another,
every fingerprint naming every concept with a level or `any`, every source key resolving to a
citation with a DOI or URL, and `reviewed_by` recording that the review was simulated. The two
structural rules its prose requires hold too: the three `organ*mnist` files share a byte-identical
`concepts` block, and every `retinamnist` concept is monotone across grades 0 to 4 (not only the
lesion concepts — the stronger property is what the file actually satisfies).

**Three properties of `medmnist.evaluator.getAUC` are now pinned, because the arms depend on
them.** It is the *unweighted* mean of one-vs-rest AUCs, equal to sklearn's macro-ovr and
deliberately not its weighted variant, so a dataset's class balance cannot reweight a comparison
between arms. It ranks each class column independently, so any strictly increasing per-column
transform leaves it unchanged — which is what makes arm B legitimate: its class score is a negative
mean absolute distance from a fingerprint, and WORKFLOW.md §3's "AUC reads that score directly, no
softmax" is exactly this invariance. sklearn's own macro-ovr *raises* on those scores, so the
choice of evaluator is load-bearing rather than conventional. And for `binary-class` the package
takes the **last** column of a two-column score matrix as the positive class; feeding column 0
would report 1 − AUC, a plausible-looking number that is exactly backwards.

**Two tests were written too strictly and told us something about the bank.** A question need not
*end* with its question mark: the three organ files append the radiological left-right convention
as a second sentence, which is a clarification a reader needs and not a defect. And the zero-shot
prompt cannot be checked against bare level tokens, because levels are ordinary words —
dermamnist's `colour_count` runs `one`, `two`, … and "exactly one of these 7 categories" is not a
mention of a concept. The check is concept ids, questions and anchor texts.

**The smoke marker is a gate, not a data dependency, and `ancient()` cannot express that.** Every
rule takes `results/smoke_ok.txt` as an input so nothing is computed on code that fails its tests.
Wrapping it in `ancient()` — the documented way to say "must exist, but its timestamp means
nothing" — suppressed rerun detection for the entire job: with it in place, a genuinely changed
bank file stopped re-rendering its own prompt, which is the one edge that must never be lost. It
was removed. The bank files are therefore deliberately *not* inputs of `smoke`, so that a marker
every rule depends on cannot let one dataset's bank edit invalidate every other dataset's response
archive; the cost is that the schema tests re-run on demand (`-F smoke`) rather than by themselves
after a bank edit. Verified on the current DAG: a bank edit reruns one job, a test or code edit
reruns the tests and the six prompts.

## 2026-09-11 — Stage 1 run: the samples exist, and dermamnist's rarest class is five images

All six `sample_dataset` jobs ran on `work1`. Each dataset now has its 500-image test sample and
its 2000-image labelled pool, drawn with seed 0 from the official splits, with the drawn indices
and labels in `results/sample/<dataset>.json` and the images in `data/cache/sample/<dataset>.npz`
(1.5 GB in total).

**Streaming works and is cheap.** The 224-pixel release members are deflated, so there is no
random access; the reader inflates the image member as a stream and copies out only the wanted
rows. pathmnist — 13.5 GB of pixels behind a 12.6 GB file — took 2 min 6 s and peaked at 392 MB of
resident memory, which is the 376 MB sample array itself. `np.load` would have needed 13.5 GB to
keep 376 MB of it. Measured requests are now in config: 1 core (mean load 0.27 to 0.79 of a core),
1500 MB, 20 minutes.

**The cached rows are the rows they claim to be.** Checked end to end on the real releases, not
only on the fixture the smoke tier uses: for pneumoniamnist (both splits) and dermamnist (test),
the whole image member was loaded the ordinary way and compared against the cache at the recorded
indices — every image, every label, and the labels in the JSON, all identical. A one-off check,
not a rule: verifying every sampled row this way costs a second full read of each release.

**Every sample tracks its split's class balance to within 2.8 percentage points**, the widest
being bloodmnist basophils (2.8) and organamnist kidney-right (2.7) in the test samples; the pools
are all within 1.4. No sample lost a class.

**But an unstratified 500-image test sample leaves very few images in a rare class, and that bounds
what the intervals can say.** dermamnist's test sample holds 5 vascular lesions and 6
dermatofibromas out of 500; bloodmnist's holds 25 basophils, organamnist's 21 femur-left. The AUC
convention is the *unweighted* mean of one-vs-rest columns (pinned in the smoke tier), so
dermamnist's macro AUC gives a column built on five positives the same weight as one built on 337,
and the paired bootstrap over test images will show it as a wide interval on every arm at once.
This is a consequence of WORKFLOW.md §4 fixing the sample at 500 with one seed, not a defect: the
same 500 images are what makes every comparison paired. Three ways out, in order of cost: report
it as a limit and read the per-dataset differences rather than the absolute AUCs; stratify the test
sample by class (changes every arm's definition, and the sample then no longer mirrors the split);
or raise the sample above 500 (the test splits allow 624 at the smallest, so pneumoniamnist caps
the shared size at 624). Left open for the owner; the numbers above are in every sample's JSON.

## 2026-09-11 — The probe: the boundary works, and a call costs ten times what the plan assumed

`rule probe` ran on a compute node against `qwen3.8-27b-fp8`, ten images of pneumoniamnist plus one
deliberately truncated call: 21 calls, 58 seconds, `results/probe/pneumoniamnist__qwen3.8-27b-fp8.json`.

**Everything the probe exists to check, checked.** A compute node reaches the service. The served
model name is `Qwen/Qwen3.8-27B-FP8`, which is *not* the alias we ask for (`qwen3.8-27b-fp8`) —
recording it was the right call, and a run that recorded only the requested name would not be able
to say which weights answered. Ten of ten concept replies parsed complete against the scales; ten
of ten zero-shot replies parsed and all ten summed to one. Thinking off behaved: every reply came
back in `content`, none in `reasoning_content`.

**The malformed path fires, and it is not simulated.** The extra call went out with a token budget
of one; the reply was "```", the content retry doubled the budget to two, the reply was "```json",
and the answer was recorded missing with both raw texts kept. `complete: false` there is the probe
passing.

**A call costs 3.6 s, not 0.1 to 0.4 s.** Median 3.6 s over the 20 scored calls, range 1.2 to 5.2 s.
The earlier figure in WORKFLOW.md §4 was measured on 2026-09-09 without an image attached; the call
this workflow actually makes carries a 224-pixel PNG and a prompt of about 1,300 tokens. A chunk of
100 images is therefore about six minutes rather than twenty seconds, which is a `runtime` request,
not a budget problem: with each model's jobs running to its own concurrency cap the primary's
18,000 calls are about 25 minutes and the ladder models are shorter. §4 now carries both
measurements with their dates. Per-call latency is recorded per attempt from here on, so the
scoring rules' requests come from the archive rather than from arithmetic on a job's wall time.

**What the answers look like, on ten images only and worth nothing statistically.** The concept
answers vary across images and move with the label — the four images the model called
`parenchymal_opacity: absent` include two of the three normals — and the zero-shot probabilities
separate the classes on eight of ten. Two concepts came back constant across all ten images
(`air_bronchogram`, and `peribronchial_thickening` on nine of ten). That is a thing to watch when
the real cells land: a concept that never varies contributes nothing to arm C and nothing to arm B
beyond a constant offset.

**Operational note from a workspace that vanished mid-session.** This agent session's checkout is
ephemeral: everything gitignored was wiped and recreated while stage 2 was being written. The
sampled arrays survived untouched, because they live under `storage_root` and only the symlink was
lost — which is the reason they are there. `results/` did not survive, and regenerating it cost
seconds. That is fine for JSON a rule can rebuild, and it is not fine for `results/score/`, which
the plan treats as fixed from the moment it is written. Before the 27,000-call fan-out is launched,
the archive has to sit on the project filesystem — either by running from a persistent checkout or
by giving `results/` (or `results/score/`) the same symlink treatment as `data/cache`.

## 2026-09-11 — The thin-class question, settled: the sample stays random

Resolved the question left open by the stage-1 entry, in favour of leaving the sample alone and
documenting the limit (WORKFLOW.md §3 now carries it).

What decided it was that the obvious fix is two different things and neither is what it looks like.
*Proportional* stratification — matching the split's class shares — reproduces almost exactly what
the random seed already drew (dermamnist's rarest class: 6 images either way; organamnist's: 21
against 22; pathmnist's: 24 against 24), because the thin columns are thin from real rarity, not
from sampling noise. *Equal-as-possible* stratification does help, but is capped by the splits
themselves: dermatofibroma would go from 6 to 23 and stop there, because the dermamnist test split
holds only about 23 of them; organamnist femur-left 21 to 46; pathmnist debris 24 to 56. A two-to
four-fold gain on the worst columns, roughly halving their standard error — real, but not a fix.

Against that: equal allocation makes each one-vs-rest column's negatives a near-uniform mixture of
the other classes instead of the dataset's own, so per-class AUC would be measured against a
different "rest" and the absolute numbers would stop meaning what a MedMNIST AUC means. And the
gain lands where it is least needed: all three hypotheses are paired differences between arms on
the same images, where a thin column is common mode and largely cancels.

So: the 500-image test sample stays as WORKFLOW.md §4 fixes it, random with seed 0, shared by every
arm. The per-dataset paired differences with their intervals stay what a reader should look at, and
the absolute AUCs carry the stated caveat. Nothing had been spent against the current sample when
this was decided — the calls start with the scoring fan-out.

## 2026-09-11 — A rule that printed one command and ran another; caught by one chunk, not by 270

The scoring fan-out's four rules were generated in a `for` loop over the model list, each with its
own `output:` path and its own `llm_<model>` resource. The first real chunk — one job, a hundred
calls, run deliberately before the other 269 — came back with `qwen3.8-27b-fp8` in its file name
and **`gemma-4-31b` in its argv, and `nvidia/Gemma-4-31B-IT-NVFP4` as the served model**. Snakemake
had printed the command it did not run: the generated rules each kept their own output path, but
all four shared the *last* iteration's `shell:` string.

Had the whole fan-out gone out, every model's archive would have been written by gemma-4-31b. H3 —
*the prior gets better with a bigger model* — would have compared four copies of one model and
found no effect, with a perfectly consistent archive underneath it. The only trace was
`served_model` disagreeing with the file name, and nothing downstream reads that.

Three changes, because one would not have been enough:

1. **The four rules are written out explicitly.** The repetition is the point: the model a rule
   uses is visible in the rule the reader is looking at, and the failure needed a rule whose
   command came from somewhere else.
2. **The model travels as a wildcard**, so all four rules share one command string that names
   `{wildcards.model}` and cannot disagree with the file it writes.
3. **The stage refuses a mismatch.** `check_output_name` compares the cell it was told to compute
   against the cell named in its output path and raises before the first call. A test holds it to
   each of the five fields.

The wasted chunk was a hundred calls and its file was deleted. The check that caught it was the
decision to run one chunk before 270; that is now the standing practice for any stage that spends
calls. Two earlier notes are worth rereading in this light: Snakemake's parser also silently
rejected a multi-line `shell:` inside a generated rule (a syntax error reported against an
unrelated line thirty lines earlier), and this bug produced no error at all. Rules generated by a
loop are not worth what they cost here.

## 2026-09-11 — qwen3.5-9b answered in a field we did not read, and the archive could not save us

The first fan-out went out and was stopped at 35%. Two failures, one of which is a lesson about
what "archive the raw reply" has to mean.

**qwen3.5-9b returned nothing readable on all 3,000 calls**: every chunk 0% complete, every image
retried, `finish_reason: stop`, 130 completion tokens, and an empty string where the answer should
be. One diagnostic call settled it — the model files its answer under `message.reasoning`, a third
field beside `content` and `reasoning_content`, and with thinking off that field holds finished
JSON rather than any chain of thought:

    {"content": null, "reasoning": "```json\\n{\\n  \\"nucleus_present\\": \\"present\\", ...

So 3,000 good answers were recorded as missing by a reader that knew two field names. `read_reply`
now tries `content`, `reasoning_content`, `reasoning` in order and records which one answered.

**And the archive could not repair it, which is the real finding.** WORKFLOW.md §7 says every raw
response is archived; what was archived was the *text this code extracted* from the response, which
is not the same thing. Extraction is a guess about another system's API, and when the guess was
wrong the only way back was to buy the calls again. The archive now holds the whole message object
beside the extracted text, so the next wrong guess costs a re-parse rather than 3,000 calls.

**The primary model's jobs timed out, 29 of them.** A 30-minute request came from the probe's
median of 3.6 s per call — measured at concurrency one. Latency is not the service's property
alone: across this run, gemma-4-12b under a cap of 24 held 3.4 s and finished a chunk in 6 minutes;
gemma-4-31b under a cap of 12 took 5.0 s and 8 to 11 minutes; the primary under a cap of 48 ran
past 30 minutes for the same hundred images. Since a timed-out chunk throws away every call it
made, `runtime` is now 120 minutes — four times the worst chunk observed, rather than twice the
best. The caps stay where the plan put them, below what the service publishes.

**What survived.** gemma-4-12b's 30 chunks (99.4% complete) and gemma-4-31b's 30 (100%) are good
and are kept; so is the primary model's one validated chunk. qwen3.5-9b's 30 chunks are a faithful
record of a reader bug and will be re-scored. Cost of the two failures: 3,000 calls for qwen3.5-9b
and roughly 2,000 spent inside jobs that timed out — about 19% of the budget, all of it bought
back by two code changes and a resource line.

## 2026-09-12 — Stages 3 to 6 built: the pixel baseline, the arms, the metric and the report

Written while the scoring fan-out ran, so that the analysis was waiting for the archive rather than
the other way round. What is worth recording is the decisions, not the code.

**Arm P does not resize.** The ImageNet weights carry their own transform, which resizes to 256 and
centre-crops back to 224. Applied here it would throw away the frame edge, and an organ crop is
*defined* by its frame: MedMNIST's organ images are bounding boxes, so the edge is the signal.
The release is already 224, the size the encoder wants, so only the channel normalisation is
applied and the images reach the encoder as they reach the model. Greyscale is repeated across
three channels rather than summing the first-layer filters, which would change the features to save
nothing.

**The estimators are where the study's judgement lives, so each is stated as a decision.** Equal
spacing of a concept's levels weights concepts by scale length — an adjacent miss costs 1.0 on a
two-level scale and 0.25 on a five-level one — which is a consequence of the mapping and the reason
no per-concept coefficient may be read as an importance. A missing answer is imputed with the
labelled pool's median and flagged with an indicator column, so "the model would not say" enters the
regression as information rather than as a value. Arm B scores over the concepts that both the
fingerprint and the image commit to, and a class with no overlap at all takes the floor rather than
a NaN, because an undefined AUC is worse than an uninformative one.

**The metric is the package's, reached by a rank formula.** A 10,000-replicate paired bootstrap over
fifty arms cannot call `getAUC` ten thousand times, so the AUC is computed from average ranks, and
the smoke tier holds the two to equality on both task types — including the coarse, heavily tied
scores arm B produces, which is exactly where a rank formula without tie handling would drift.

**A class with no positives in a replicate is undefined, not 0.5.** With dermamnist's five vascular
lesions this happens in a large share of replicates, and calling it a coin flip would drag that
dataset's macro AUC toward chance in a way that looks like a result.

**An end-to-end test of the analysis chain caught the expensive bug.** The estimators and the metric
had tests; the glue did not. A miniature archive with a known answer now runs the whole chain, and
on its first run it found that a bootstrap distribution of n_B mixing `<=50` with `>2000` produces a
NaN quantile — the evaluate stage would have died on it after the entire night of calls. Quantiles
of n_B are now taken on the ordinal ranks, since there is no crossing half way between 200 and 500
labelled images.

## 2026-09-12 — The primary model is contention-bound, and a wave that wrote nothing

The 48-job wave submitted at 23:06 ran its full two hours and produced **no chunks at all**. Every
job was killed at its time limit mid-chunk, and a chunk that times out writes nothing: the hundred
calls it made are spent and unrecorded. That is the single most expensive shape of failure in this
workflow, and it is worth stating plainly because the fix is not obvious from the inside.

**What the measurements say.** A call to `qwen3.8-27b-fp8` costs 4.5 s with nothing else running
and 89 s while 48 of our own jobs are in flight — measured, not inferred. The ladder models do not
behave this way: qwen3.5-9b held 2.8 s per call under a cap of 96, gemma-4-12b 3.4 s under 24,
gemma-4-31b 5.0 s under 12. So this is the 27B model's capacity (and whatever else is using it),
not concurrency as a general phenomenon. Aggregate throughput on it rose only about 2.5-fold going
from one stream to 48, which is a nearly saturated endpoint.

**Three consequences, all recorded in config where the numbers live.** The runtime request is now
240 minutes, four times the worst chunk observed rather than twice the best. The remaining work is
ordered by dataset, three at a time, because the analysis chain needs every chunk of a dataset
before it can say anything about it — so a cutoff at any hour leaves whole datasets analysable
instead of six half-finished ones. And the existing archive was marked current rather than
re-bought when the reader fix changed the code behind it, which is what `--touch` is for.

**What a timed-out chunk should have left behind.** Nothing in the archive says how far a killed
job got, because the stage writes its JSON at the end. A progress line every ten calls would have
turned two hours of silence into a measurement, and would have let this be diagnosed in twenty
minutes rather than at the deadline. Not changed now: `priors/score.py` is an input to every
protected chunk already written, and re-scoring 91 chunks to add a log line would cost more than
the line is worth tonight. It belongs in the next re-score.

## 2026-09-12 — First real results, on three of six datasets: all three hypotheses fail so far

pathmnist, dermamnist and octmnist completed their archive overnight and the whole analysis ran
over them. These are three of six, so the sign tests are weak by construction (3 of 3 would be
p = 0.125), but the per-dataset numbers are what the plan says to read, and they are consistent.

**H1 — not supported (1 of 3).** n_B is `<=50` on pathmnist and on dermamnist: the ImageNet pixel
probe with fifty labelled images is already better than the zero-label textbook arm. Only octmnist
put the crossing inside the curve, at 500 labels [100, 1000]. Arm C beat arm P at n = 50 on
octmnist alone. The concept scores are not worthless — they are simply worth less than fifty
labelled images and an ImageNet encoder, on two of these three datasets.

**H2 — not supported (0 of 3), and this is the interesting one.** Asking the model for the
diagnosis beat asking it for the textbook's features every time: pathmnist 0.927 against 0.924
(a tie inside its interval, B − A = −0.003 [−0.019, +0.014]), dermamnist 0.770 against 0.671
(−0.099 [−0.168, −0.029]), octmnist 0.941 against 0.894 (−0.046 [−0.064, −0.028]).

But the permutation controls say the bank is doing real work: permuting the fingerprints across
classes costs arm B 0.43 AUC on pathmnist, 0.52 on octmnist and 0.21 on dermamnist, and permuting
the concept columns costs arm C on every dataset. So the concept scores carry genuine class
information — the model's direct answer simply carries more. That is a finding about the *bank as
an estimator*, not about whether the model can read the features: arm B compresses twelve concept
answers into one nearest-fingerprint distance, and that compression is lossy in a way the zero-shot
distribution is not.

**H3 — not supported (2 of 3 in each family).** Within qwen, the 27B model beat the 9B on
pathmnist and dermamnist and lost on octmnist; within gemma, the 31B beat the 12B on dermamnist and
octmnist and lost on pathmnist. Friedman over all four models gives p = 0.61. No scale effect is
visible at this size, and the plan's own threshold (5 of 6) could not have been met by three
datasets in any case.

**The archive is clean.** Completeness is 99.8% to 100% on every dataset-model cell; no cell comes
near the 5% incompleteness cap, and the retry path fired on well under 1% of images.

## 2026-09-12 — The full run: all six datasets, all three hypotheses unsupported

The archive completed at 07:02 and the analysis at 07:25. 270 chunks, 27,000 calls, no cell over
the 5% incompleteness cap. The three-dataset reading of a few hours earlier holds on all six, and
in two places it gets sharper.

**H1 — not supported. n_B is `<=50` on five of six datasets.** Fifty labelled images and a frozen
ImageNet ResNet-18 already beat the zero-label textbook arm everywhere except octmnist, where the
crossing sits at 500 [100, 1000]. Arm C beat arm P at n = 50 on octmnist alone (1 of 6, p = 0.98
against the hypothesis). The honest headline: **the textbook prior is worth fewer than fifty
labelled images** on this benchmark suite.

**H2 — not supported, 0 of 6, and the shape of the failure is the finding.** Asking the model for
the diagnosis beat asking it for the textbook's features on every dataset. The gap is smallest
where the classes are visually distinctive (pathmnist −0.003, inside its interval) and largest
where the task is a single binary call (pneumoniamnist −0.191 [−0.221, −0.159]).

And yet both permutation controls bite everywhere: permuting the fingerprints across classes costs
arm B between 0.21 and 0.52 AUC, and permuting the concept columns costs arm C on all six. So the
bank is not noise — the concept answers carry substantial class information. What fails is the
*estimator*: arm B compresses eight to twelve concept answers into one nearest-fingerprint
distance, and that compression throws away more than the zero-shot distribution does. Arm C, which
learns weights over the same concept answers, reaches 0.93 on bloodmnist and 0.97 on pathmnist —
the information is there; the fingerprint is the wrong way to read it out.

**H3 — not supported.** The larger qwen won on 4 of 6, the larger gemma on 3 of 6, and Friedman
over all four models gives p = 0.85. No scale effect is visible in arm B at these sizes. Note that
arm B is the arm with the weakest estimator, so this tests scale through a lossy channel; the same
comparison on arm C would need the ladder models to score the pool, which the plan deliberately
does not buy.

**What the study cannot say**, unchanged and worth repeating beside these numbers: every source
dataset is public, so "the model carries textbook knowledge" and "the model has seen this
benchmark" are not distinguishable here. The bank's expert review is simulated. And the test
sample's rare classes are thin, which widens every absolute AUC — though not the paired
differences the hypotheses are decided on.

## 2026-09-12 — Arm D added, post-hoc: the bank in the prompt, integrated by the model

H2's failure has a specific shape (entry above): arm B loses to arm A on all six datasets, while
both permutation controls bite on all six. Read together those say the bank carries real class
information and that the nearest-fingerprint rule is a lossy way to read it out — a statement about
the *estimator*, not about the bank. Arm C is one way to check that, but it needs labels. Arm D is
the zero-label way: hand the model the whole bank — every concept with its anchors, and every
class's textbook fingerprint — and then ask it arm A's question. The integration happens inside the
model instead of in a distance in concept space.

**It is post-hoc and it is labelled post-hoc everywhere.** It was designed after seeing H2 fail, so
`D − A` and `D − B` are descriptive statistics, not tests: no `supported` verdict reads them, the
report has its own section saying so, and `evaluate_across` files arm D under `extensions` rather
than beside H1–H3. The sign tests reported for it are a compact way of saying how many datasets
moved the same way, nothing more.

**What it costs and where it lives.** One more prompt per dataset (`directed`), scored by the
primary model on the 500-image test split alone: 30 chunks, 3,000 calls, taking the budget from
27,000 to 30,000 and the clean-clone DAG from 312 jobs to 342. It sits *inside* `rule all` rather
than in an extension rule of its own, which is the one place it departs from how WORKFLOW.md §10
treats extensions: every arm has to be in the same paired bootstrap to be compared to the others,
and an arm scored outside it could only be set beside the results, never differenced against them.

Two invariants worth stating because they are the inverse of each other. The concept prompt names
no class and the zero-shot prompt mentions no concept — that separation is what makes H2 a fair
question, and the smoke tier checks it on the rendered strings. The directed prompt must name
every class *and* every concept, and the smoke tier checks that too, because a directed prompt that
had quietly dropped a fingerprint would be a weaker arm D reported as the real one. An `any` in a
fingerprint is rendered as what it means in the bank ("the sources do not commit on: ...") rather
than dropped: a class the literature is silent about on some feature is itself information.

One latent bug found on the way: `sums_to_one`, the diagnostic recording whether the model obeyed
"make the probabilities sum to 1", was gated on `kind == "zero_shot"` and would have been silently
absent from every arm D answer. It is now gated on the answer's shape (`kind != "concept"`), which
is what it was always a property of.

## 2026-09-12 — Arm D's result: the readout was lossy, but the bank is not news to the model

3,000 calls, 30 chunks, 500 of 500 images complete on every dataset and not one content retry —
the cleanest cell in the archive. Arm D splits the H2 post-mortem in half, and confirms only one
side of it.

| dataset | AUC(D) | AUC(A) | AUC(B) | D − A | D − B |
|---|---|---|---|---|---|
| pathmnist | 0.890 | 0.927 | 0.924 | −0.038 [−0.058, −0.017] | −0.035 [−0.053, −0.017] |
| dermamnist | 0.790 | 0.770 | 0.671 | +0.018 [−0.040, +0.088] | +0.117 [+0.061, +0.181] |
| octmnist | 0.886 | 0.941 | 0.894 | −0.055 [−0.074, −0.036] | −0.008 [−0.031, +0.014] |
| pneumoniamnist | 0.906 | 0.918 | 0.727 | −0.012 [−0.032, +0.009] | +0.179 [+0.148, +0.210] |
| bloodmnist | 0.827 | 0.883 | 0.775 | −0.056 [−0.081, −0.031] | +0.052 [+0.026, +0.078] |
| organamnist | 0.766 | 0.710 | 0.685 | +0.056 [+0.031, +0.081] | +0.082 [+0.046, +0.119] |

**The nearest-fingerprint readout really was lossy: D beats B on 4 of 6.** Where arm B fell
furthest behind, arm D recovers most of the gap — pneumoniamnist 0.727 to 0.906, against arm A's
0.918, so essentially all of the deficit was the estimator rather than the bank. dermamnist
+0.117 and bloodmnist +0.052 say the same thing more mildly. That was the reading the permutation
controls pointed at, and it survives.

**But the bank is not information the model lacked: D loses to A on 4 of 6.** Being handed the
concepts, the anchors and every class's fingerprint made the model *worse* at naming the class than
being asked cold — clearly so on pathmnist, octmnist and bloodmnist, whose intervals exclude zero.
Given the image, the model's own diagnosis beats being told what to look for. The bank constrains
rather than informs.

Both readings together: arm B measured the bank through a bad estimator *and* the bank was never
going to add much on top of what the model already does with the image. H2's premise — that
directing the model at cited features beats asking it for the diagnosis — fails at both levels, and
arm D is what separates them. One dataset dissents: organamnist beats both A (+0.056) and B (+0.082)
with intervals excluding zero, which is the one place the textbook demonstrably helped.

None of this is a test. Arm D was designed after H2 failed; the counts above are descriptive, the
sign-test p values (0.89 against A, 0.34 against B) are reported only as a compact way of saying how
many datasets moved together, and no `supported` verdict reads them. H1, H2 and H3 remain
unsupported on exactly the evidence recorded in the entries above.

## 2026-09-12 — The service serialises us: concurrency buys no throughput

Measured while arm D's 24-job wave ran, because the wave was far slower than predicted and the
cause mattered more than the delay. One call through the same code path from the login node took
**42.8 s**, against **1.49 s** for the identical call when a single chunk ran alone that morning.
It succeeded on the first transport attempt — no 429, no backoff — so nothing was failing; the
requests were queued at the service.

| concurrent jobs | s/call | aggregate calls/s |
|---|---|---|
| 1 | 1.5 | 0.67 |
| 24 | 42.8 | 0.56 |

Latency scales almost exactly linearly with our own concurrency, which means aggregate throughput
is flat — 24-way concurrency delivered slightly *less* total throughput than one job would. The
same shape appeared last night on the concept prompt (4.5 s at one job, 89 s at 48), so this is a
property of the service and not of a prompt. The practical consequence is that the `llm_<model>`
caps do not buy wall-clock: killing a wave and resubmitting at a lower cap would finish at the same
time, which is why arm D's wave was left alone. The caps still earn their place as a politeness
limit on a shared service, not as a throughput knob.

Two cautions on reading this. The service is shared, so some of the 1.5 s to 42.8 s change may be
other users' load rather than ours, and this is two points rather than a curve. And a diagnostic
that cost one call and five minutes replaced an estimate that had already been wrong twice: the job
CPU counters could not settle it, because at 43 s per call four minutes of work rounds to under one
second of CPU and looks identical to a hang.

## 2026-09-12 — The published ceiling, read against every arm: 2,000 labels is the benchmark

The literature extension is finished: `data/literature/benchmarks.yaml` now reads into a table that
sets every arm of this study against the best of the five fully supervised methods Yang et al.
(2023) report for the same six tasks at the same 224 pixels, and the report's prose states its
numbers from macros rather than leaving the comparison qualitative.

| dataset | A | B | D | C (n=2000) | P (n=2000) | published | method |
|---|---|---|---|---|---|---|---|
| pathmnist | 0.927 | 0.924 | 0.890 | 0.965 | 0.986 | 0.989 | ResNet-18 (224) |
| dermamnist | 0.770 | 0.671 | 0.790 | 0.799 | 0.921 | 0.920 | ResNet-18 (224) |
| octmnist | 0.941 | 0.894 | 0.886 | 0.933 | 0.947 | 0.963 | Google AutoML Vision |
| pneumoniamnist | 0.918 | 0.727 | 0.906 | 0.728 | 0.971 | 0.991 | Google AutoML Vision |
| bloodmnist | 0.883 | 0.775 | 0.827 | 0.930 | 0.990 | 0.998 | ResNet-18 (224) |
| organamnist | 0.710 | 0.685 | 0.766 | 0.887 | 0.991 | 0.998 | ResNet-18 (224) |

**The pixel probe at 2,000 labels is the published benchmark, to within a rounding error.** Its
median gap to the ceiling is 0.007; it is within two points on all six datasets, and on dermamnist
it is at or above it (0.921 against 0.920). The published numbers are trained on each dataset's
entire official training split — thousands to tens of thousands of images — so 2,000 labels and a
frozen ImageNet ResNet-18 recover essentially all of what full supervision buys on these tasks.

**That reframes H1's negative result rather than merely restating it.** The earlier entry recorded
that the textbook prior is worth fewer than fifty labelled images. Set against the ceiling, the
reason is visible: the whole interval the prior was competing for is narrow. The best zero-label arm
per dataset — whichever of A, B and D wins there — sits a median 0.094 below the ceiling and is
within five points of it on one dataset of six, while the labelled probe closes that to 0.007. There
was never much headroom between "a few labels" and "all of them" for a zero-label prior to claim.

Two limits on reading any of this, both now in the report's prose. These gaps subtract a number
from another paper: no bootstrap here covers them, unlike every other interval in the report, which
is a paired percentile interval on the same 500 images. And the table's last column is the best of
five methods, which is not always the same method across datasets, while Figure 1 draws the
ResNet-18 (224) row alone — the one backbone trained at this study's own input resolution.
`ceiling()` is defined once in `priors/report.py` and read by both the table and the macros, so the
prose and the table cannot disagree about which method won a dataset. ACC is pinned beside AUC in
the source file and deliberately not shown: this study computes no ACC to set beside it.

**Two of my own numbers were wrong in the first build of this table, and are recorded here because
the report would not have contradicted either.** `sorted(values)[len(values) // 2]` is not a median
on an even-length list — it is the upper of the two middle values — so the zero-label gap printed
0.115 when the answer is 0.094 and the concept gap 0.111 when it is 0.089. And the "within two
points" count compared raw floats, where pneumoniamnist's gap is 0.020000000000000018, so the prose
said five of six while the table beside it printed 0.971 against 0.991. Both are fixed and pinned by
tests. The lesson is the one the workflow is built around: a number that reaches the prose through a
macro is still only as good as the function behind it, and the check that caught these was reading
the generated table against the generated sentence.

## 2026-09-12 — Thinking works; the reason it did not was our own token budget

Tested because the user asked whether reasoning had ever been made to work, having read in the RCD
documentation that most of these models support it. It does, and the conclusion this project has
carried since 2026-09-09 was wrong in its cause, though not in what was observed.

**What the old claim said.** `WORKFLOW.md` §7 and `priors/llm.py` both stated that with reasoning
left on, the primary model spends its whole token budget in `reasoning_content` and returns
nothing. True as observed, and the inference drawn from it — that the served stack cannot do this —
was not. The budget was `max_tokens: 512`, which is this workflow's own config line, sized for
twelve concepts of JSON and nothing else. A model that thinks for 1,578 tokens and then answers
hits that ceiling mid-thought, and what the reader sees is a truncated chain of thought in a
reasoning field and an empty `content`. The diagnosis stopped one step short of the cause.

**Measured today**, one call per cell through `priors/llm.py` on the real concept prompt with a
real 224-pixel image (pneumoniamnist, image 0):

| model | thinking on, 512 | 2048 | 4096 | 8192 |
|---|---|---|---|---|
| qwen3.8-27b-fp8 | truncated | parses, 1578 tok, 62 s | parses | — |
| gemma-4-12b | truncated | parses, 1447 tok, 10 s | — | — |
| gemma-4-31b | truncated | parses, 1171 tok, 30 s | — | — |
| qwen3.5-9b | truncated | truncated | truncated | truncated |

With thinking off the same call costs 112 completion tokens and 3.8 s on the primary model, so
reasoning is a factor of ten to sixteen in wall clock and about fourteen in completion tokens.
qwen3.5-9b — the same model that answers in the `reasoning` field with thinking off — did not
finish a chain of thought within 8192 tokens and would need its own budget.

**And `reasoning_effort` is a first-class parameter**, which is the part with consequences beyond
this correction. The service's `/v1/models?full=true` endpoint reports, per model, the effort
levels it accepts. The primary model advertises four and all four work: `none` (112 tokens,
4.9 s), `low` (982, 39.4 s), `medium` (986, 41.3 s), `xhigh` (1578, 68.0 s). That is a cleaner
control than the `chat_template_kwargs.enable_thinking` boolean this workflow sends, and it is
also a warning: the service's **default** for this model is `xhigh`, so a caller who sets nothing
gets the slowest setting. This workflow has always set the switch explicitly, which is the only
reason its archive is uniform.

**Nothing was re-scored and nothing will be by this entry.** The archive was bought thinking-off
and is a fixed input (§5, principle 7); the correction is to the *stated reason* for that setting,
not to the setting. `WORKFLOW.md` §7 now carries both the measurement and the date, and §10 lists
`reasoning_sweep` as an extension that was cut as impossible and is merely expensive. The
docstring in `priors/llm.py` still carries the old claim deliberately: that module is a `code()`
input to all 300 protected score chunks, so correcting a comment in it marks the whole archive
stale, and the honest repair is an edit plus `snakemake --touch` from the owner's checkout rather
than an edit made casually from a session that does not run the workflow.

## 2026-09-12 — What the service actually offers: no bigger open-weight eyes, and two aliases that would break an archive

The same session read the service's `/v1/models?full=true` metadata rather than probing, which is
what the RCD documentation points at and what this project should have used from the start. Kept
as `docs/rcd_llm_service.md`, with every claim marked as documented or measured.

**The H3 ladder cannot be extended upward in open weights.** Nine locally hosted models declare
the `images` feature, and the largest is `gemma-4-31b`, which this study already scores. The big
models on the service are text-only and reject an image outright with `400 ... is not a multimodal
model`: `glm-5.3` (753B, the largest thing RCD hosts), `deepseek-v4-pro`, `gptoss-120b`, the GLM
5.x builds. What is available instead is *sideways*: `qwen3.6-27b-fp8` and `qwen3.6-35b-a3b-fp8`,
a newer generation at the primary model's size, both `experimental` rather than `active`. And the
OpenAI gateway models are reachable with this same key — `gpt-5.5` and `gpt-5.6-terra` both
answered this workflow's concept prompt with an image attached, parsed complete, at about 1,226
prompt tokens and 291–428 completion tokens per call — but they are closed, of unknown size, and
cannot sit on a parameter axis.

**Two aliases on the service would silently destroy an archive's meaning.** `cub` and `tiger`
point at "a smaller agentic capable model" and "the most powerful model we are currently hosting";
`cub` resolves today to this study's own primary model, and `tiger` to `glm-5.3`. An alias is a
promise that the weights behind a name may change without notice, which is the same failure as the
generated-rule bug of 2026-09-11 with nobody to blame for it. Recording `served_model` in every
manifest is what makes it survivable; naming the target rather than the alias is what avoids it.

**A lifecycle field exists and this study's four models are all `active`.** `experimental` models
may be removed without notice and their engines updated underneath a run; `active-lts` models are
promised not to retire mid-semester. A study that spans weeks should read that field before
choosing, and this one did not know it existed.

## 2026-09-12 — What a gateway call costs: caching carries this workflow, and flex halves the rest

Measured while answering how far the project's OpenAI credits would go on `gpt-5.6-terra`. The
numbers are in `docs/rcd_llm_service.md`; the finding is that this workflow's prompt shape is
unusually cheap to run on a metered model, for a reason worth stating.

**The concept prompt is a fixed prefix repeated five hundred times per dataset.** Only the image
changes between calls of a cell, so the 1,500-to-2,000-token rendered prompt is identical across
the whole cell. Six consecutive organamnist calls each reported 1,792 of 2,018 prompt tokens
cached — 89%. That is not a tuning trick; it is a consequence of `render_prompts` being its own
rule (2026-09-11), which made the prompt an artifact rather than a string formatted at the call
site. A workflow that rebuilt the prompt per image with the image's own id in it would cache
nothing.

**Mean cost per call, six datasets, two images each, `reasoning_effort: low`: 1,684 prompt and 313
completion tokens**, every one parsing complete. With caching and the documented `flex` service
tier — accepted on ordinary chat completions, not only through the Batch API — a full 3,000-call
concept pass over the six test samples is about 1.0M price-equivalent input against 5.05M nominal.

**No credit-to-currency rate is documented and the service exposes no pricing endpoint**, so the
absolute cost is not knowable from here. Recorded instead: this session spent 33,540 prompt and
7,387 completion tokens on `gpt-5.6-terra` and 1,226 and 291 on `gpt-5.5`, so the delta on the
OpenAI Credits page fixes the rate for every estimate above.

Nothing was bought toward a result. These were diagnostic calls, no archive was written, and
whether a gateway model enters the study at all is undecided: it cannot join H3, since a closed
model of unknown size has no place on a parameter axis, and it makes the contamination limit
(§2) strictly worse.

## 2026-09-12 — Arm D removed from the workflow; what it measured stays here

The user asked for arm D to be scrubbed from the repository. Done, everywhere a rule, a test, a
table, a figure or a plan sentence mentioned it: the directed prompt and its renderer, the fan-out
cell, the classify and evaluate blocks, the `arm_d` table and its macros, the report section, the
curve figure's third line, the literature table's D column, and the three test modules that held
any of it. 291 tests pass, `rule all` is 312 jobs where it was 342, and the scoring fan-out is 270
chunks where it was 300 — back to the pre-registered budget.

**Why it went, stated plainly because the study is better for it.** Arm D was designed after seeing
H2 fail, so it could decide nothing, and an arm that decides nothing has to be labelled post-hoc in
every table, figure, macro and paragraph it touches. Two entries above record it doing exactly
that. The cost was not the 3,000 calls; it was that every reader of the report met a number they
had to be told twice not to believe, on every page it appeared. Four pre-registered arms and no
asterisk is a clearer study than five arms and a standing caveat.

**What it measured is not deleted, and this entry is why.** Arm D answered its question: the
nearest-fingerprint readout really is lossy (D beat B on 4 of 6, recovering nearly all of
pneumoniamnist's deficit), and the bank is not information the model lacked (D lost to A on 4 of 6).
Those two readings are in the entry of 2026-09-12 above and remain the best evidence about what
went wrong with H2. `CHANGELOG.md` and `SESSION_LOG.md` are appended and never rewritten, so
neither was edited: the removal is a new fact about the workflow, not a revision of what was found.

**The archive was not deleted either.** The 30 `__directed__` chunks sit in `results/score/`,
write-protected, unread by any rule and no longer required by `rule all`. They were bought with
3,000 calls, and nothing about removing an arm justifies destroying the record of it. Deleting them
is a separate decision and would need to be a deliberate one.

**What this costs to realise in the owner's checkout**: no LLM calls at all. The archive is
untouched, so only the analysis chain reruns — classify, evaluate, evaluate_across, tables, figures
and the report, about sixteen CPU jobs and a few minutes.

**The lesson, and the rule any future arm obeys.** A decision rule before the calls. An arm worth
adding is worth pre-registering; one that cannot be pre-registered is a separate study, not an
extension inside `rule all`. WORKFLOW.md §10 now says so where arm D's description used to be.

## 2026-09-12 — H4's thinking wave, stopped before it could write nothing

Eleven thinking chunks were submitted together and would have been the 2026-09-12 failure again —
a wave that spends every call and writes no file — so they were cancelled forty minutes in and
resubmitted under a cap. Recorded because the reasoning is the same one this project has now met
three times and got wrong twice.

**Measured while the eleven ran**, one timed call through the same code path: **134 s per call**,
against 16.7 s for the single chunk that ran alone an hour earlier and 41 s at concurrency one this
morning. That is the endpoint's flat-throughput behaviour again — latency rises in proportion to
our own concurrency, aggregate stays put at about 0.08 calls per second — so eleven chunks in
flight is not eleven times faster, it is eleven chunks each taking 3.7 hours. Against a 240-minute
limit that left seventeen minutes of margin on a service shared with the rest of the university,
and a chunk that overruns its limit writes nothing, losing every call it made.

**The fix is a cap, and the cap is not a throughput knob.** Four in flight and twelve in flight
finish the whole wave at the same hour, because the aggregate is flat. What four buys is that each
chunk takes about eighty minutes rather than 3.7 hours, so no chunk is anywhere near its limit, and
whole datasets land as the wave proceeds instead of all twelve arriving at the deadline together.
`llm_reader_medium: 4` in the profile, `runtime: 600` in config, both with the measurement in a
comment beside them. The thinking reader gets its own resource rather than sharing the primary
model's: it is the same endpoint and the two caps have to be read together, but a thinking chunk is
an order of magnitude longer than a thinking-off one and one shared cap cannot say that.

**Cost of stopping: about 200 calls**, spent and unrecorded, which is what forty minutes at the
observed aggregate rate buys. The thirteen chunks already written — one thinking, twelve gateway —
were untouched and are kept.

**Still missing, and it is the same gap recorded on 2026-09-12.** A scoring job writes its JSON at
the end and logs nothing on the way, so a running chunk is indistinguishable from a hung one, and
the only way to learn the rate was to spend a call on a diagnostic. That is now twice this has cost
real time. A progress line every ten calls belongs in `priors/score.py` before the next re-score.
