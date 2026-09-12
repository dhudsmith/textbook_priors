"""The workflow's computations, one entry point per unit of parallel work.

Each stage is a pure function of `config/config.yaml`, its command-line cell and the seed it
derives from them, and writes ONE JSON file: {"manifest": {...}, ...payload}. Nothing here prints
a table; tables and figures are drawn from those files by the report stages.

    sample DATASET --out FILE --arrays FILE     the test sample and the labelled pool (stage 1)
    render-prompts DATASET --out FILE            the two prompt strings for one dataset (stage 2)
    probe DATASET MODEL --out FILE               ten images through the service (stage 2, opt-in)
    score DATASET MODEL SPLIT PROMPT CHUNK --out FILE   one chunk of the fan-out (stage 2)
    collect-scores DATASET --out FILE            one dataset's chunks, gathered (stage 2)
    features DATASET --out FILE --arrays FILE    ImageNet features of the sampled images (stage 3)
    classify DATASET --out FILE --arrays FILE    arms A, B, C, P and the controls (stage 4)

Run with  python -m priors.stages <stage> [args]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import yaml

from . import classify as arms, data, features as pixels, llm, prompts, sample as sampling, score
from .manifest import Run

CONFIG = yaml.safe_load(Path(os.environ.get("PRIORS_CONFIG", "config/config.yaml")).read_text())


def sample(dataset: str, out: str, arrays: str) -> None:
    """Draw one dataset's test sample and labelled pool out of its release file.

    Two outputs, not one: the JSON is the unit of work (the drawn indices, the labels, the counts a
    reader should check) and the images ride in an .npz beside the cache, not in results/, because
    a quarter of a gigabyte of pixels per dataset is an input to later stages rather than a result
    anything reads. `data/cache` is a symlink onto the project filesystem (WORKFLOW.md 11)."""
    spec = CONFIG["sample"]
    release = data.load_release(CONFIG["release"])
    described = release.dataset(dataset)
    path = Path(CONFIG["rawdir"]) / described["file"]

    with Run("sample", dict(dataset=dataset, **spec), seeds=[spec["seed"]]) as run:
        drawn = {"test": sampling.draw(path, "test", spec["test_n"], spec["seed"]),
                 "pool": sampling.draw(path, "train", spec["pool_n"], spec["seed"])}

        Path(arrays).parent.mkdir(parents=True, exist_ok=True)
        np.savez(arrays, **{f"{split}_{key}": drawn[split][key]
                            for split in drawn for key in ("images", "labels", "indices")})

        run.write(out, dict(
            dataset=dataset,
            source_file=str(path),
            md5_224=described["md5_224"],      # recorded from the pinned release, not recomputed
            release_sha256=release.sha256,
            size=CONFIG["size"],
            arrays={"file": arrays,
                    "images": {split: {"shape": list(drawn[split]["images"].shape),
                                       "dtype": str(drawn[split]["images"].dtype)}
                               for split in drawn}},
            splits={split: {k: v for k, v in drawn[split].items() if k != "images"}
                    for split in drawn},
        ))


def render_prompts(dataset: str, out: str) -> None:
    """Turn one dataset's concept bank and label map into both prompt strings.

    No LLM call, no image, no randomness: the output is a deterministic function of the two fixed
    inputs and three config values, and it carries the hash of each input and of each rendered
    prompt so that a score archive can be traced to the exact strings that produced it."""
    size, anchors = CONFIG["size"], CONFIG["vlm"]["prompt"]["anchors"]
    bank = data.load_bank(dataset, CONFIG["conceptdir"])
    release = data.load_release(CONFIG["release"])
    classes = release.class_names(dataset)
    data.check_classes(bank, classes)

    with Run("render_prompts", dict(dataset=dataset, size=size, anchors=anchors)) as run:
        payload = prompts.render(bank, classes, size=size, anchors=anchors)
        run.write(
            out,
            dict(
                dataset=dataset,
                bank_file=bank.file,
                bank_sha256=bank.sha256,
                release_file=release.file,
                release_sha256=release.sha256,
                **payload,
            ),
        )


def probe(dataset: str, model: str, out: str) -> None:
    """Ten images of one dataset through one model, on a compute node, outside `rule all`.

    What it is for (WORKFLOW.md section 9, step 3): that a compute node reaches the service at all,
    that the archive and the manifest carry what they promise - the served model name, the prompt
    hash, the temperature and the reasoning setting - and that a malformed answer is recorded as
    missing rather than guessed. The last is not simulated: one extra call is made with a token
    budget of one, which truncates the reply, and the result shows the content retry firing and the
    answer ending up empty.

    It writes no response archive. `results/score/` is written by the scoring rules alone and is
    fixed from the moment it exists (CLAUDE.md); a probe that wrote into it would make re-scoring
    an accident rather than a decision.
    """
    vlm = CONFIG["vlm"]
    spec = vlm["probe"]
    rendered = json.loads(Path(f"{CONFIG['outdir']}/prompts/{dataset}.json").read_text())
    arrays = np.load(f"{CONFIG['cachedir']}/{dataset}.npz")
    images = arrays["test_images"][: spec["n"]]

    client = llm.Client(model=model, base_url=vlm["base_url"], key_file=vlm["key_file"],
                        temperature=vlm["temperature"], reasoning=vlm["reasoning"],
                        retries=vlm["transport_retries"], timeout=vlm["timeout"])

    params = dict(dataset=dataset, model=model, n=spec["n"], temperature=vlm["temperature"],
                  reasoning=vlm["reasoning"], max_tokens=vlm["max_tokens"], retries=vlm["retries"],
                  concept_prompt_sha256=rendered["prompts"]["concept"]["sha256"],
                  zero_shot_prompt_sha256=rendered["prompts"]["zero_shot"]["sha256"],
                  bank_sha256=rendered["bank_sha256"], key_file=vlm["key_file"])

    with Run("probe", params) as run:
        records = []
        for position, image in enumerate(images):
            url = score.png_data_url(image)
            records.append({
                "position": position,
                "index": int(arrays["test_indices"][position]),
                "label": int(arrays["test_labels"][position]),
                "concept": score.ask_one(client, rendered["prompts"]["concept"], url, "concept",
                                         rendered["concepts"], vlm["max_tokens"], vlm["retries"]),
                "zero_shot": score.ask_one(client, rendered["prompts"]["zero_shot"], url,
                                           "zero_shot", rendered["classes"], vlm["max_tokens"],
                                           vlm["retries"]),
            })

        # The malformed path, against the real service rather than a fixture: one token cannot hold
        # a JSON object, so the reply is truncated, the content retry fires, and the answer is
        # recorded missing. `complete: false` here is the probe passing, not failing.
        truncated = score.ask_one(client, rendered["prompts"]["concept"],
                                  score.png_data_url(images[0]), "concept", rendered["concepts"],
                                  spec["malformed_max_tokens"], vlm["retries"])

        complete = [r for r in records if r["concept"]["complete"]]
        latencies = sorted(reply["elapsed_s"] for r in records for kind in ("concept", "zero_shot")
                           for reply in r[kind]["replies"])
        run.write(out, dict(
            dataset=dataset, model=model,
            served_model=records[0]["concept"]["replies"][0]["served_model"],
            n=len(records),
            calls=len(latencies),
            seconds_per_call={"median": latencies[len(latencies) // 2],
                              "min": latencies[0], "max": latencies[-1],
                              "total": round(sum(latencies), 2)},
            concept_complete=len(complete),
            zero_shot_complete=sum(r["zero_shot"]["complete"] for r in records),
            zero_shot_sums_to_one=sum(bool(r["zero_shot"]["sums_to_one"]) for r in records),
            malformed_check={"requested_max_tokens": spec["malformed_max_tokens"],
                             "content_attempts": truncated["content_attempts"],
                             "complete": truncated["complete"],
                             "recorded_missing": not truncated["complete"],
                             "replies": truncated["replies"]},
            records=records,
        ))


def check_output_name(out, dataset: str, model: str, split: str, prompt: str, chunk: int) -> None:
    """The cell this job was told to compute must be the cell it was told to write.

    Written after a rule wrote one model's answers into the file named for another: the rules that
    generated the fan-out kept their own output paths but shared a single command, and Snakemake
    printed the command it had not run. Nothing downstream could have caught it - the archive was
    internally consistent and only `served_model` disagreed with the file name - so the check lives
    here, before the first call, where a mismatch costs nothing instead of a hundred calls or a
    hypothesis. Cheap, and it fires on any rule that is edited into disagreeing with itself.
    """
    stem = Path(out).stem
    expected = f"{dataset}__{model}__{split}__{prompt}__chunk{int(chunk):02d}"
    if stem != expected:
        raise ValueError(f"this job was told to score {expected} and to write {stem}: refusing")


def score_chunk(dataset: str, model: str, split: str, prompt: str, chunk: int, out: str) -> None:
    """One unit of the scoring fan-out: one dataset, one model, one split, one prompt, one chunk.

    The archive this writes is the study's raw material (WORKFLOW.md section 7). Every image gets
    its parsed answer and every raw reply, including the attempts that failed to parse, and the
    manifest records what produced them: the served model name, the hash of the prompt string that
    was sent, the hash of the bank behind it, the temperature and the reasoning setting. Everything
    downstream is a deterministic function of these files, so nothing below this rule ever needs to
    ask the model again.
    """
    check_output_name(out, dataset, model, split, prompt, chunk)
    vlm = CONFIG["vlm"]
    rendered = json.loads(Path(f"{CONFIG['outdir']}/prompts/{dataset}.json").read_text())
    arrays = np.load(f"{CONFIG['cachedir']}/{dataset}.npz")
    images, labels = arrays[f"{split}_images"], arrays[f"{split}_labels"]
    indices = arrays[f"{split}_indices"]

    spans = score.chunks(len(images), vlm["chunk"])
    if not 0 <= chunk < len(spans):
        raise ValueError(f"chunk {chunk} of {len(spans)} for {dataset}/{split}")
    start, stop = spans[chunk]

    schema = rendered["concepts"] if prompt == "concept" else rendered["classes"]
    client = llm.Client(model=model, base_url=vlm["base_url"], key_file=vlm["key_file"],
                        temperature=vlm["temperature"], reasoning=vlm["reasoning"],
                        retries=vlm["transport_retries"], timeout=vlm["timeout"])

    params = dict(dataset=dataset, model=model, split=split, prompt=prompt, chunk=chunk,
                  images=stop - start, temperature=vlm["temperature"], reasoning=vlm["reasoning"],
                  max_tokens=vlm["max_tokens"], retries=vlm["retries"],
                  prompt_sha256=rendered["prompts"][prompt]["sha256"],
                  bank_sha256=rendered["bank_sha256"], key_file=vlm["key_file"])

    with Run("score", params) as run:
        records = []
        for position in range(start, stop):
            answer = score.ask_one(client, rendered["prompts"][prompt],
                                   score.png_data_url(images[position]), prompt, schema,
                                   vlm["max_tokens"], vlm["retries"])
            records.append({"position": int(position), "index": int(indices[position]),
                            "label": int(labels[position]), **answer})

        latencies = sorted(reply["elapsed_s"] for r in records for reply in r["replies"])
        run.write(out, dict(
            dataset=dataset, model=model, split=split, prompt=prompt, chunk=chunk,
            served_model=records[0]["replies"][0]["served_model"],
            span=[start, stop],
            complete=sum(r["complete"] for r in records),
            incomplete=sum(not r["complete"] for r in records),
            retried=sum(r["content_attempts"] > 1 for r in records),
            calls=len(latencies),
            seconds_per_call={"median": latencies[len(latencies) // 2],
                              "min": latencies[0], "max": latencies[-1],
                              "total": round(sum(latencies), 2)},
            records=records,
        ))


def collect_scores(dataset: str, out: str) -> None:
    """One dataset's chunks, gathered into the table the classify stage reads.

    A gather and nothing else: the answers are carried across as the level tokens the model gave,
    with `null` where it gave none. Turning a level into a number is the estimator's job
    (WORKFLOW.md section 3) and belongs to the stage that also decides what to do about the
    missing ones, not to a rule whose only purpose is to put 45 files into one.
    """
    vlm = CONFIG["vlm"]
    rendered = json.loads(Path(f"{CONFIG['outdir']}/prompts/{dataset}.json").read_text())
    cells, sources = {}, []

    for path in sorted(Path(f"{CONFIG['outdir']}/score").glob(f"{dataset}__*.json")):
        chunk = json.loads(path.read_text())
        key = f"{chunk['model']}__{chunk['split']}__{chunk['prompt']}"
        cell = cells.setdefault(key, {"model": chunk["model"], "split": chunk["split"],
                                      "prompt": chunk["prompt"],
                                      "served_model": chunk["served_model"],
                                      "prompt_sha256": chunk["manifest"]["params"]["prompt_sha256"],
                                      "rows": []})
        field = "answers" if chunk["prompt"] == "concept" else "scores"
        for record in chunk["records"]:
            cell["rows"].append({"position": record["position"], "index": record["index"],
                                 "label": record["label"], "complete": record["complete"],
                                 field: record[field]})
        sources.append(path.name)

    for cell in cells.values():
        cell["rows"].sort(key=lambda r: r["position"])
        cell["n"] = len(cell["rows"])
        cell["incomplete_frac"] = round(sum(not r["complete"] for r in cell["rows"]) / cell["n"], 4)

    with Run("collect_scores", dict(dataset=dataset, cells=len(cells), chunks=len(sources))) as run:
        run.write(out, dict(
            dataset=dataset,
            concepts=[c["id"] for c in rendered["concepts"]],
            classes=rendered["classes"],
            missing_max_frac=CONFIG["classify"]["missing_max_frac"],
            # The gate of WORKFLOW.md section 3: a cell more than 5% incomplete is flagged in the
            # report and kept out of the headline. Recorded per cell here so the report reads it
            # rather than recomputing it.
            cells={key: {**cell, "over_missing_cap":
                         cell["incomplete_frac"] > CONFIG["classify"]["missing_max_frac"]}
                   for key, cell in cells.items()},
            chunk_files=sources,
        ))


def features(dataset: str, out: str, arrays: str) -> None:
    """Frozen ImageNet features of one dataset's sampled images: arm P's half of the comparison.

    Same shape as the sample stage: the JSON is the unit of work and the arrays ride in the cache,
    because 5 MB per dataset of float features is an input to the classifier rather than a result.
    Nothing is trained and nothing is random, so the result carries no seed.
    """
    spec = CONFIG["features"]
    sample_arrays = np.load(f"{CONFIG['cachedir']}/{dataset}.npz")
    threads = int(os.environ.get("OMP_NUM_THREADS", "1"))

    with Run("features", dict(dataset=dataset, **spec, threads=threads)) as run:
        out_arrays, num_params, url = {}, None, None
        for split in ("test", "pool"):
            vectors, num_params, url = pixels.extract(
                sample_arrays[f"{split}_images"], spec["arch"], spec["weights"],
                batch=spec["batch"], threads=threads)
            out_arrays[f"{split}_features"] = vectors

        Path(arrays).parent.mkdir(parents=True, exist_ok=True)
        np.savez(arrays, **out_arrays)
        run.write(out, dict(
            dataset=dataset, arch=spec["arch"], weights=spec["weights"], weights_url=url,
            arrays={"file": arrays,
                    **{k: {"shape": list(v.shape), "dtype": str(v.dtype),
                           # A constant feature column carries no information and would be dropped
                           # by standardisation anyway; counted here so the report can say so.
                           "constant_columns": int((v.std(axis=0) == 0).sum())}
                       for k, v in out_arrays.items()}},
        ))


def classify(dataset: str, out: str, arrays: str) -> None:
    """Every arm's class scores on the shared test sample, for one dataset.

    Nothing is measured here: this stage produces the scores and the evaluate stage turns them into
    AUCs, because the paired bootstrap has to resample the test images once for every arm at the
    same time. The scores ride in an .npz beside the JSON, which is small enough to be a result.
    """
    spec, sample_spec = CONFIG["classify"], CONFIG["sample"]
    curve = CONFIG["curve"]
    rendered = json.loads(Path(f"{CONFIG['outdir']}/prompts/{dataset}.json").read_text())
    gathered = json.loads(Path(f"{CONFIG['outdir']}/scores/{dataset}.json").read_text())
    bank = data.load_bank(dataset, CONFIG["conceptdir"])
    concepts, classes = rendered["concepts"], rendered["classes"]
    primary = CONFIG["vlm"]["primary"]

    sample_arrays = np.load(f"{CONFIG['cachedir']}/{dataset}.npz")
    y_test = np.asarray(sample_arrays["test_labels"]).reshape(-1).astype(int)
    y_pool = np.asarray(sample_arrays["pool_labels"]).reshape(-1).astype(int)
    pixel_arrays = np.load(f"{CONFIG['featuredir']}/{dataset}.npz")

    def cell(model, split, prompt):
        key = f"{model}__{split}__{prompt}"
        if key not in gathered["cells"]:
            raise KeyError(f"{dataset}: {key} is not in the gathered scores")
        return gathered["cells"][key]["rows"]

    out_arrays, index = {}, []
    fingerprints = arms.fingerprint_matrix(classes, bank.classes, concepts)

    with Run("classify", dict(dataset=dataset, **spec, curve_n=curve["n"], seeds=curve["seeds"],
                              primary=primary), seeds=curve["seeds"]) as run:
        # ---- arm A: the zero-shot distribution, read straight out of the archive ----------------
        zero_shot = cell(primary, "test", "zero_shot")
        a_scores = np.array([[row["scores"].get(name) if row["scores"].get(name) is not None else 0.0
                              for name in classes] for row in zero_shot])
        out_arrays["A"] = a_scores
        index.append({"arm": "A", "key": "A", "model": primary, "labels": "none"})

        # ---- arm B: nearest fingerprint, for every model, plus the permutation control ----------
        b_complete = {}
        for model in CONFIG["vlm"]["models"]:
            test_concepts = arms.concept_matrix(cell(model, "test", "concept"), concepts)
            b_complete[model] = float(np.mean(~np.isnan(test_concepts).any(axis=1)))
            out_arrays[f"B__{model}"] = arms.arm_b_scores(test_concepts, fingerprints)
            index.append({"arm": "B", "key": f"B__{model}", "model": model, "labels": "none"})
            for seed in spec["permute"]["seeds"]:
                out_arrays[f"Bperm__{model}__seed{seed}"] = arms.arm_b_scores(
                    test_concepts, arms.permute_fingerprints(fingerprints, seed))
                index.append({"arm": "B_permuted", "key": f"Bperm__{model}__seed{seed}",
                              "model": model, "labels": "none", "permute_seed": seed})

        # ---- arms C and P: the curve, at every n and every seed ---------------------------------
        pool_concepts = arms.concept_matrix(cell(primary, "pool", "concept"), concepts)
        test_concepts = arms.concept_matrix(cell(primary, "test", "concept"), concepts)
        medians = arms.pool_medians(pool_concepts)
        pool_c, pool_flags = arms.impute(pool_concepts, medians)
        test_c, test_flags = arms.impute(test_concepts, medians)
        # The indicator columns have to match between fit and predict, so keep the pool's choice.
        keep = np.isnan(pool_concepts).any(axis=0)
        x_pool_c = np.hstack([pool_c, np.isnan(pool_concepts)[:, keep].astype(float)])
        x_test_c = np.hstack([test_c, np.isnan(test_concepts)[:, keep].astype(float)])
        x_pool_p, x_test_p = pixel_arrays["pool_features"], pixel_arrays["test_features"]

        fits = []
        for seed in curve["seeds"]:
            subsets = arms.nested_subsets(y_pool, curve["n"], len(classes), seed)
            for n, idx in subsets.items():
                for arm, x_pool, x_test in (("C", x_pool_c, x_test_c), ("P", x_pool_p, x_test_p)):
                    got = arms.fit_predict(x_pool[idx], y_pool[idx], x_test, len(classes),
                                           spec["l2_grid"], spec["cv_folds"], seed)
                    key = f"{arm}__n{n}__seed{seed}"
                    out_arrays[key] = got["scores"]
                    index.append({"arm": arm, "key": key, "model": primary if arm == "C" else None,
                                  "labels": int(len(idx)), "n": int(n), "seed": int(seed),
                                  "C": got["C"], "folds": got["folds"]})
                    fits.append({"key": key, "C": got["C"], "folds": got["folds"],
                                 "classes_present": len(got["classes"])})

        # ---- arm C's control: the concept columns shuffled across images ------------------------
        for seed in spec["permute"]["seeds"]:
            shuffled = arms.permute_columns(x_pool_c, seed)
            subsets = arms.nested_subsets(y_pool, curve["n"], len(classes), curve["seeds"][0])
            for n, idx in subsets.items():
                got = arms.fit_predict(shuffled[idx], y_pool[idx], x_test_c, len(classes),
                                       spec["l2_grid"], spec["cv_folds"], curve["seeds"][0])
                key = f"Cperm__n{n}__seed{seed}"
                out_arrays[key] = got["scores"]
                index.append({"arm": "C_permuted", "key": key, "model": primary,
                              "labels": int(len(idx)), "n": int(n), "permute_seed": int(seed)})

        Path(arrays).parent.mkdir(parents=True, exist_ok=True)
        np.savez(arrays, labels=y_test, **out_arrays)
        run.write(out, dict(
            dataset=dataset, classes=classes, n_classes=len(classes),
            arrays={"file": arrays, "keys": sorted(out_arrays)},
            index=index,
            fits=fits,
            complete_frac={model: b_complete[model] for model in b_complete},
            incomplete_over_cap={key: cellspec["over_missing_cap"]
                                 for key, cellspec in gathered["cells"].items()},
            missing_indicator_columns=int(keep.sum()),
            pool_medians={c["id"]: float(m) for c, m in zip(concepts, medians)},
        ))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="stage", required=True)
    p = sub.add_parser("sample"); p.add_argument("dataset")
    p.add_argument("--out", required=True); p.add_argument("--arrays", required=True)
    p = sub.add_parser("render-prompts"); p.add_argument("dataset"); p.add_argument("--out", required=True)
    p = sub.add_parser("probe"); p.add_argument("dataset"); p.add_argument("model")
    p.add_argument("--out", required=True)
    p = sub.add_parser("score"); p.add_argument("dataset"); p.add_argument("model")
    p.add_argument("split"); p.add_argument("prompt"); p.add_argument("chunk", type=int)
    p.add_argument("--out", required=True)
    p = sub.add_parser("collect-scores"); p.add_argument("dataset"); p.add_argument("--out", required=True)
    p = sub.add_parser("features"); p.add_argument("dataset")
    p.add_argument("--out", required=True); p.add_argument("--arrays", required=True)
    p = sub.add_parser("classify"); p.add_argument("dataset")
    p.add_argument("--out", required=True); p.add_argument("--arrays", required=True)
    a = ap.parse_args(argv)
    if a.stage == "sample":
        sample(a.dataset, a.out, a.arrays)
    elif a.stage == "render-prompts":
        render_prompts(a.dataset, a.out)
    elif a.stage == "probe":
        probe(a.dataset, a.model, a.out)
    elif a.stage == "score":
        score_chunk(a.dataset, a.model, a.split, a.prompt, a.chunk, a.out)
    elif a.stage == "collect-scores":
        collect_scores(a.dataset, a.out)
    elif a.stage == "features":
        features(a.dataset, a.out, a.arrays)
    elif a.stage == "classify":
        classify(a.dataset, a.out, a.arrays)
    else:
        raise SystemExit(f"stage {a.stage} not implemented yet")


if __name__ == "__main__":
    main()
