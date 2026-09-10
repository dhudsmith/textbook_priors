# Change log

Dated findings, decisions and corrections. Appended, never rewritten. Structure will live in
README.md once the skeleton exists (WORKFLOW.md §9, step 7); the plan lives in WORKFLOW.md.

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
