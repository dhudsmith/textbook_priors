"""data: the workflow's fixed inputs, read and hashed in one place.

Two inputs were completed before the workflow runs and no rule refetches or re-verifies them
(WORKFLOW.md section 4): the concept bank under `data/concepts/`, and the pinned MedMNIST v2
release, whose file names, checksums, split sizes and label maps are described by
`config/medmnist.yaml`. Both are read here so that every rule depending on one records the same
hash for the same bytes, and so the smoke tier validates the object the rules actually use rather
than its own second reading of the file.

Nothing here validates the bank's schema. That is the smoke tier's job (CONCEPT_BANK.md lists the
rules); a loader that silently repaired a bank would hide exactly what the tests exist to catch.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

import yaml


def sha256_file(path) -> str:
    """Hash a fixed input, so a result's manifest names the bytes it was computed from."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def one_line(text: str) -> str:
    """Bank prose as one line. YAML folds a block scalar's newlines to spaces; the indentation of
    the source file must not reach the prompt, because the prompt string is hashed and compared."""
    return " ".join(str(text).split())


@dataclass(frozen=True)
class Bank:
    """One dataset's concept bank: the parsed document, plus the file it came from and its hash."""

    dataset: str
    file: str
    sha256: str
    doc: dict

    @property
    def modality(self) -> str:
        return one_line(self.doc["modality"])

    @property
    def concepts(self) -> list[dict]:
        """The concepts in bank order. That order fixes the prompt's question order, the feature
        columns of arms C and P, and the fingerprint comparison of arm B."""
        return list(self.doc["concepts"])

    @property
    def classes(self) -> dict:
        """Class name -> {fingerprint, sources}. Bank order, which is NOT the label-index order;
        anything indexed by class takes its order from the release (see Release.class_names)."""
        return dict(self.doc["classes"])


@dataclass(frozen=True)
class Release:
    """The pinned release description, `config/medmnist.yaml`, with the file's hash."""

    file: str
    sha256: str
    doc: dict

    def dataset(self, name: str) -> dict:
        return self.doc["datasets"][name]

    def class_names(self, name: str) -> list[str]:
        """The class names in label-index order: the order every score vector, every zero-shot
        distribution and every AUC column uses. Taken from the release rather than from the bank,
        whose `classes` mapping is written in whatever order reads best (bloodmnist differs)."""
        label = self.dataset(name)["label"]
        return [label[i] for i in sorted(label, key=int)]


def load_bank(dataset: str, conceptdir) -> Bank:
    path = Path(conceptdir) / f"{dataset}.yaml"
    doc = yaml.safe_load(path.read_text())
    if doc.get("dataset") != dataset:
        raise ValueError(f"{path} declares dataset {doc.get('dataset')!r}, not {dataset!r}")
    return Bank(dataset=dataset, file=str(path), sha256=sha256_file(path), doc=doc)


def load_release(path) -> Release:
    path = Path(path)
    return Release(file=str(path), sha256=sha256_file(path), doc=yaml.safe_load(path.read_text()))


def check_classes(bank: Bank, classes: list[str]) -> None:
    """The bank names exactly the release's classes, no more and no fewer.

    A precondition of every artifact that carries both, checked wherever one is built: arm B reads
    the bank's fingerprints and arm A reads the release's names, so a bank that misspells a class
    would silently give the two arms different label spaces and make the H2 comparison meaningless.
    The smoke tier checks this across all six datasets against the installed `medmnist` package;
    this is the same check at the point of use, where it fails the one job that got it wrong."""
    missing = [c for c in classes if c not in bank.classes]
    extra = [c for c in bank.classes if c not in classes]
    if missing or extra:
        raise ValueError(
            f"{bank.file} does not match the release label map for {bank.dataset}: "
            f"missing {missing}, unexpected {extra}"
        )
