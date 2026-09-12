"""features: the pixel baseline's representation, from a frozen ImageNet encoder.

Arm P is the fair comparison for arm C (WORKFLOW.md section 3): a vision-language model is an
enormous pretrained model, so the pixel baseline is also pretrained - the same classifier, the same
regularisation search and the same labelled subsets, with ImageNet features in place of concept
scores. Only the features differ, which is what makes the curve a statement about the features.

The encoder is frozen and nothing here is trained. Preprocessing is deliberately numpy rather than
torchvision transforms, so that the smoke tier can check it without torch in its environment.
"""
from __future__ import annotations

import numpy as np

# ImageNet's channel statistics, the ones the pretrained weights were fitted under.
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)


def preprocess(images: np.ndarray) -> np.ndarray:
    """Sampled uint8 images -> the float NCHW batch the encoder expects.

    Two decisions worth stating. Greyscale images are repeated across three channels, because the
    encoder has three and the alternative - summing the first-layer filters - changes the features
    to save nothing. And the weights' own transform is NOT applied: it resizes to 256 and crops back
    to 224, which would throw away the frame edge, and the release is already 224 at the size the
    encoder wants (WORKFLOW.md section 4). Only the normalisation is kept.
    """
    array = np.asarray(images)
    if array.ndim == 3:                                  # N, H, W  -> greyscale
        array = np.repeat(array[..., None], 3, axis=3)
    if array.ndim != 4 or array.shape[3] != 3:
        raise ValueError(f"cannot preprocess images of shape {np.asarray(images).shape}")
    scaled = array.astype(np.float32) / 255.0
    normalised = (scaled - MEAN) / STD
    return np.ascontiguousarray(normalised.transpose(0, 3, 1, 2))


def extract(images: np.ndarray, arch: str, weights: str, batch: int = 64, threads: int = 1):
    """The penultimate-layer features of every image, as a (N, 512) array for ResNet-18.

    Torch is imported here rather than at module scope so that everything above stays importable in
    the light environment, where the smoke tier runs.
    """
    import torch
    import torchvision

    torch.set_num_threads(max(1, int(threads)))
    if arch != "resnet18":
        raise ValueError(f"only resnet18 is wired up, not {arch!r}")
    enum = torchvision.models.ResNet18_Weights[weights.upper()]
    model = torchvision.models.resnet18(weights=enum)
    model.fc = torch.nn.Identity()            # the penultimate layer is what arm P uses
    model.eval()

    out = []
    with torch.inference_mode():
        for start in range(0, len(images), batch):
            chunk = preprocess(images[start:start + batch])
            out.append(model(torch.from_numpy(chunk)).numpy())
    return np.concatenate(out).astype(np.float32), str(enum.meta.get("num_params", "")), enum.url
