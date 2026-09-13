"""The workflow's computations, one entry point per unit of parallel work.

Each stage is a pure function of `config/config.yaml`, its command-line cell and the seed it
derives from them, and writes ONE JSON file: {"manifest": {...}, ...payload}. Nothing here prints
a table; tables and figures are drawn from those files by the report stages.

    sample DATASET --out FILE --arrays FILE     the test sample and the labelled pool (stage 1)
    render-prompts DATASET --out FILE            the three prompt strings for one dataset (stage 2)
    probe DATASET MODEL --out FILE               ten images through the service (stage 2, opt-in)
    score DATASET MODEL SPLIT PROMPT CHUNK --out FILE   one chunk of the fan-out (stage 2)
    collect-scores DATASET --out FILE            one dataset's chunks, gathered (stage 2)
    features DATASET --out FILE --arrays FILE    ImageNet features of the sampled images (stage 3)
    embed DATASET --out FILE --arrays FILE       the answers and the bank, as prose, embedded (stage 3)
    classify DATASET --out FILE --arrays FILE    arms A, B, C, D, P and the controls (stage 4)
    evaluate DATASET --out FILE                  AUCs, the paired bootstrap and n_B (stage 5)
    evaluate-across --out FILE                   the sign tests, the ladder, the verdicts (stage 5)
    tables --dest DIR                            every table and number macro the report states
    figures --dest DIR                           the three figures

Run with  python -m priors.stages <stage> [args]
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import numpy as np
import yaml

from . import data
from .manifest import Run

# Only `data` (yaml) and `manifest` are imported at module scope. Every other module is imported
# inside the stage that needs it, because the stages do not share an environment: the features job
# runs in envs/priors_torch.yml, which has torch and neither sklearn nor openai, and a driver that
# imported every module at the top made that job fail on `import sklearn` before it did anything.
# One entry point per unit of work does not mean one dependency set for all of them.

CONFIG = yaml.safe_load(Path(os.environ.get("PRIORS_CONFIG", "config/config.yaml")).read_text())


def sample(dataset: str, out: str, arrays: str) -> None:
    """Draw one dataset's test sample and labelled pool out of its release file.

    Two outputs, not one: the JSON is the unit of work (the drawn indices, the labels, the counts a
    reader should check) and the images ride in an .npz beside the cache, not in results/, because
    a quarter of a gigabyte of pixels per dataset is an input to later stages rather than a result
    anything reads. `data/cache` is a symlink onto the project filesystem (WORKFLOW.md 11)."""
    from . import sample as sampling
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
    """Turn one dataset's concept bank and label map into all three prompt strings.

    No LLM call, no image, no randomness: the output is a deterministic function of the two fixed
    inputs and three config values, and it carries the hash of each input and of each rendered
    prompt so that a score archive can be traced to the exact strings that produced it."""
    from . import prompts
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
    from . import llm, score
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
    from . import llm, score
    check_output_name(out, dataset, model, split, prompt, chunk)
    vlm = CONFIG["vlm"]
    rendered = json.loads(Path(f"{CONFIG['outdir']}/prompts/{dataset}.json").read_text())
    arrays = np.load(f"{CONFIG['cachedir']}/{dataset}.npz")
    images, labels = arrays[f"{split}_images"], arrays[f"{split}_labels"]
    indices = arrays[f"{split}_indices"]

    # `model` is the name in the output path, which for H4 is a *reader*: a model plus a reasoning
    # effort (WORKFLOW.md section 2). Resolving it here rather than in the rule keeps the archive's
    # file name and the call that filled it the same decision - the lesson of the generated-rule
    # bug, applied to a second thing a rule can disagree with its own output about.
    reader = vlm.get("readers", {}).get(model)
    served = reader["model"] if reader else model
    effort = reader["effort"] if reader else vlm["reasoning"]
    api = reader.get("api", "local") if reader else "local"
    tier = reader.get("service_tier") if reader else None
    # A reader may have to run at the served default: the gateway's reasoning models reject any
    # temperature at all. `temperature: null` in config means omit the field, and the manifest then
    # records null rather than a number that was never sent.
    temperature = reader.get("temperature", vlm["temperature"]) if reader else vlm["temperature"]
    budget = reader["max_tokens"] if reader else vlm["max_tokens"]
    # A reader reads a prefix of the split, not all of it: the images every other reader was already
    # scored on, so the comparison is paired and the existing archives are subset rather than bought
    # again. `min` because a subsample longer than the split would silently score fewer.
    scored = min(reader["subsample"], len(images)) if reader else len(images)

    spans = score.chunks(scored, vlm["chunk"])
    if not 0 <= chunk < len(spans):
        raise ValueError(f"chunk {chunk} of {len(spans)} for {dataset}/{split}")
    start, stop = spans[chunk]

    schema = rendered["concepts"] if prompt == "concept" else rendered["classes"]
    client = llm.Client(model=served, base_url=vlm["base_url"], key_file=vlm["key_file"],
                        temperature=temperature, reasoning=effort, api=api,
                        service_tier=tier,
                        retries=vlm["transport_retries"], timeout=vlm["timeout"])

    params = dict(dataset=dataset, model=model, split=split, prompt=prompt, chunk=chunk,
                  images=stop - start, temperature=temperature, reasoning=effort,
                  served_name=served, api=api, service_tier=tier, subsample=scored,
                  max_tokens=budget, retries=vlm["retries"],
                  prompt_sha256=rendered["prompts"][prompt]["sha256"],
                  bank_sha256=rendered["bank_sha256"], key_file=vlm["key_file"])

    with Run("score", params) as run:
        records = []
        for position in range(start, stop):
            answer = score.ask_one(client, rendered["prompts"][prompt],
                                   score.png_data_url(images[position]), prompt, schema,
                                   budget, vlm["retries"])
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
    from . import features as pixels
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


def embed(dataset: str, out: str, arrays: str) -> None:
    """One dataset's concept answers, class names and fingerprints, rendered as prose and embedded.

    H5's raw material (WORKFLOW.md section 2). Every concept cell in the gathered archive is
    rendered row by row - the primary model's test and pool, the ladder models' test, the readers'
    prefix - so that T can later be read for any of them; the class names and fingerprints are
    rendered once each. The npz holds one unit-vector matrix per cell plus the two class matrices;
    the JSON holds every rendered text's hash, the served model name, the dimension, and the
    fingerprint similarity matrix, which is a property of the bank and is reported as one.

    This is a second LLM boundary and is recorded like the first: the texts that went over the wire
    are hashed here and the model that answered is named, so the vectors can be re-derived or
    disputed later without guessing what was sent.
    """
    from . import embed as words
    spec = CONFIG["embed"]
    vlm = CONFIG["vlm"]
    bank = data.load_bank(dataset, CONFIG["conceptdir"])
    release = data.load_release(CONFIG["release"])
    classes = release.class_names(dataset)
    gathered = json.loads(Path(f"{CONFIG['outdir']}/scores/{dataset}.json").read_text())
    template = spec["template"]

    embedder = words.Embedder(spec["model"], vlm["base_url"], vlm["key_file"], batch=spec["batch"],
                              retries=vlm["transport_retries"], timeout=vlm["timeout"])

    with Run("embed", dict(dataset=dataset, model=spec["model"], template=template,
                           batch=spec["batch"], bank_sha256=bank.sha256)) as run:
        out_arrays, cells = {}, {}
        for key, cell in sorted(gathered["cells"].items()):
            if cell["prompt"] != "concept":
                continue
            rows = cell["rows"]
            texts = [words.answer_text(bank, row, template) for row in rows]
            vectors = embedder.embed(texts)
            out_arrays[f"answers__{key}"] = vectors
            out_arrays[f"positions__{key}"] = np.array([r["position"] for r in rows], dtype=np.int64)
            committed = [words.committed_count(bank, r.get("answers") or {}) for r in rows]
            cells[key] = {"n": len(rows), "texts_sha256": words.sha256(texts),
                          "empty_descriptions": int(sum(1 for c in committed if c == 0)),
                          "mean_committed": float(np.mean(committed)) if committed else 0.0,
                          "example": texts[0] if texts else ""}

        name_texts = [words.name_text(bank, c, template) for c in classes]
        fingerprint_texts = [words.fingerprint_text(bank, c, template) for c in classes]
        out_arrays["names"] = embedder.embed(name_texts)
        out_arrays["fingerprints"] = embedder.embed(fingerprint_texts)
        similarity = words.similarity_matrix(out_arrays["fingerprints"])
        off_diagonal = similarity[~np.eye(len(classes), dtype=bool)]

        Path(arrays).parent.mkdir(parents=True, exist_ok=True)
        np.savez(arrays, **out_arrays)
        run.write(out, dict(
            dataset=dataset, classes=classes, model=spec["model"],
            served_model=embedder.served_model, dimension=embedder.dimension,
            calls=embedder.calls, prompt_tokens=embedder.prompt_tokens,
            template=template,
            arrays={"file": arrays, "keys": sorted(out_arrays)},
            cells=cells,
            class_texts={"names": name_texts, "fingerprints": fingerprint_texts,
                         "names_sha256": words.sha256(name_texts),
                         "fingerprints_sha256": words.sha256(fingerprint_texts)},
            fingerprint_similarity={"matrix": similarity.round(4).tolist(),
                                    "off_diagonal_min": float(off_diagonal.min()) if len(off_diagonal) else None,
                                    "off_diagonal_max": float(off_diagonal.max()) if len(off_diagonal) else None,
                                    "off_diagonal_mean": float(off_diagonal.mean()) if len(off_diagonal) else None},
        ))


def classify(dataset: str, out: str, arrays: str) -> None:
    """Every arm's class scores on the shared test sample, for one dataset.

    Nothing is measured here: this stage produces the scores and the evaluate stage turns them into
    AUCs, because the paired bootstrap has to resample the test images once for every arm at the
    same time. The scores ride in an .npz beside the JSON, which is small enough to be a result.

    Five arms: A zero-shot, B nearest fingerprint, C the concept probe, P the pixel probe, and the
    post-hoc D, which is arm A's question asked with the whole bank in the prompt. D decides no
    hypothesis; it is here so that it is bootstrapped against the others rather than beside them.
    """
    from . import classify as arms
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

        # ---- H4: every reader's concept answers, read by a cross-validated probe ----------------
        # A reader is a model plus an effort. The four models above are readers at effort `none`
        # and are subset to the same prefix the new readers were scored on, so they join H4 for
        # nothing. The probe needs no labelled pool, which is the only reason six readers can be
        # compared at all (WORKFLOW.md section 2); what it measures is how much class information
        # the answers carry, not a point on any learning curve.
        h4 = CONFIG["h4"]
        sub = int(h4["subsample"])
        probe_spec = spec["probe"]
        y_sub = y_test[:sub]
        readers = list(CONFIG["vlm"]["models"]) + list(CONFIG["vlm"].get("readers", {}))
        reader_report = {}
        for reader in readers:
            rows = cell(reader, "test", "concept")[:sub]
            if len(rows) < sub:
                raise ValueError(f"{dataset}: {reader} has {len(rows)} rows, H4 needs {sub}")
            raw = arms.concept_matrix(rows, concepts)
            # Imputed on this reader's own medians over its own images: the pool's medians belong to
            # one model at one effort, and using them here would push every reader toward the
            # baseline's habits on exactly the answers H4 is comparing.
            filled, _ = arms.impute(raw, arms.pool_medians(raw))
            missing = np.isnan(raw)
            columns = missing.any(axis=0)
            x = np.hstack([filled, missing[:, columns].astype(float)])
            got = arms.cv_probe(x, y_sub, len(classes), spec["l2_grid"],
                                probe_spec["folds"], probe_spec["seed"])
            out_arrays[f"CV__{reader}"] = got["scores"]
            index.append({"arm": "CV", "key": f"CV__{reader}", "model": reader, "labels": "cv",
                          "images": sub, "folds": got["folds"]})
            reader_report[reader] = {
                "complete_frac": float(np.mean(~np.isnan(raw).any(axis=1))),
                "answered_frac": float(np.mean(~np.isnan(raw))),
                "folds": got["folds"], "thin_classes": got["thin_classes"],
                "missing_indicator_columns": int(columns.sum()),
            }

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
            h4={"subsample": sub, "readers": reader_report},
            arrays={"file": arrays, "keys": sorted(out_arrays)},
            index=index,
            fits=fits,
            complete_frac={model: b_complete[model] for model in b_complete},
            incomplete_over_cap={key: cellspec["over_missing_cap"]
                                 for key, cellspec in gathered["cells"].items()},
            missing_indicator_columns=int(keep.sum()),
            pool_medians={c["id"]: float(m) for c, m in zip(concepts, medians)},
        ))


def evaluate(dataset: str, out: str) -> None:
    """Every arm's AUC on one dataset, with paired intervals on the differences, and n_B.

    One bootstrap, shared: each replicate resamples the 500 test images once and every arm is
    recomputed on that same resample, so a difference between two arms is a difference of two
    columns of the same matrix and its interval is a percentile of that. The absolute AUCs carry
    the thin-class caveat of WORKFLOW.md section 3; the differences are what the hypotheses read.
    """
    from . import evaluate as metrics
    spec, curve = CONFIG["evaluate"], CONFIG["curve"]
    release = data.load_release(CONFIG["release"])
    task = release.dataset(dataset)["medmnist_task"]
    summary = json.loads(Path(f"{CONFIG['outdir']}/classify/{dataset}.json").read_text())
    arrays = np.load(f"{CONFIG['outdir']}/classify/{dataset}.npz")
    labels = arrays["labels"].astype(int)
    n_classes = summary["n_classes"]
    primary = CONFIG["vlm"]["primary"]

    # H4's arrays cover a prefix of the test sample, not all of it, so they cannot ride in the same
    # bootstrap as the arms: one replicate resamples one set of images, and two sets of images are
    # two bootstraps. They get their own below, over the prefix the readers share.
    arm_scores = {k: arrays[k] for k in arrays.files
                  if k != "labels" and not k.startswith("CV__")}
    cv_scores = {k[4:]: arrays[k] for k in arrays.files if k.startswith("CV__")}
    with Run("evaluate", dict(dataset=dataset, task=task, bootstrap=spec["bootstrap"],
                              ci=spec["ci"]), seeds=[spec.get("seed", 0)]) as run:
        point = {k: metrics.auc(labels, v, task, n_classes) for k, v in arm_scores.items()}
        keys, replicates = metrics.bootstrap_aucs(labels, arm_scores, task, n_classes,
                                                  spec["bootstrap"], spec.get("seed", 0))
        column = {k: i for i, k in enumerate(keys)}

        def mean_over_seeds(arm, n):
            cols = [column[f"{arm}__n{n}__seed{s}"] for s in curve["seeds"]]
            return replicates[:, cols].mean(axis=1)

        # ---- the curve, and the differences H1 turns on ----------------------------------------
        curve_points = {}
        for arm in ("C", "P"):
            for n in curve["n"]:
                draws = mean_over_seeds(arm, n)
                curve_points[f"{arm}__n{n}"] = {
                    "point": float(np.mean([point[f"{arm}__n{n}__seed{s}"] for s in curve["seeds"]])),
                    **metrics.interval(draws, spec["ci"])}

        differences = {}
        for n in curve["n"]:
            differences[f"C_minus_P__n{n}"] = metrics.interval(
                mean_over_seeds("C", n) - mean_over_seeds("P", n), spec["ci"])
        b_primary = replicates[:, column[f"B__{primary}"]]
        differences["B_minus_A"] = metrics.interval(b_primary - replicates[:, column["A"]], spec["ci"])
        for n in curve["n"]:
            differences[f"C_minus_B__n{n}"] = metrics.interval(
                mean_over_seeds("C", n) - b_primary, spec["ci"])

        # ---- the permutation controls: how much each arm loses when its structure is destroyed --
        controls = {}
        for model in CONFIG["vlm"]["models"]:
            drops = np.mean([replicates[:, column[f"Bperm__{model}__seed{s}"]]
                             for s in CONFIG["classify"]["permute"]["seeds"]], axis=0)
            controls[f"B__{model}"] = {
                "permuted": float(np.mean([point[f"Bperm__{model}__seed{s}"]
                                           for s in CONFIG["classify"]["permute"]["seeds"]])),
                "drop": metrics.interval(replicates[:, column[f"B__{model}"]] - drops, spec["ci"])}
        for n in curve["n"]:
            permuted = np.mean([replicates[:, column[f"Cperm__n{n}__seed{s}"]]
                                for s in CONFIG["classify"]["permute"]["seeds"]], axis=0)
            controls[f"C__n{n}"] = {
                "permuted": float(np.mean([point[f"Cperm__n{n}__seed{s}"]
                                           for s in CONFIG["classify"]["permute"]["seeds"]])),
                "drop": metrics.interval(mean_over_seeds("C", n) - permuted, spec["ci"])}

        # ---- n_B: how many labelled images the pixel probe needs to reach the textbook ---------
        point_curve = {n: curve_points[f"P__n{n}"]["point"] for n in curve["n"]}
        n_b_point = metrics.crossing(point_curve, point[f"B__{primary}"], curve["n"])
        draws = []
        for b in range(replicates.shape[0]):
            draws.append(metrics.crossing({n: float(np.mean([replicates[b, column[f"P__n{n}__seed{s}"]]
                                                             for s in curve["seeds"]]))
                                           for n in curve["n"]}, b_primary[b], curve["n"]))
        draws = np.array(draws, dtype=float)
        half = (1 - spec["ci"]) / 2
        n_b = {
            "point": metrics.code_crossing(n_b_point, curve["n"]),
            "median": metrics.quantile_code(draws, 0.5, curve["n"]),
            "lo": metrics.quantile_code(draws, half, curve["n"]),
            "hi": metrics.quantile_code(draws, 1 - half, curve["n"]),
            "already_above_frac": float(np.mean(draws == -np.inf)),
            "never_reaches_frac": float(np.mean(draws == np.inf)),
        }

        # ---- H4: the reader chain, on the prefix every reader shares --------------------------
        # Its own bootstrap, over the same 200 images for every reader, so `thinking - baseline`
        # and `frontier - thinking` are differences of two columns of one matrix exactly as every
        # other paired difference in this study is. The decision rule is in config and was fixed
        # before the first of these calls was bought (WORKFLOW.md section 2).
        h4_spec = CONFIG["h4"]
        sub = int(h4_spec["subsample"])
        y_sub = labels[:sub]
        cv_point = {k: metrics.auc(y_sub, v, task, n_classes) for k, v in cv_scores.items()}
        cv_keys, cv_reps = metrics.bootstrap_aucs(y_sub, cv_scores, task, n_classes,
                                                  spec["bootstrap"], spec.get("seed", 0))
        cv_column = {k: i for i, k in enumerate(cv_keys)}
        steps = {}
        for name, (lo, hi) in {"thinking_minus_baseline": (h4_spec["baseline"], h4_spec["thinking"]),
                               "frontier_minus_thinking": (h4_spec["thinking"], h4_spec["frontier"])}.items():
            steps[name] = {"from": lo, "to": hi,
                           **metrics.interval(cv_reps[:, cv_column[hi]] - cv_reps[:, cv_column[lo]],
                                              spec["ci"])}
        h4 = {"subsample": sub, "probe_auc": cv_point, "steps": steps}

        run.write(out, dict(
            dataset=dataset, task=task, n_classes=n_classes, classes=summary["classes"],
            auc={k: point[k] for k in sorted(point)},
            curve=curve_points,
            differences=differences,
            controls=controls,
            n_b=n_b,
            arm_b_by_model={m: point[f"B__{m}"] for m in CONFIG["vlm"]["models"]},
            h4=h4,
            complete_frac=summary["complete_frac"],
            incomplete_over_cap=summary["incomplete_over_cap"],
            bootstrap=spec["bootstrap"],
        ))


def evaluate_across(out: str) -> None:
    """The across-dataset tests: H1, H2, H3 and H4 as WORKFLOW.md section 2 states their rules.

    Sign tests rather than pooled AUCs, because an AUC on pathmnist and an AUC on octmnist are not
    commensurable quantities to average. With six datasets the test is coarse - 6 of 6 is p = 0.016
    and 5 of 6 is p = 0.11 - so a hypothesis is supported only when it wins everywhere, and the
    per-dataset differences are what carries the reading.

    H4 is a hypothesis and not an extension, which is the one thing about it worth stating here.
    Its decision rule was written into config and WORKFLOW.md before any call of its readers was
    bought, which is what arm D could not say for itself and why arm D is gone.
    """
    from . import evaluate as metrics
    spec, curve = CONFIG["evaluate"], CONFIG["curve"]
    datasets = CONFIG["datasets"]
    models = CONFIG["vlm"]["models"]
    per = {d: json.loads(Path(f"{CONFIG['outdir']}/evaluate/{d}.json").read_text()) for d in datasets}

    with Run("evaluate_across", dict(datasets=datasets, min_n_b=100, h3_min_wins=spec["h3_min_wins"])) as run:
        smallest = min(curve["n"])
        # H1: the textbook is worth a measurable number of labelled images.
        c_beats_p = {d: per[d]["differences"][f"C_minus_P__n{smallest}"]["median"] > 0 for d in datasets}
        n_b_values = {d: per[d]["n_b"]["point"] for d in datasets}
        numeric = [float(v) for v in n_b_values.values() if v.isdigit()]
        never = sum(1 for v in n_b_values.values() if v.startswith(">"))
        already = sum(1 for v in n_b_values.values() if v.startswith("<="))

        # "median n_B at least 100" has to be read on the ordinal scale, because n_B is ordinal and
        # its values include `<=50` and `>2000`. A median over the numeric ones alone would drop
        # exactly the datasets that carry the most information: a `>2000` is the strongest possible
        # evidence for H1 and a `<=50` the strongest against, and discarding both would let three
        # datasets decide a six-dataset rule. Ranks keep them in, in the right order.
        ranks = [metrics.rank_of(-np.inf if v.startswith("<=") else np.inf if v.startswith(">")
                                 else float(v), curve["n"]) for v in n_b_values.values()]
        median_rank = float(np.median(ranks))
        threshold_rank = metrics.rank_at_least(100.0, curve["n"])
        h1 = {
            "n_b": n_b_values,
            "median_n_b": metrics.code_of_rank(int(np.ceil(median_rank)), curve["n"]),
            "median_n_b_over_numeric": float(np.median(numeric)) if numeric else None,
            "median_rank": median_rank, "threshold_rank": threshold_rank,
            "datasets_where_the_probe_never_reaches_arm_b": never,
            "datasets_where_the_probe_starts_above_arm_b": already,
            "c_beats_p_at_smallest_n": c_beats_p,
            "c_beats_p_wins": sum(c_beats_p.values()),
            "c_beats_p_sign_test_p": metrics.sign_test(sum(c_beats_p.values()), len(datasets)),
            "supported": bool(sum(c_beats_p.values()) == len(datasets)
                              and median_rank >= threshold_rank),
        }

        # H2: the bank, not just the model.
        b_beats_a = {d: per[d]["differences"]["B_minus_A"]["median"] > 0 for d in datasets}
        b_drops = {d: per[d]["controls"][f"B__{CONFIG['vlm']['primary']}"]["drop"]["median"] > 0
                   for d in datasets}
        c_drops = {d: per[d]["controls"][f"C__n{max(curve['n'])}"]["drop"]["median"] > 0
                   for d in datasets}
        h2 = {
            "b_beats_a": b_beats_a, "b_beats_a_wins": sum(b_beats_a.values()),
            "b_beats_a_sign_test_p": metrics.sign_test(sum(b_beats_a.values()), len(datasets)),
            "b_loses_under_permutation": b_drops, "c_loses_under_permutation": c_drops,
            "supported": bool(sum(b_beats_a.values()) == len(datasets)
                              and all(b_drops.values()) and all(c_drops.values())),
        }

        # H3: scale, read within family because size and training data are confounded across them.
        families = {}
        for name, cfg in models.items():
            families.setdefault(cfg["family"], []).append((cfg["params_b"], name))
        ladder = {}
        for family, members in families.items():
            small, large = [name for _, name in sorted(members)][0], [name for _, name in sorted(members)][-1]
            wins = {d: per[d]["arm_b_by_model"][large] > per[d]["arm_b_by_model"][small] for d in datasets}
            ladder[family] = {"smaller": small, "larger": large, "wins": sum(wins.values()),
                              "per_dataset": wins,
                              "sign_test_p": metrics.sign_test(sum(wins.values()), len(datasets))}
        order = [name for _, name in sorted((m["params_b"], n) for n, m in models.items())]
        table = np.array([[per[d]["arm_b_by_model"][m] for m in order] for d in datasets])
        h3 = {
            "ladder": ladder, "model_order": order,
            "arm_b_auc": {d: {m: per[d]["arm_b_by_model"][m] for m in order} for d in datasets},
            "friedman": metrics.friedman(table),
            "supported": bool(all(f["wins"] >= spec["h3_min_wins"] for f in ladder.values())),
        }

        # H4: a better reader gets more class information out of the same images. Two steps, each
        # changing one thing: effort (H4a) then model (H4b). Supported on 6 of 6, the rule H1 and
        # H2 are held to, because 5 of 6 is p = 0.11 and this study cannot do better with six
        # datasets. The `probe_auc` per reader is reported whatever the verdict: which concepts a
        # reader can answer is the question the study is really asking now.
        h4_spec, h4 = CONFIG["h4"], {}
        for part, step in (("h4a", "thinking_minus_baseline"), ("h4b", "frontier_minus_thinking")):
            wins = {d: per[d]["h4"]["steps"][step]["median"] > 0 for d in datasets}
            first = per[datasets[0]]["h4"]["steps"][step]
            h4[part] = {
                "step": step, "from": first["from"], "to": first["to"],
                "per_dataset": wins, "wins": sum(wins.values()),
                "differences": {d: per[d]["h4"]["steps"][step] for d in datasets},
                "sign_test_p": metrics.sign_test(sum(wins.values()), len(datasets)),
                "supported": bool(sum(wins.values()) >= h4_spec["min_wins"]),
            }
        readers = sorted(per[datasets[0]]["h4"]["probe_auc"])
        h4["probe_auc"] = {d: {r: per[d]["h4"]["probe_auc"][r] for r in readers} for d in datasets}
        h4["readers"] = readers
        h4["subsample"] = h4_spec["subsample"]
        h4["supported"] = bool(h4["h4a"]["supported"] and h4["h4b"]["supported"])

        run.write(out, dict(datasets=datasets, h1=h1, h2=h2, h3=h3, h4=h4,
                            flagged_cells={d: [k for k, over in per[d]["incomplete_over_cap"].items() if over]
                                           for d in datasets}))


def tables(dest: str) -> None:
    """Every table and every number macro the report states, from results/ alone."""
    from . import report as reporting
    datasets, curve = CONFIG["datasets"], CONFIG["curve"]["n"]
    primary = CONFIG["vlm"]["primary"]
    per, across = reporting.load(CONFIG["outdir"], datasets)
    literature = data.load_literature(CONFIG["literature"])
    Path(dest).mkdir(parents=True, exist_ok=True)
    with Run("tables", dict(datasets=datasets, literature_sha256=literature.sha256)) as run:
        reporting.table_h1(per, datasets, curve, dest)
        reporting.table_h2(per, datasets, curve, primary, dest)
        reporting.table_h3(across, datasets, dest)
        reporting.table_h4(across, datasets, dest)
        reporting.table_literature(per, literature, datasets, curve, primary, dest)
        reporting.table_completeness(per, datasets, dest)
        macros = reporting.numbers(per, across, datasets, curve, primary, dest, literature)
        run.write(f"{CONFIG['outdir']}/tables.json", dict(dest=dest, macros=macros))


def figures(dest: str) -> None:
    """The five figures: one per hypothesis, and H4a read against its baseline."""
    from . import report as reporting
    datasets, curve = CONFIG["datasets"], CONFIG["curve"]["n"]
    per, across = reporting.load(CONFIG["outdir"], datasets)
    literature = data.load_literature(CONFIG["literature"])
    Path(dest).mkdir(parents=True, exist_ok=True)
    with Run("figures", dict(datasets=datasets, literature_sha256=literature.sha256)) as run:
        reporting.figure_curve(per, datasets, curve, dest, literature=literature)
        reporting.figure_n_b(per, datasets, curve, dest)
        reporting.figure_ladder(across, datasets, dest)
        reporting.figure_readers(across, datasets, dest)
        reporting.figure_thinking(across, datasets, dest)
        run.write(f"{CONFIG['outdir']}/figures.json", dict(dest=dest,
                  files=["fig_curve.png", "fig_n_b.png", "fig_ladder.png", "fig_readers.png",
                         "fig_thinking.png"]))


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
    p = sub.add_parser("embed"); p.add_argument("dataset")
    p.add_argument("--out", required=True); p.add_argument("--arrays", required=True)
    p = sub.add_parser("classify"); p.add_argument("dataset")
    p.add_argument("--out", required=True); p.add_argument("--arrays", required=True)
    p = sub.add_parser("evaluate"); p.add_argument("dataset"); p.add_argument("--out", required=True)
    p = sub.add_parser("evaluate-across"); p.add_argument("--out", required=True)
    for name in ("tables", "figures"):
        q = sub.add_parser(name); q.add_argument("--dest", required=True)
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
    elif a.stage == "embed":
        embed(a.dataset, a.out, a.arrays)
    elif a.stage == "classify":
        classify(a.dataset, a.out, a.arrays)
    elif a.stage == "evaluate":
        evaluate(a.dataset, a.out)
    elif a.stage == "evaluate-across":
        evaluate_across(a.out)
    elif a.stage == "tables":
        tables(a.dest)
    elif a.stage == "figures":
        figures(a.dest)
    else:
        raise SystemExit(f"stage {a.stage} not implemented yet")


if __name__ == "__main__":
    main()
