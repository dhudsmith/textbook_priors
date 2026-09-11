# The concept bank

Twelve files, one per MedMNIST v2 2D dataset, carrying this project's prior knowledge into the
workflow. Each names the visual diagnostic features a domain expert uses, as neutral questions
with ordered scales, and gives every class its expected level on each — the class's *textbook
fingerprint*. The workflow reads them as fixed, cited inputs; nothing here is computed.

## Method

Built on 2026-09-09 by the procedure in `../../CONCEPT_BANK.md`, outside the workflow, with a
web-connected assistant (Claude Opus 5, `claude-opus-5`) working one dataset at a time. For each
dataset the assistant anchored on the MedMNIST v2 paper and the source-dataset paper, searched
for the clinical or pathological criteria that distinguish the classes — guideline documents,
consensus lexicons, review articles, the source dataset's own annotation protocol, standard
atlases — distilled the visual features those sources enumerate, dropped everything invisible in
a single 224-pixel image without clinical context, and wrote the surviving features as questions
with ordered scales and per-class fingerprints. Class names and task types were taken verbatim
from the `medmnist` package's label maps (version 3.0.2), not retyped.

Every source carries a citation and a DOI or stable URL. The twelve files hold 125 source
entries drawing on 92 distinct works, and every one was checked independently of the assistant
that proposed it: the 73 with DOIs were resolved through doi.org content negotiation and their
registered titles compared against the citation text, and the 19 without were fetched. None
failed. `../../report/references.bib` carries one BibTeX entry per source key, 92 in all, so the
technical report can cite the bank's sources.

Each file was then reviewed twice more, by reviewers that had not written it: once for schema
and internal consistency, once for scientific quality. Both passes found real defects, and the
files record the corrections. The recurring one is worth naming because it will recur again:
**a feature that is characteristic when present is not the same as a feature that is expected.**
Committing a class to a high-specificity, low-sensitivity finding (BI-RADS' thick echogenic
halo, dermoscopy's spoke-wheel areas) inverts the criterion it came from. Every file now states
the rule it applied in a header block: commit only where the source reports the feature in a
majority of that class, or where it is definitional; otherwise `any`, or an ordinal bound that
the comment names as a bound.

## Expert review is simulated

**No clinician has reviewed these files.** Every file's `provenance.reviewed_by` says so
explicitly and contains the word `simulated`. The review that was performed is the sceptical
read described in `CONCEPT_BANK.md` step 6 — is every concept visible in one small image, is
every fingerprint traceable to a source, is anything a diagnosis in disguise — carried out by
the same class of assistant that drafted the file, not by a domain expert.

In a real project a clinician reviews and signs each file before anything downstream is
believed, and `reviewed_by` records their name and the date. Nothing downstream of this
directory should be read as if that had happened here.

## What is in each file

| dataset | task | classes | concepts | sources |
|---|---|---:|---:|---:|
| bloodmnist | multi-class | 8 | 9 | 11 |
| breastmnist | binary | 2 | 7 | 8 |
| chestmnist | multi-label | 14 | 12 | 10 |
| dermamnist | multi-class | 7 | 12 | 17 |
| octmnist | multi-class | 4 | 9 | 9 |
| organamnist | multi-class | 11 | 12 | 10 |
| organcmnist | multi-class | 11 | 12 | 10 |
| organsmnist | multi-class | 11 | 12 | 10 |
| pathmnist | multi-class | 9 | 12 | 8 |
| pneumoniamnist | binary | 2 | 8 | 8 |
| retinamnist | ordinal | 5 | 10 | 7 |
| tissuemnist | multi-class | 8 | 8 | 17 |

123 concepts and 92 distinct sources in total. The three `organ*mnist` files share one identical
concept set, as the same eleven organs appear in three planes; only the fingerprints and the
plane wording differ.

`task` uses the vocabulary of `CONCEPT_BANK.md` (`multi-class`, `binary`, `multi-label`,
`ordinal`). Each file also carries `medmnist_task` with the raw string from the `medmnist`
package, so the mapping between the two is recorded rather than inferred.

## Known limits

Recorded here because they bound what arm B (nearest fingerprint, no labels) can achieve,
and because a limitation that is discovered later looks like a bug. Each is documented in its
own file too.

- **Seven class pairs cannot be separated by any concept**, in three groups. `organsmnist`
  `femur-left`/`-right`, `kidney-left`/`-right` and `lung-left`/`-right`: a single sagittal crop
  carries no cue for which side of the body it came from. `tissuemnist` `Collecting Duct,
  Connecting Tubule` against each of `Distal Convoluted Tubule`, `Proximal Tubule Segments` and
  `Thick Ascending Limb`, and `Distal Convoluted Tubule` against `Thick Ascending Limb`: every
  published difference between these segments is cytoplasmic or immunohistochemical, and none
  survives a nuclear stain. These are properties of the images and the labels, not omissions,
  and no concept was invented to paper over them.

- **`chestmnist` is out of arm B, and pairwise separability is the wrong measure for it.**
  `WORKFLOW.md` §10 excludes it: nearest-fingerprint matching is not defined over fourteen
  co-occurring findings, so chestmnist runs in arms A, C, P and E only. Its fingerprints are
  deliberately thin — 74% `any`, and `cardiomegaly` commits exactly one concept, a wide cardiac
  silhouette — which is right for a label that constrains one sign and says nothing about the
  rest. They stand as documentation and as the expected levels when a finding is present, and
  the concept *scores* still carry chestmnist through arms C and P. Raising its separability
  would mean asserting findings are absent when the sources say nothing of the kind. That trade
  was tried during construction and reverted; the file carries a header block saying so, because
  the failure mode is a later audit flagging these pairs and someone "fixing" them back.

- **A disjunctive criterion cannot be expressed as one fingerprint.** A fingerprint is a single
  vector per class, but several diagnostic criteria are disjunctions: the ICDR 4-2-1 rule
  ("any of the following"), Menzies' BCC rule (no network plus *one or more* of six features),
  the WHO paediatric pneumonia categories (consolidation *or* other infiltrate). Where the
  disjunction could be relaxed to `any` it was; where relaxing it would collapse a class onto
  its neighbour it was left as a conjunction and flagged in the file. `retinamnist` grade 3 is
  the clearest instance. Expressing these properly needs a set of vectors or a rule, which is a
  change to how arm B matches, not to the bank.

- **Some concepts are one-sided.** After the sensitivity rule was applied, several concepts are
  committed by one class and held at the floor by the others — BI-RADS' thick echogenic halo
  (36% sensitive, 99% specific), dermoscopy's leaf-like and spoke-wheel areas, chestmnist's
  pleural line and supradiaphragmatic gas. These rule *in* and say nothing when absent. Arm B as
  specified in `WORKFLOW.md` §3 masks `any` levels and averages the absolute difference over the
  concepts a fingerprint does commit to, so a class carried by one high-specificity feature is
  scored on few concepts and a near-miss on any of them costs it proportionally more. That is the
  honest reading of a thin fingerprint rather than a defect, but it is worth knowing when the
  per-dataset arm-B numbers come in.

- **`tissuemnist`'s prior is weak by construction.** Its labels were assigned by
  immunofluorescence markers in separate channels and by where each cell sat in the 3D volume —
  none of which reaches the greyscale image. Hand-crafted nuclear shape and texture features
  reached only 42.2% balanced accuracy in the source paper. Its crops are 32x32x7 voxels
  rendered as 28x28 projections, so the 224-pixel version is an upscale carrying no additional
  detail. The primary literature does not hold the values this file needs: Woloshuk 2021 states
  it "does not address which specific features in the nuclei are key determinants", and Winfree
  2017 and Ferkowicz 2021 use DAPI only to locate and count nuclei. Its tubular-class values
  therefore rest on histology teaching sites, which each file names explicitly.

- **Sixteen class pairs in arm-B datasets rest on a single committed concept.** Not defects —
  each is the textbook distinction itself — but each is a single point of failure for arm B, and
  a scoring error on that one concept collapses the pair. Beyond retinamnist 0/1 and 3/4 named
  above: bloodmnist immature-granulocyte against neutrophil and against monocyte
  (`chromatin_density`); dermamnist dermatofibroma/nevus (`central_white_patch`) and actinic
  keratoses/vascular (`red_lacunae`); octmnist drusen/normal (`rpe_line_contour`, whose
  middle-to-top boundary this README already records as reasoned rather than published);
  organamnist and organcmnist femur, kidney and lung left/right (`body_side` alone — a single
  left-right convention error would collapse all six at once); organsmnist liver/spleen
  (`relative_size`, which is also the concept under the resize caveat).

- **Two source-level caveats that live only in the YAML.** The organ files assume portal-venous
  contrast phase and note that LiTS is a liver-tumour cohort, so its abdomens are not a healthy
  reference. dermamnist's melanoma fingerprint is the *pigmented* melanoma; amelanotic and
  nodular melanomas score `absent` where it commits, which the file records in a comment.

- **Two features are at or below the resolution.** `retinamnist` microaneurysms are 15-60 um
  against roughly 50 um per pixel for a 45-degree field resized to 224, so grade 1 — defined by
  "microaneurysms only" — turns on a feature of about one pixel, and grade 0 vs 1 separates on
  that concept alone. `chestmnist`'s 1 cm nodule is about 6 pixels. Both are kept, because they
  are what the scales are built on, but neither should be believed without this caveat.

- **The organ resize is a standing caveat, not a gate.** MedMNIST crops organ bounding boxes and
  resizes them to a square with no stated aspect-ratio handling. If that resize is anisotropic it
  stretches elongated organs toward filling the frame. Each of the three `organ*mnist` files
  carries a KNOWN LIMITATION block naming the affected concepts and classes. `relative_size` is
  designed to survive it, because its anchors count crop-edge landmarks rather than measure axes;
  `elongation` does not, and is the weakest concept of the twelve. Related: with the spleen
  attenuation corrected for portal-venous phase, liver and spleen separate in sagittal on
  `relative_size` alone.

- **Lumped classes** force honest `any` where the sources disagree across the entities a single
  label pools: `dermamnist`'s `benign keratosis-like lesions` (seborrhoeic keratosis, solar
  lentigo, lichen-planus-like keratosis), `bloodmnist`'s immature granulocytes (a maturation
  series), `breastmnist`'s `normal, benign` (images with no lesion *and* images with a benign
  one), and `pneumoniamnist`'s `pneumonia` (bacterial and viral).

- **Fingerprints are the textbook's expectation, not the dataset's statistics.** Where a file
  commits a class to a level, a cited source says an expert expects it — the images were never
  inspected. `any` means the literature does not commit, and it is used deliberately rather than
  defensively.

- **One citation gap worth closing.** Bain, *Blood Cells: A Practical Guide*, would settle the
  `bloodmnist` immature-granulocyte values; it has no resolvable DOI and the publisher returns
  403, so those values rest on an explicitly-labelled ordinal floor instead. Anyone with library
  access can close this.

## Anchored scale levels

Every concept carries an `anchors` block: one entry per scale level, saying what that level looks
like, with its own source keys.


Why they exist, and how the scoring prompt renders them, is `WORKFLOW.md` §7. What belongs here
is the record of building them. The bank was inconsistent about anchoring before this pass: 40 of
123 questions already embedded one informally, and which ones did depended on who wrote the file,
so a cross-modality comparison partly measured prompt-authoring style.

The change is **additive**. `scale` remains an ordered list of strings — the ordinal index
mapping, the `retinamnist` monotonicity check and every existing reader are untouched — and
`anchors` sits beside it. No scale, question or fingerprint changed when anchors were added; that
was verified by parsing the before and after of every file, not by reading the diff. Scales did
change later, in the audit pass below, and those changes were deliberate.

Anchors are the level's provenance, not decoration. `marked` on its own is unsourced in any
useful sense; an anchor is a paraphrase of a diagnostic criterion with a citation attached, which
is what the bank claims to be. Where a source states a threshold it is used literally — the ABCD
rule's axes of asymmetry and eighths of the perimeter, Fleischner's 3 cm nodule and its
vessel-visibility test for consolidation against ground glass, the ICDR 4-2-1 quadrant counts,
Fleming's 50% gland-formation split, Beckman's drusen sizes. Where the literature sets no
boundary, the anchor describes the appearance in the source's own qualitative terms and carries
a comment recording that the boundary was reasoned rather than read. Many anchors rest on a real
threshold and the rest are qualitative; the files mark the reasoned boundaries in comments, so
which is which is recoverable per concept rather than per anchor.

Two conventions worth knowing, because they prevent systematic error. Anchors compare to
something else in the frame rather than to an absolute size, since the images carry no scale bar
— red cells in `bloodmnist`, the optic disc in `retinamnist`, muscle at the crop edge in the
organ files, the hemithorax in `chestmnist`. And in `octmnist`, heights are compared to heights
and widths to widths, because OCT B-scans are displayed with roughly threefold vertical stretch
and a height-to-width comparison would be wrong by that factor.

A class description, if one is ever wanted in prose, should be composed from the anchors at
render time rather than authored separately. A hand-written paragraph per class is where the
diagnosis smuggles itself back in, and it would create a second representation of the same
knowledge that can drift from the fingerprints.

### What the audit pass changed

Two reviewers went over the bank and the plan after the anchors landed, and three files changed
as a result. `pathmnist` gained `no_glands` and `no_fibres`, and `bloodmnist` gained `no_nucleus`
on its two nucleus-dependent concepts: those questions presuppose something the image may not
contain, and without a floor the model must either invent a level or return nothing, which the
archive would record as missing. Committing the affected classes to the new floors also moved
nine `pathmnist` fingerprint cells and two `bloodmnist` ones off `any`, so the bank gained signal
rather than merely avoiding a failure. `dermamnist`'s `pigment_network` was split into
`pigment_network` and `network_atypia`, both binary: presence and atypia are two axes, and the
estimators map a scale to equally spaced numbers, so the old three-level form placed "regular
network" exactly halfway between "no network" and "atypical network", which is not what the
literature means. `asymmetry` and `border_irregularity` were merged to stay within the concept
cap — they were byte-identical across all seven classes, so the merge cost no separation.

### What the prompt-rendering pass changed

One further change, on 2026-09-11, when the workflow's `render_prompts` rule made the prompt a
file that can be inspected. The concept prompt must never name a class, because H2 compares it
against the zero-shot prompt and a class name in the wrong one makes that comparison circular.
Checked as a property of the rendered strings, it held on five of the six talk-version datasets
and failed on `octmnist`, whose `retinal_thickness` scale had a level named `normal` while
`normal` is also one of its four classes. Two levels were renamed in that file:
`retinal_thickness: normal` became `not_increased`, and `foveal_contour: normal_depression`
became `depressed` so that the word leaves the file's scales altogether. Scale order, questions,
anchor text and sources are unchanged, and the four fingerprint cells naming those levels were
renamed with them, so no class's expected level moved; the estimators index a scale by position,
so no number moves either.

Three apparent collisions elsewhere were left alone, because they are shared words and not class
names: `pathmnist`'s concept `necrotic_debris` against its class `debris` (the concept is the
criterion for that class, and the prompt never offers it as a category), `bloodmnist`'s
`cytoplasm_basophilia` against `basophil`, and `organamnist`'s left/right levels against
`lung-left` and `lung-right`. The check that separates these from a real leak matches a class
name as a whole word, treating an identifier such as `necrotic_debris` as one word.

### Anchors that cannot be applied at this resolution

Written anyway, because the scales are built on them, but recorded here because a score against
them is closer to noise than to a reading:

- `retinamnist`: the `microaneurysms_dot_haemorrhages` few-versus-moderate boundary, and
  `irma: mild` at all — mild IRMA is *defined* as indistinguishable from a normal small branch,
  which no anchor wording can recover at roughly 50 um per pixel.
- `tissuemnist`: all three `chromatin_texture` levels and `outline_regularity: lobed`. A nucleus
  spans about 14 native pixels and the projection through a 3.9 um slab can fuse lobes that are
  separate in 3D.
- `octmnist`: the `rpe_line_contour` boundary between a drusenoid elevation and a fibrovascular
  one rests on reasoning about when a dome becomes a detachment, not a published threshold.
- `organ*mnist`: `elongation` cannot be made robust to an anisotropic resize, because such a
  resize drives the axis ratio toward 1 by construction and that ratio is what the concept
  measures. `relative_size` is designed to survive it, because its anchors count landmarks caught
  at the crop edge and a count survives any resize.

## Schema

Defined in `../../CONCEPT_BANK.md`, which is the single source of the rules a smoke test must
enforce — including the two structural checks this bank relies on: the three `organ*mnist` files
share one concept set, and `retinamnist`'s fingerprints are monotone across grades 0 to 4.

The workflow's `smoke` target does not exist yet — it arrives with the Snakefile skeleton
(`WORKFLOW.md` §9, step 1). Until then these files have been checked by a standalone
validator that encodes the same rules, plus two structural checks the prose requires: the three
`organ*mnist` files must share one concept set, and `retinamnist`'s fingerprints must be
monotone across grades 0 to 4. The smoke test should encode all of it.
