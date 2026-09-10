"""train: arm E, ResNet-18 from scratch on the official splits (WORKFLOW.md section 3).

The fully supervised ceiling and the number reconciled against the published MedMNIST table, so
the recipe is the paper's: cross-entropy (BCE-with-logits for chestmnist), batch 128, Adam at
0.001 for 100 epochs with the rate multiplied by 0.1 after epochs 50 and 75, best epoch by
validation AUC, no augmentation, inputs scaled to [-1, 1] (Normalize(0.5, 0.5)). At 28 the model
is the MedMNIST ResNet-18 variant (3x3 stem, no max-pool, n_channels in); at 224 torchvision's
resnet18 with greyscale replicated to three channels, as the benchmark's --as_rgb does. Every
split is held in RAM as uint8 and normalised on the device, so the loader is a permutation.

Arm E is evaluated twice: on the full official test split for the reconciliation, and on the
shared test sample (by index) for the paired comparisons.
"""
from __future__ import annotations

import copy
import time

from pathlib import Path

import numpy as np

from . import data as D
from .manifest import Run


def make_model(size: int, in_channels: int, n_classes: int):
    if int(size) == 28:
        return ResNetSmall(in_channels, n_classes)
    import torchvision
    from torch import nn
    m = torchvision.models.resnet18(weights=None, num_classes=n_classes)
    if in_channels != 3:
        m.conv1 = nn.Conv2d(in_channels, 64, kernel_size=7, stride=2, padding=3, bias=False)
    return m


def _torch_modules():
    import torch
    from torch import nn
    import torch.nn.functional as F

    class BasicBlock(nn.Module):
        expansion = 1

        def __init__(self, in_planes, planes, stride=1):
            super().__init__()
            self.conv1 = nn.Conv2d(in_planes, planes, 3, stride, 1, bias=False)
            self.bn1 = nn.BatchNorm2d(planes)
            self.conv2 = nn.Conv2d(planes, planes, 3, 1, 1, bias=False)
            self.bn2 = nn.BatchNorm2d(planes)
            self.shortcut = nn.Sequential()
            if stride != 1 or in_planes != planes:
                self.shortcut = nn.Sequential(nn.Conv2d(in_planes, planes, 1, stride, bias=False), nn.BatchNorm2d(planes))

        def forward(self, x):
            out = F.relu(self.bn1(self.conv1(x)))
            out = self.bn2(self.conv2(out))
            return F.relu(out + self.shortcut(x))

    class ResNet(nn.Module):
        """The MedMNIST/experiments ResNet-18 for 28-pixel inputs: 3x3 stem, no max-pool."""

        def __init__(self, in_channels, num_classes, blocks=(2, 2, 2, 2)):
            super().__init__()
            self.in_planes = 64
            self.conv1 = nn.Conv2d(in_channels, 64, 3, 1, 1, bias=False)
            self.bn1 = nn.BatchNorm2d(64)
            self.layer1 = self._make(64, blocks[0], 1)
            self.layer2 = self._make(128, blocks[1], 2)
            self.layer3 = self._make(256, blocks[2], 2)
            self.layer4 = self._make(512, blocks[3], 2)
            self.avgpool = nn.AdaptiveAvgPool2d((1, 1))
            self.linear = nn.Linear(512, num_classes)

        def _make(self, planes, n, stride):
            layers = []
            for s in [stride] + [1] * (n - 1):
                layers.append(BasicBlock(self.in_planes, planes, s))
                self.in_planes = planes
            return nn.Sequential(*layers)

        def forward(self, x):
            out = F.relu(self.bn1(self.conv1(x)))
            out = self.layer4(self.layer3(self.layer2(self.layer1(out))))
            out = self.avgpool(out).flatten(1)
            return self.linear(out)

    return ResNet


def ResNetSmall(in_channels, n_classes):
    return _torch_modules()(in_channels, n_classes)


def to_input(x_uint8, device, size: int):
    """uint8 (b, H, W[, C]) -> float (b, C', H, W) in [-1, 1]; greyscale to 3 channels at 224."""
    x = x_uint8.to(device, non_blocking=True)
    if x.ndim == 3:
        x = x.unsqueeze(1)
        if int(size) != 28:
            x = x.expand(-1, 3, -1, -1)
    else:
        x = x.permute(0, 3, 1, 2)
    return (x.float() / 255.0 - 0.5) / 0.5


def predict(model, x_uint8, task: str, device, size: int, batch: int = 512) -> np.ndarray:
    """Class probabilities: softmax for single-label tasks, sigmoid per finding for multi-label."""
    import torch
    model.eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(x_uint8), batch):
            logits = model(to_input(x_uint8[i:i + batch], device, size)).float()
            p = torch.sigmoid(logits) if task == "multi-label, binary-class" else torch.softmax(logits, 1)
            out.append(p.cpu().numpy())
    return np.concatenate(out)


def train_arrays(xtr, ytr, xva, yva, *, task: str, n_classes: int, size: int, tcfg: dict, seed: int,
                 device, log=print, epochs: int | None = None):
    """The recipe on arrays already in RAM (torch uint8 images, labels as medmnist stores them).
    Returns (best model, history). `epochs` overrides the config for the smoke test only."""
    import torch
    from medmnist.evaluator import getAUC
    torch.manual_seed(seed)
    np.random.seed(seed)
    torch.backends.cudnn.deterministic = bool(tcfg.get("deterministic", False))
    torch.backends.cudnn.benchmark = not torch.backends.cudnn.deterministic
    in_ch = 3 if (xtr.ndim == 4 or int(size) != 28) else 1
    model = make_model(size, in_ch, n_classes).to(device)
    multilabel = task == "multi-label, binary-class"
    crit = torch.nn.BCEWithLogitsLoss() if multilabel else torch.nn.CrossEntropyLoss()
    opt = torch.optim.Adam(model.parameters(), lr=float(tcfg["lr"]))
    n_epochs = int(epochs or tcfg["epochs"])
    milestones = [int(round(m * n_epochs / int(tcfg["epochs"]))) for m in tcfg["milestones"]]
    sched = torch.optim.lr_scheduler.MultiStepLR(opt, milestones=milestones, gamma=float(tcfg["gamma"]))
    scaler_on = bool(tcfg.get("amp", False)) and device.type == "cuda"
    ytr_t = torch.as_tensor(np.asarray(ytr)).float() if multilabel else torch.as_tensor(np.asarray(ytr).reshape(-1)).long()
    yva_np = np.asarray(yva)
    g = torch.Generator().manual_seed(seed)
    batch = int(tcfg["batch"])
    hist = {"train_loss": [], "val_auc": [], "epoch_s": []}
    best_auc, best_state, best_epoch = -1.0, None, -1
    for ep in range(n_epochs):
        t0 = time.time()
        model.train()
        perm = torch.randperm(len(xtr), generator=g)
        tot, cnt = 0.0, 0
        for i in range(0, len(perm), batch):
            idx = perm[i:i + batch]
            x = to_input(xtr[idx], device, size)
            y = ytr_t[idx].to(device)
            opt.zero_grad(set_to_none=True)
            with torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=scaler_on):
                loss = crit(model(x).float(), y)
            loss.backward()
            opt.step()
            tot += float(loss) * len(idx)
            cnt += len(idx)
        sched.step()
        pva = predict(model, xva, task, device, size)
        auc = float(getAUC(yva_np, pva, task))
        hist["train_loss"].append(tot / max(cnt, 1))
        hist["val_auc"].append(auc)
        hist["epoch_s"].append(round(time.time() - t0, 1))
        if auc > best_auc:
            best_auc, best_epoch = auc, ep
            best_state = copy.deepcopy(model.state_dict())
        log(f"epoch {ep + 1}/{n_epochs} loss {tot / max(cnt, 1):.4f} val_auc {auc:.4f} "
            f"lr {opt.param_groups[0]['lr']:.2e} {hist['epoch_s'][-1]}s", flush=True)
    model.load_state_dict(best_state)
    hist.update(best_epoch=best_epoch, best_val_auc=best_auc, milestones=milestones)
    return model, hist


def train_dataset(cfg: dict, ds: str, size: int, seed: int, out, log=print) -> None:
    import torch
    from medmnist.evaluator import getACC, getAUC
    tcfg = cfg["train"]
    task = D.task_string(cfg, ds)
    K = D.n_classes(cfg, ds)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log(f"{ds} at {size}, seed {seed}, device {device}", flush=True)
    t0 = time.time()
    arr = {f"{s}_{w}": np.load(D.cache_dir(cfg, ds, size) / f"{s}_{w}.npy") for s in D.SPLITS for w in ("images", "labels")}
    x = {s: torch.from_numpy(arr[f"{s}_images"]) for s in D.SPLITS}
    log(f"loaded {sum(v.numel() for v in x.values()) / 1e9:.1f} GB of uint8 in {time.time() - t0:.0f} s", flush=True)
    sample = D.load_sample(cfg, ds)
    params = dict(dataset=ds, size=int(size), seed=int(seed),
                  **{k: tcfg[k] for k in ("arch", "pretrained", "epochs", "batch", "lr", "milestones", "gamma", "select_on", "amp")})
    with Run("train", params, seeds=[int(seed)], deterministic=bool(tcfg.get("deterministic", False))) as run:
        t1 = time.time()
        model, hist = train_arrays(x["train"], arr["train_labels"], x["val"], arr["val_labels"], task=task,
                                   n_classes=K, size=int(size), tcfg=tcfg, seed=int(seed), device=device, log=log)
        train_s = time.time() - t1
        p_test = predict(model, x["test"], task, device, size)
        p_sample = p_test[sample["test_idx"]]
        y_test, y_sample = arr["test_labels"], arr["test_labels"][sample["test_idx"]]
        metrics = {"test_full": {"auc": float(getAUC(y_test, p_test, task)), "acc": float(getACC(y_test, p_test, task)), "n": int(len(y_test))},
                   "sample": {"auc": float(getAUC(y_sample, p_sample, task)), "acc": float(getACC(y_sample, p_sample, task)), "n": int(len(y_sample))}}
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        npz = str(out)[:-5] + ".npz"
        np.savez(npz, test_scores=p_test.astype(np.float32), sample_scores=p_sample.astype(np.float32), test_idx=sample["test_idx"])
        if tcfg.get("save_weights"):
            torch.save(model.state_dict(), str(out)[:-5] + ".pt")
        n_img = len(x["train"]) * len(hist["train_loss"])
        run.write(out, dict(dataset=ds, size=int(size), seed=int(seed), task=task, arrays=npz, metrics=metrics,
                            history=hist, device=str(device), gpu=torch.cuda.get_device_name(0) if device.type == "cuda" else None,
                            train_s=round(train_s, 1), images_per_s=round(n_img / max(train_s, 1e-9), 1)))
    log(f"{ds}@{size} seed {seed}: best epoch {hist['best_epoch'] + 1}, test AUC {metrics['test_full']['auc']:.4f} "
        f"ACC {metrics['test_full']['acc']:.4f}; sample AUC {metrics['sample']['auc']:.4f}", flush=True)
