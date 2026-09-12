# Literature benchmarks

One file, `benchmarks.yaml`: published, fully supervised AUC and ACC for the six MedMNIST v2 tasks
this study uses, read into the report as a citable reconciliation point (WORKFLOW.md section 4)
and not rerun. Unlike the concept bank, nothing here is built for this project — it is transcribed
from a published table.

## Source and verification

Yang et al., "MedMNIST v2 — A large-scale lightweight benchmark for 2D and 3D biomedical image
classification," *Scientific Data* 10, 41 (2023) — the same paper that defines the MedMNIST v2
release this study reads (`config/medmnist.yaml`'s Zenodo record). Table 3 reports AUC and ACC for
five methods (ResNet-18 and ResNet-50 at 224 and 28 pixels, auto-sklearn, AutoKeras, Google AutoML
Vision) on all twelve 2D datasets; `benchmarks.yaml` keeps the 224-pixel ResNet-18/50 rows and the
three AutoML rows for the six datasets this study runs.

Transcribed by hand from the arXiv PDF (2110.14795) on 2026-09-12 and checked twice: once
value-by-value against the extracted table text, once by confirming each dataset's row is
internally consistent with the paper's own across-dataset average (Table 5). Every method the
paper reports is kept rather than only the best one, so a reader sees the range a published
benchmark actually covers.

## What this is not

These are fully supervised numbers — trained on each dataset's whole official training split,
thousands to tens of thousands of images (WORKFLOW.md section 4) — not a same-conditions baseline
for any arm here, which sees at most 2,000 labelled images. The report reads them as a ceiling for
the task, not as a comparison arm: no hypothesis in `WORKFLOW.md` section 2 turns on a value in
this file, and none of `evaluate_across`'s three `supported` flags reads it.
