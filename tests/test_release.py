"""The pinned release description against the installed package.

`config/medmnist.yaml` describes a fixed input that no rule re-fetches or re-verifies (WORKFLOW.md
section 4): the six 224-pixel release files, their checksums, their split sizes and their label
maps. Its values were read from `medmnist` 3.0.2 rather than retyped, and this is where that claim
is held to the package. A version bump that moved a label map would otherwise rewrite a prompt and
reorder an AUC column in silence.

Deliberately not checked: the files on disk. Their presence, size and MD5 were verified once,
before the workflow, and are recorded in WORKFLOW.md section 4 as provenance; re-hashing 21 GB in
the smoke tier would be a rule pretending a fixed input is not fixed.
"""
import pytest

from priors import data

from .conftest import INFO, RUN_DATASETS


def test_the_release_describes_every_dataset_the_workflow_runs(config, release):
    assert sorted(release.doc["datasets"]) == sorted(RUN_DATASETS)
    assert release.doc["size"] == config["size"]


def test_the_release_records_the_package_version_it_was_read_from(release):
    import medmnist

    assert release.doc["medmnist_version"] == medmnist.__version__


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_release_matches_the_installed_medmnist(release, dataset):
    described, info = release.dataset(dataset), INFO[dataset]
    assert {str(k): v for k, v in described["label"].items()} == info["label"]
    assert described["medmnist_task"] == info["task"]
    assert described["md5_224"] == info["MD5_224"]
    assert described["n_samples"] == info["n_samples"]
    assert described["n_channels"] == info["n_channels"]
    assert described["file"] == f"{dataset}_224.npz"


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_the_bank_names_exactly_the_release_label_map(banks, release, dataset):
    """The check `render_prompts` makes at the point of use, here across every dataset at once:
    arm B reads the bank's fingerprints and arm A reads the release's names, so a misspelt class
    would give the two arms different label spaces and make the H2 comparison meaningless."""
    data.check_classes(banks[dataset], release.class_names(dataset))


@pytest.mark.parametrize("dataset", RUN_DATASETS)
def test_class_order_comes_from_the_label_index(release, dataset):
    """Bank order is reading order and is not the label order (bloodmnist differs), so every
    artifact indexed by class takes its order from here."""
    label = release.dataset(dataset)["label"]
    assert release.class_names(dataset) == [label[i] for i in sorted(label, key=int)]
