# Building the concept bank

Instructions for producing `data/concepts/<dataset>.yaml`, the twelve files that carry the
project's prior knowledge into the workflow described in `WORKFLOW.md`. This step happens
outside the workflow, with a web-connected assistant (ChatGPT or Claude), and its output is
committed as an input with full provenance.

## Why this is outside the workflow

Constructing a prior is a scholarly act: finding the literature, reading it, deciding which
features an expert actually uses. It is not a computation, it needs the open internet (the RCD
models cannot reach it), and in a real project it ends with a domain expert signing off. The
workflow starts where computation starts, with these files as fixed, cited inputs.

For this project the expert review is **simulated**. Each file says so explicitly. Nothing
downstream pretends otherwise.

## What a file contains

One file per MedMNIST dataset. Three parts: provenance, the concepts the VLM will be asked
about, and each class's textbook fingerprint over those concepts.

```yaml
dataset: dermamnist
modality: dermatoscopic images of pigmented skin lesions
task: multi-class                        # multi-class | binary | multi-label | ordinal
medmnist_task: multi-class               # the medmnist package's raw task string, verbatim
source_dataset: HAM10000 (Tschandl et al. 2018)
provenance:
  method: literature review with a web-connected assistant
  assistant: <model name>, <date>
  reviewed_by: simulated review by <your name>, <date>; no clinician has reviewed this file
  sources:
    - key: abbasi2004
      citation: "Abbasi NR et al. Early diagnosis of cutaneous melanoma: revisiting the ABCD criteria. JAMA 2004;292:2771-6."
      doi: 10.1001/jama.292.22.2771
      used_for: [asymmetry, border_irregularity, colour_variegation, diameter]
concepts:                                # abridged: the real file lists all 6-12 concepts,
                                         # and every fingerprint below names every one of them
  - id: asymmetry
    question: "Is the lesion asymmetric in shape or colour across one or both axes?"
    scale: [absent, mild, marked]
    sources: [abbasi2004]
  - id: border_irregularity
    question: "Are the borders irregular, notched or blurred rather than smooth and sharp?"
    scale: [absent, mild, marked]
    sources: [abbasi2004]
    anchors:                               # required; exactly one entry per scale level
      absent:
        text: "the edge is smooth and sharp the whole way round"
        sources: [abbasi2004]
      mild:
        text: "an abrupt cut-off in up to about three of the eight perimeter segments"
        sources: [abbasi2004]
      marked:
        text: "an abrupt cut-off in four or more of the eight segments, half the rim or more"
        sources: [abbasi2004]
classes:
  melanoma:
    fingerprint: {asymmetry: marked, border_irregularity: marked, colour_variegation: marked}
    sources: [abbasi2004]
  melanocytic_nevus:
    fingerprint: {asymmetry: absent, border_irregularity: absent, colour_variegation: absent}
    sources: [abbasi2004]
```

Rules the smoke test enforces:

- `dataset` and every class name match the `medmnist` package's label map exactly.
- `medmnist_task` is the package's raw task string verbatim; `task` is its mapping into this
  document's vocabulary (`multi-class`, `binary`, `multi-label`, `ordinal`). The two must agree.
- Every concept has an `id` (lowercase, underscores), a `question` answerable from the image
  alone, an ordered `scale` of two to five levels, and at least one source key.
- Every concept carries an `anchors` block: exactly one entry per scale level, no level missing
  and none named that is not in the scale. Each anchor has a `text` describing what that level
  looks like and at least one source key. No two anchors in a concept share the same text, and
  none merely restates its own level token. The scoring prompt renders these, so a concept
  without them renders nothing (`WORKFLOW.md` §7).
- The three `organ*mnist` files share one byte-identical `concepts` block.
- `retinamnist` fingerprints are monotone in the lesion concepts across grades 0 to 4.
- Every class has a fingerprint that names every concept with a level from that concept's scale,
  or `any` where the literature does not commit.
- Every source key referenced exists in `provenance.sources` with a citation and a DOI or URL.
- `reviewed_by` is present and, for this project, contains the word `simulated`.

The `concepts` block feeds every arm that uses concept scores (arms B and C in
`WORKFLOW.md` §3); the `classes` fingerprints feed arm B alone, and are the project's only
label-free predictor, so a careless fingerprint costs a hypothesis rather than a decimal place.

Rules the review enforces (not machine-checkable):

- Concepts describe **what is visible**, not the diagnosis. "Central bright region with dark
  border" is a concept; "looks malignant" is not.
- Anchors say what each level *looks like*, so the model is not left to invent the threshold.
  Adjacent anchors must be separable: if `mild` and `marked` could describe the same image, they
  are not doing their work. Prefer a comparison to something else in the frame over an absolute
  measure, since the image carries no scale bar, and put the source's own numeric threshold in
  the anchor wherever one exists. Where the literature sets no boundary, describe the appearance
  in the source's qualitative terms and record that the boundary was reasoned rather than read —
  do not manufacture precision.
- Concepts are chosen for what the VLM will actually see: 224-pixel images, sometimes greyscale,
  without clinical context. A feature that needs magnification or a second view does not belong.
- Six to twelve concepts per dataset. Fewer than six cannot separate the classes; more than
  twelve dilutes the prompt and the regression.
- Fingerprints are the textbook's expectation, not a guess at the dataset's statistics.

## Procedure, per dataset

1. **Anchor on the source data.** Start from the MedMNIST v2 paper's description of the dataset
   and the paper for its source data (table below). Note the imaging modality, how the images
   were acquired, the class definitions and the label map.
2. **Find the diagnostic criteria.** Search for the clinical or pathological criteria used to
   distinguish these classes: guideline documents, review articles, the source dataset's own
   annotation protocol, standard atlases. Prefer sources that list features explicitly. Record
   each with citation and DOI as you go.
3. **Read, then distil.** For each class, list the visual features the sources say an expert
   looks for. Merge synonyms across sources. Drop anything invisible at 224 pixels.
4. **Turn features into questions with scales.** Each concept becomes one question a careful
   observer could answer from the image, with an ordered scale. Keep wording neutral; do not name
   the class in the question.
5. **Write the fingerprints.** For each class, the expected level of every concept according to
   the sources; `any` where they are silent.
6. **Review.** Read the file as a sceptical clinician would: is every concept visible, is every
   fingerprint sourced, is anything a diagnosis in disguise? Fix, then fill `reviewed_by` with the
   simulated-review statement and the date.
7. **Validate.** Run `snakemake --profile profiles/local -j 2 -F smoke` in the workflow repository
   once the file is in `data/concepts/`; `tests/test_bank.py` encodes every rule above.

## Starting points

Verify each against the MedMNIST v2 paper before relying on it.

| dataset | source data | where the criteria live |
|---|---|---|
| pathmnist | NCT-CRC-HE-100K (Kather et al. 2019) | colorectal histology tissue-type descriptions; the nine tissue classes |
| chestmnist | NIH ChestX-ray14 (Wang et al. 2017) | radiology descriptions of the 14 findings; Fleischner Society glossary |
| dermamnist | HAM10000 (Tschandl et al. 2018) | ABCD rule, seven-point checklist, dermoscopy pattern analysis |
| octmnist | Kermany et al. 2018 | OCT descriptions of CNV, DME, drusen versus normal retina |
| pneumoniamnist | Kermany et al. 2018 | radiographic signs of paediatric pneumonia |
| retinamnist | DeepDRiD | international diabetic-retinopathy severity scale (microaneurysms, haemorrhages, exudates, neovascularisation) |
| breastmnist | Al-Dhabyani et al. 2020 | BI-RADS ultrasound lexicon (shape, margin, echo pattern, posterior features) |
| bloodmnist | Acevedo et al. 2020 | haematology morphology of the eight peripheral-blood cell types |
| tissuemnist | BBBC051 (Woloshuk et al. 2021) | kidney cortex cell-type morphology under fluorescence microscopy |
| organa/c/smnist | LiTS (Bilic et al. 2023) with organ labels (Xu et al. 2019) | cross-sectional anatomy of the eleven organs in axial, coronal and sagittal CT |

## Notes on the hard cases

- **chestmnist** is multi-label with fourteen findings. Write concepts at the level of
  radiographic signs (opacity location and pattern, cardiac silhouette size, pleural line,
  mediastinal contour) rather than one concept per finding, and let fingerprints share concepts.
  Cap at twelve concepts. chestmnist is not among the talk version's six datasets (`WORKFLOW.md`
  §10), and on the full branch it is excluded from arm B; write its fingerprints as the expected
  levels when a finding is present, as documentation, and expect its numbers to come from the arms
  that need only the concept scores.
- **retinamnist** is ordinal. Fingerprints for the five grades should be monotone in the lesion
  concepts; the scale levels do the work.
- **organa/c/smnist** are greyscale CT slices with a fixed window. Concepts are anatomical
  (position in the slice, shape, density relative to neighbours, adjacent structures), and the
  same eleven classes appear in three planes, so write one shared concept set with three
  fingerprint files, or note where a plane changes the expected level.
- **tissuemnist** and **bloodmnist** classes are cell types; concepts are morphological (nucleus
  shape and lobation, cytoplasm texture and colour, granules, size relative to neighbours).
- **breastmnist** and **pneumoniamnist** are binary; keep the concept set small and the two
  fingerprints clearly opposed.

## A prompt to start the assistant

> I am building a cited bank of visual diagnostic features for the MedMNIST dataset
> `<dataset>` (`<modality>`, classes: `<label map>`; source data: `<source>`). Search for the
> clinical or pathological criteria used to distinguish these classes, prioritising guideline
> documents, review articles and the source dataset's annotation protocol. For each source you
> use, give the full citation and DOI. Then list six to twelve visual features that an expert
> uses and that are visible in a single 224-pixel image without clinical context, phrased as
> neutral questions with an ordered scale of two to five levels. Finally, for each class, give the
> expected level of every feature according to the sources, or `any` where they are silent. Output
> the result in this YAML schema: `<paste the schema above>`.

Then read the sources it cites. The assistant finds and drafts; the reader decides.

## Deliverables

- `data/concepts/<dataset>.yaml` for all twelve datasets, passing the smoke test.
- `data/concepts/README.md`: the method and the date, the simulated-review statement and the note
  that in a real project a clinician reviews each file, a per-dataset table of classes, concepts
  and sources, and every known limit of the bank — anything a downstream reader would otherwise
  discover as a bug.
- `report/references.bib` entries for every source key, so the technical report can cite the
  bank's sources.
