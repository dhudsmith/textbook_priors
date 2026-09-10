"""The torch tier's checks: model shapes at 28 and 224, the input mapping, two epochs of the recipe
on random data, and the feature extractor. Run by rule smoke_torch in envs/priors_torch.yml."""
import numpy as np
import pytest

torch = pytest.importorskip("torch")

from priors import features as F   # noqa: E402
from priors import train as T      # noqa: E402


def test_small_resnet_shapes():
    m = T.ResNetSmall(1, 5)
    assert m(torch.zeros(2, 1, 28, 28)).shape == (2, 5)
    m3 = T.make_model(28, 3, 9)
    assert m3(torch.zeros(2, 3, 28, 28)).shape == (2, 9)
    assert not hasattr(m3, "maxpool")


def test_torchvision_resnet_at_224_accepts_three_channels():
    m = T.make_model(224, 3, 7)
    assert m(torch.zeros(1, 3, 64, 64)).shape == (1, 7)          # any size >= 32 works; 64 keeps the test fast
    assert isinstance(m.fc, torch.nn.Linear) and m.fc.out_features == 7


def test_to_input_range_and_channels():
    grey = torch.randint(0, 256, (2, 28, 28), dtype=torch.uint8)
    x = T.to_input(grey, torch.device("cpu"), 28)
    assert x.shape == (2, 1, 28, 28) and x.min() >= -1 and x.max() <= 1
    x224 = T.to_input(grey, torch.device("cpu"), 224)
    assert x224.shape == (2, 3, 28, 28) and torch.equal(x224[:, 0], x224[:, 2])
    rgb = torch.randint(0, 256, (2, 28, 28, 3), dtype=torch.uint8)
    assert T.to_input(rgb, torch.device("cpu"), 28).shape == (2, 3, 28, 28)
    assert torch.isclose(T.to_input(torch.full((1, 4, 4), 255, dtype=torch.uint8), torch.device("cpu"), 28).max(), torch.tensor(1.0))


@pytest.mark.parametrize("task", ["multi-class", "multi-label, binary-class"])
def test_two_epochs_of_the_recipe_run_and_select_the_best(cfg, task):
    pytest.importorskip("medmnist")
    rng = np.random.default_rng(0)
    n, K = 64, 3
    x = torch.from_numpy(rng.integers(0, 256, (n, 28, 28), dtype=np.uint8))
    if task == "multi-class":
        y = rng.integers(0, K, (n, 1))
        yv = rng.integers(0, K, (16, 1))
    else:
        y = rng.integers(0, 2, (n, K))
        yv = rng.integers(0, 2, (16, K))
    xv = torch.from_numpy(rng.integers(0, 256, (16, 28, 28), dtype=np.uint8))
    tcfg = dict(cfg["train"], batch=16, epochs=100)
    model, hist = T.train_arrays(x, y, xv, yv, task=task, n_classes=K, size=28, tcfg=tcfg, seed=0,
                                 device=torch.device("cpu"), log=lambda *a, **k: None, epochs=2)
    assert len(hist["train_loss"]) == 2 and len(hist["val_auc"]) == 2 and hist["best_epoch"] in (0, 1)
    assert hist["best_val_auc"] == max(hist["val_auc"])
    P = T.predict(model, xv, task, torch.device("cpu"), 28)
    assert P.shape == (16, K) and (P >= 0).all() and (P <= 1).all()
    if task == "multi-class":
        assert np.allclose(P.sum(1), 1, atol=1e-5)


def test_feature_extractor_dimension_and_normalisation():
    import torchvision
    m = torchvision.models.resnet18(weights=None)
    m.fc = torch.nn.Identity()
    m.eval()
    imgs = np.random.default_rng(0).integers(0, 256, (5, 64, 64), dtype=np.uint8)
    feats = F.extract(m, imgs, batch=2, device=torch.device("cpu"))
    assert feats.shape == (5, 512) and feats.dtype == np.float32
    x = F.to_tensor(np.zeros((1, 8, 8), np.uint8), torch.device("cpu"))
    assert x.shape == (1, 3, 8, 8)
    assert torch.allclose(x[0, :, 0, 0], -torch.tensor(F.IMAGENET_MEAN) / torch.tensor(F.IMAGENET_STD))
