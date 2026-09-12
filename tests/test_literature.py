"""The pinned literature-benchmark table against the datasets this workflow runs.

`data/literature/benchmarks.yaml` is a fixed input like the bank and the release (WORKFLOW.md
section 4): nothing here is computed, so what the smoke tier can check is only that the file
covers what the study needs, that its numbers are the AUC/ACC values the report expects (fractions
in [0, 1], not the fingerprint of a value shifted a row), and that its citation actually resolves
in `report/references.bib`, since a table with a dangling `\\cite` fails `pdflatex` only after the
whole study has run.
"""
import re

from .conftest import ROOT, RUN_DATASETS

METHODS = ("resnet18_224", "resnet50_224", "auto_sklearn", "autokeras", "google_automl")
BIB_PATH = ROOT / "report" / "references.bib"


def test_the_literature_table_covers_every_dataset_the_workflow_runs(literature):
    assert sorted(literature.doc["datasets"]) == sorted(RUN_DATASETS)


def test_every_dataset_reports_every_method(literature):
    for dataset in RUN_DATASETS:
        methods = literature.doc["datasets"][dataset]
        assert set(methods) == set(METHODS), dataset


def test_every_value_is_an_auc_or_acc_fraction(literature):
    for dataset in RUN_DATASETS:
        for method, values in literature.doc["datasets"][dataset].items():
            assert set(values) == {"auc", "acc"}, f"{dataset}/{method}"
            for metric, value in values.items():
                assert 0.0 <= value <= 1.0, f"{dataset}/{method}/{metric} = {value}"


def test_the_citation_key_resolves_in_the_bibliography(literature):
    key = literature.doc["citation"]
    text = BIB_PATH.read_text()
    assert re.search(rf"@\w+\{{{re.escape(key)},", text), \
        f"{literature.file} cites {key!r}, which is not a BibTeX key in {BIB_PATH}"
