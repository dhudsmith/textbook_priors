# Change log

Dated findings, decisions and corrections. Appended, never rewritten. Structure lives in
README.md; the plan lives in WORKFLOW.md.

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
with arm B's zero-label accuracy as the line to cross. The headline number is now n_B: the labels
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
figure, the reasoning sweep, and two of the three diagnostics. The permutation controls that
replace the prompt ablation are re-analyses of the response archive and cost no calls. Four
figures became three, six arms became five, nine stages stayed nine, and the plan lost the talk
narrative to TALK.md so that what remains is the experiment.

**Still needing a person:** confirmation of the 54,000-call volume with the service owners, and
the acceptable-use statement for de-identified public medical images.
