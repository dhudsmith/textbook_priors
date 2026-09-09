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

Recorded here because they bound what arm B (fingerprint matching with no training) can achieve,
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

- **`chestmnist` is multi-label, and pairwise separability is the wrong measure for it.** An
  image showing cardiomegaly and effusion is correctly labelled with both, so arm B never
  chooses between two findings; each finding is scored against its own signs. Its fingerprints
  are therefore deliberately thin — 74% `any`, and `cardiomegaly` commits exactly one concept, a
  wide cardiac silhouette. Raising its separability score would require asserting that findings
  are absent when the sources say nothing of the kind. That trade was tried during construction
  and reverted; the file carries a header block saying so, because the failure mode is that a
  later audit flags these pairs and someone "fixes" them back into the defect.

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
  pleural line and supradiaphragmatic gas. These rule *in* and say nothing when absent. A
  matching rule for arm B that averages a distance over all concepts will under-weight exactly
  the features clinicians rely on most; this is worth handling explicitly when arm B is built.

- **`tissuemnist`'s prior is weak by construction.** Its labels were assigned by
  immunofluorescence markers in separate channels and by where each cell sat in the 3D volume —
  none of which reaches the greyscale image. Hand-crafted nuclear shape and texture features
  reached only 42.2% balanced accuracy in the source paper. Its crops are 32x32x7 voxels
  rendered as 28x28 projections, so the 224-pixel version is an upscale carrying no additional
  detail. The primary literature does not hold the values this file needs: Woloshuk 2021 states
  it "does not address which specific features in the nuclei are key determinants", and Winfree
  2017 and Ferkowicz 2021 use DAPI only to locate and count nuclei. Its tubular-class values
  therefore rest on histology teaching sites, which each file names explicitly.

- **Two features are at or below the resolution.** `retinamnist` microaneurysms are 15-60 um
  against roughly 50 um per pixel for a 45-degree field resized to 224, so grade 1 — defined by
  "microaneurysms only" — turns on a feature of about one pixel, and grade 0 vs 1 separates on
  that concept alone. `chestmnist`'s 1 cm nodule is about 6 pixels. Both are kept, because they
  are what the scales are built on, but neither should be believed without this caveat.

- **One open verification item.** MedMNIST crops organ bounding boxes and resizes them to a
  square with no stated aspect-ratio handling. If that resize is anisotropic it stretches
  elongated organs toward filling the frame, and `elongation` and `relative_size` in the three
  `organ*mnist` files become unreliable. This is not answerable from the literature and was not
  guessed at: each file carries a DO NOT TRUST YET block naming the affected values, to be
  checked against the fetched arrays at stage 2 (CACHE). A second consequence rides on it — with
  the spleen attenuation corrected for portal-venous phase, liver and spleen separate in
  sagittal on `relative_size` alone, so if that concept is dropped they become inseparable too.

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

## Schema

Defined in `../../CONCEPT_BANK.md`. The rules a smoke test must enforce: dataset name, task and
every class name match the `medmnist` label map exactly; every concept has a lowercase
underscored `id`, a `question` answerable from the image alone, an ordered `scale` of two to
five levels and at least one source key; every class fingerprint names every concept with a
level from that concept's scale or `any`; every referenced source key exists in
`provenance.sources` with a citation and a DOI or URL; `reviewed_by` is present and, for this
project, contains the word `simulated`.

The workflow's `smoke` target does not exist yet — it arrives with the Snakefile skeleton
(`WORKFLOW.md` section 10, step 1). Until then these files have been checked by a standalone
validator that encodes the same rules, plus two structural checks the prose requires: the three
`organ*mnist` files must share one concept set, and `retinamnist`'s fingerprints must be
monotone across grades 0 to 4. The smoke test should encode all of it.
