"""features: ImageNet ResNet-18 penultimate features for the sampled images (arm P, WORKFLOW.md section 3).

The label-matched pixel baseline is transfer learning without the textbook: the 512-d global
average-pooled features of torchvision's ResNet-18 (IMAGENET1K_V1), frozen, on the same seeded
test sample and labelled pool the VLM scores. Greyscale is replicated to three channels and
ImageNet normalisation applied. Torch is imported here and in train.py only.
"""
from __future__ import annotations

import time

from pathlib import Path

import numpy as np

from . import data as D
from .manifest import Run

IMAGENET_MEAN = (0.485, 0.456, 0.406)
IMAGENET_STD = (0.229, 0.224, 0.225)
WEIGHTS = {"imagenet1k_v1": "IMAGENET1K_V1"}


def to_tensor(imgs: np.ndarray, device):
    """uint8 (n, H, W) or (n, H, W, 3) -> float (n, 3, H, W), ImageNet-normalised, on device."""
    import torch
    x = torch.from_numpy(np.ascontiguousarray(imgs)).to(device)
    if x.ndim == 3:
        x = x.unsqueeze(-1).expand(-1, -1, -1, 3)
    x = x.permute(0, 3, 1, 2).float().div_(255.0)
    mean = torch.tensor(IMAGENET_MEAN, device=device).view(1, 3, 1, 1)
    std = torch.tensor(IMAGENET_STD, device=device).view(1, 3, 1, 1)
    return (x - mean) / std


def backbone(weights: str, device):
    import torch
    import torchvision
    w = getattr(torchvision.models.ResNet18_Weights, WEIGHTS[weights])
    m = torchvision.models.resnet18(weights=w)
    m.fc = torch.nn.Identity()           # the 512-d penultimate layer is now the output
    return m.eval().to(device), w


def extract(model, imgs: np.ndarray, batch: int, device) -> np.ndarray:
    import torch
    out = []
    with torch.no_grad():
        for i in range(0, len(imgs), batch):
            out.append(model(to_tensor(imgs[i:i + batch], device)).float().cpu().numpy())
    return np.concatenate(out).astype(np.float32)


def features_dataset(cfg: dict, ds: str, out, log=print) -> None:
    import torch
    fcfg = cfg["features"]
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    sample = D.load_sample(cfg, ds)
    with Run("features", dict(dataset=ds, **{k: fcfg[k] for k in ("arch", "weights", "layer")})) as run:
        model, w = backbone(fcfg["weights"], device)
        t0 = time.time()
        feats = {s: extract(model, sample[f"{s}_images"], int(fcfg["batch"]), device) for s in ("test", "pool")}
        wall = time.time() - t0
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        npz = str(out)[:-5] + ".npz"
        np.savez(npz, test=feats["test"], pool=feats["pool"], test_idx=sample["test_idx"], pool_idx=sample["pool_idx"])
        n = sum(len(v) for v in feats.values())
        run.write(out, dict(dataset=ds, arrays=npz, dim=int(feats["test"].shape[1]),
                            n_test=int(len(feats["test"])), n_pool=int(len(feats["pool"])),
                            device=str(device), weights_url=str(w.url), images_per_s=round(n / max(wall, 1e-9), 1),
                            feature_means_first5=feats["test"].mean(0)[:5].tolist()))
    log(f"{ds}: {n} images at {n / max(wall, 1e-9):.0f} img/s on {device}; wrote {out}")
