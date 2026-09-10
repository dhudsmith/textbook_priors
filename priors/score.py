"""score: one chunk of one split of one dataset through one model with one prompt (WORKFLOW.md section 7).

The unit of work is a chunk of `vlm.chunk` images of the seeded test sample or labelled pool. Per
image: the 224-pixel PNG and the prompt go out, structured JSON comes back, is archived raw, then
parsed against the bank's scales (concept prompt) or the option list (zero-shot prompt). One retry
on a malformed answer, then the answer is recorded as missing, never guessed. A transport failure
that survives the client's backoff fails the job, so the archive only ever holds completed chunks.
Everything downstream is a deterministic function of these files.
"""
from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from . import data as D
from . import llm
from . import prompts as P
from .manifest import Run


def n_chunks(n: int, chunk: int) -> int:
    return (n + chunk - 1) // chunk


def chunk_bounds(n: int, chunk: int, k: int) -> tuple[int, int]:
    lo = k * chunk
    if lo >= n:
        raise ValueError(f"chunk {k} is past the end of a {n}-image split at chunk size {chunk}")
    return lo, min(n, lo + chunk)


def build_prompt(cfg: dict, ds: str, prompt: str):
    """(system, user, bank, options): options is the zero-shot option list, None for concept."""
    bank = D.load_bank(cfg, ds)
    if prompt == "concept":
        system, user = P.render_concept(bank, anchors=bool(cfg["vlm"]["prompt"]["anchors"]))
        return system, user, bank, None
    if prompt == "zeroshot":
        options = P.zeroshot_options(D.class_names(cfg, ds), (cfg["vlm"].get("zeroshot_names") or {}).get(ds))
        system, user = P.render_zeroshot(bank["modality"], options)
        return system, user, bank, options
    raise ValueError(f"unknown prompt {prompt!r}")


def score_images(client, cfg: dict, model: str, prompt: str, system: str, user: str, bank: dict, options,
                 images: np.ndarray, log=print, sleep=time.sleep) -> list[dict]:
    """Score the given images in order; one record per image with every raw reply archived."""
    vcfg = cfg["vlm"]
    retries = int(vcfg.get("retries", 1))
    records = []
    for i, img in enumerate(images):
        req = llm.chat_request(model, system, user, llm.image_data_url(img), vcfg)
        raws, calls, best = [], [], None
        for attempt in range(retries + 1):
            call = llm.complete(client, req, vcfg, sleep=sleep)
            text = call.pop("text")
            raws.append({"content": call.pop("content"), "reasoning_content": call.pop("reasoning_content")})
            calls.append(call)
            if prompt == "concept":
                answers, missing = P.parse_concept(text, bank)
                cand = {"answers": answers, "n_missing": int(missing)}
                if best is None or missing < best["n_missing"]:
                    best = cand
                if missing == 0:
                    break
            else:
                dist = P.parse_zeroshot(text, options)
                cand = {"distribution": None if dist is None else dist.tolist(), "n_missing": int(dist is None)}
                if best is None or cand["n_missing"] < best["n_missing"]:
                    best = cand
                if dist is not None:
                    break
        rec = {"i": i, **best, "raw": raws, "attempts": len(raws), "calls": calls,
               "served_model": calls[-1].get("served_model")}
        records.append(rec)
        if (i + 1) % 10 == 0 or i + 1 == len(images):
            log(f"  {i + 1}/{len(images)} images, {sum(len(r['raw']) for r in records)} calls, "
                f"{sum(r['n_missing'] > 0 for r in records)} incomplete", flush=True)
    return records


def score_chunk(cfg: dict, ds: str, model: str, split: str, prompt: str, k: int, out, limit: int | None = None,
                client=None, log=print, sleep=time.sleep, extra_manifest: dict | None = None) -> None:
    """One archive file. `limit` truncates the chunk (the probe only); such a file must never be
    written under results/score/, which is why the probe rule writes elsewhere."""
    vcfg = cfg["vlm"]
    sample = D.load_sample(cfg, ds)
    images = sample[f"{split}_images"]
    index = sample[f"{split}_idx"]
    lo, hi = chunk_bounds(len(images), int(vcfg["chunk"]), k)
    if limit is not None:
        hi = min(hi, lo + int(limit))
    system, user, bank, options = build_prompt(cfg, ds, prompt)
    client = client or llm.make_client(vcfg)
    params = dict(dataset=ds, model=model, split=split, prompt=prompt, chunk=k, lo=lo, hi=hi,
                  temperature=vcfg["temperature"], reasoning=vcfg["reasoning"],
                  reasoning_extra_body=vcfg.get("reasoning_extra_body"), json_mode=vcfg.get("json_mode"),
                  max_tokens=vcfg.get("max_tokens"), anchors=vcfg["prompt"]["anchors"], retries=vcfg["retries"])
    with Run("score", params) as run:
        t0 = time.time()
        log(f"scoring {ds} {split}[{lo}:{hi}] with {model} / {prompt}", flush=True)
        records = score_images(client, cfg, model, prompt, system, user, bank, options, images[lo:hi], log, sleep)
        for r, j in zip(records, range(lo, hi)):
            r["i"] = j
            r["split_index"] = int(index[j])
        wall = time.time() - t0
        calls = sum(r["attempts"] for r in records)
        served = sorted({r["served_model"] for r in records if r["served_model"]})
        payload = {
            "dataset": ds, "model": model, "split": split, "prompt": prompt, "chunk": k, "lo": lo, "hi": hi,
            "n_images": len(records), "n_incomplete": int(sum(r["n_missing"] > 0 for r in records)),
            "n_missing_total": int(sum(r["n_missing"] for r in records)), "calls": calls,
            "wall_s": round(wall, 1), "calls_per_min": round(60 * calls / max(wall, 1e-9), 2),
            "prompt_text": {"system": system, "user": user}, "options": options,
            "concept_ids": D.concept_ids(bank) if prompt == "concept" else None,
            "images": records,
        }
        extra = {"served_model": served, "prompt_hash": P.prompt_hash(system, user),
                 "bank_hash": D.file_hash(D.bank_path(cfg, ds)), "base_url": vcfg["base_url"]}
        extra.update(extra_manifest or {})
        run.write(out, payload, extra=extra)
    log(f"wrote {out}: {calls} calls in {wall:.0f} s", flush=True)


def probe(cfg: dict, out, log=print) -> None:
    """The opt-in ten-image probe (WORKFLOW.md section 9, step 4): does a compute node reach the
    service, are the configured model names served, is the archive right, is a malformed reply
    handled. Written under results/score_probe/, never into the archive."""
    vcfg = cfg["vlm"]
    client = llm.make_client(vcfg)
    served = llm.list_models(client)
    missing = [m for m in vcfg["models"] if m not in served]
    log(f"service lists {len(served)} models: {served}")
    if missing:
        raise SystemExit(f"configured models not served: {missing}; served: {served}")
    pr = vcfg["probe"]
    score_chunk(cfg, pr["dataset"], vcfg["primary"], "test", "concept", 0, out, limit=int(pr["n"]),
                client=client, log=log, extra_manifest={"probe": True, "models_served": served})
