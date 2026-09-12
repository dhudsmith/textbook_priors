# =====================================================================================
# TEXTBOOK PRIORS OVER VISUAL FEATURES
#
# Can a vision-language model's textbook knowledge of what pathology looks like stand in for
# labelled data? Six MedMNIST benchmarks, four arms, three hypotheses (WORKFLOW.md sections 1-3).
#
#     snakemake --profile profiles/palmetto              # everything, on SLURM
#     snakemake --profile profiles/palmetto -n           # dry run: inspect the DAG
#     snakemake --profile profiles/local -j 2 smoke      # the tests, seconds
#     snakemake --profile profiles/local -j 2 prompts    # one stage by name
#
# The workflow reads top to bottom through seven stages (WORKFLOW.md section 6):
#
#   0  SMOKE      bank schema and anchors, label maps against the pinned release, both prompts,
#                 the arm-B estimator on a fixture, metric conventions, client retry
#   1  SAMPLE     per dataset: the seeded 500-image test sample and 2000-image labelled pool
#   2  SCORE      per dataset: render the concept and zero-shot prompts from the bank; then,
#                 per model x split x prompt x chunk of 100, the VLM calls, archived raw
#   3  FEATURES   per dataset: ImageNet ResNet-18 penultimate features of the sampled images
#   4  CLASSIFY   per dataset: arms A, B, C, P at every n and seed, and the permutation controls
#   5  EVALUATE   AUC per arm; the paired bootstrap; n_B; the sign tests and the ladder
#   6  REPORT     three figures, tables, number macros, the technical report PDF
#
# The stages land one at a time, each tested before the next is written; the section at the foot
# of this file lists what is still to come. Every unit of work is one entry point of
# priors/stages.py, a pure function of its inputs, its config values and its own seed, writing one
# JSON with a run manifest. Tables and figures read only those files. The two fixed inputs - the
# concept bank and the raw MedMNIST releases - were completed before the workflow and no rule
# refetches or re-verifies them (WORKFLOW.md section 4).
# =====================================================================================

import re
from pathlib import Path

import yaml

configfile: "config/config.yaml"

# Seconds-long bookkeeping runs in the submitting process rather than paying a SLURM round-trip.
# Anything with a real toolchain or a real cost is submitted so it runs with declared resources.
localrules:
    all, sample, prompts, score, smoke, render_prompts, collect_scores,


OUT = config["outdir"]
DATASETS = config["datasets"]
RES = config["resources"]

# The pinned release description, read here only to name each dataset's release file: the file a
# sample job reads has to be a declared input, and this file is the authority on what it is called.
RELEASE = yaml.safe_load(Path(config["release"]).read_text())["datasets"]

# BLAS sizes its thread pool from the machine, not the cgroup; pin it to the allocation.
PIN = "export OMP_NUM_THREADS={threads} MKL_NUM_THREADS={threads} OPENBLAS_NUM_THREADS={threads}; "
STAGE = PIN + "python -m priors.stages "


def code(*modules):
    """The priors modules whose contents determine a rule's output.

    Snakemake's `code` rerun trigger inspects the rule's own shell line, not the Python it invokes,
    so editing a module leaves downstream outputs stale without notice. Listing the modules puts
    them under the ordinary input trigger. Keep these lists minimal and honest. The config is
    deliberately NOT listed; the values a rule's numbers depend on are declared as params instead,
    which Snakemake tracks value by value, so a resource edit reruns nothing."""
    return [f"priors/{m}.py" for m in modules]


def res(name):
    """Per-rule resources from config, as the keyword arguments `resources:` wants."""
    r = RES[name]
    return dict(mem_mb=r["mem_mb"], runtime=r["runtime"], cpus_per_task=r["cpus"])


CODE_SAMPLE = code("data", "sample", "stages")
CODE_PROMPTS = code("data", "prompts", "stages")
CODE_SCORE = code("llm", "score", "stages")     # the prompts arrive as a file, not as a module

TEST_FILES = sorted(str(p) for p in Path("tests").glob("*.py"))

SMOKE = f"{OUT}/smoke_ok.txt"
SAMPLES = expand(f"{OUT}/sample/{{dataset}}.json", dataset=DATASETS)
PROMPTS = expand(f"{OUT}/prompts/{{dataset}}.json", dataset=DATASETS)

MODELS = list(config["vlm"]["models"])
PRIMARY = config["vlm"]["primary"]
CHUNK = config["vlm"]["chunk"]


def slug(model):
    """A model name as a rule name and a resource name: `qwen3.8-27b-fp8` is neither."""
    return re.sub(r"[^a-z0-9]+", "_", model.lower())


def chunk_ids(split):
    """The chunk numbers one split is cut into, zero-padded so they sort."""
    n = config["sample"]["test_n" if split == "test" else "pool_n"]
    return [f"{k:02d}" for k in range((n + CHUNK - 1) // CHUNK)]


def score_cells(model=None):
    """Every (dataset, model, split, prompt, chunk) the fan-out covers.

    `splits` per model comes from config, because arm B is training-free and only the primary model
    ever needs the labelled pool. The zero-shot prompt is the primary model's alone: arm A is one
    baseline for H2, not a fifth arm per model."""
    cells = []
    for name in ([model] if model else MODELS):
        for split in config["vlm"]["models"][name]["splits"]:
            prompts = ["concept"] + (["zero_shot"] if name == PRIMARY and split == "test" else [])
            for prompt in prompts:
                for dataset in DATASETS:
                    for chunk in chunk_ids(split):
                        cells.append(f"{OUT}/score/{dataset}__{name}__{split}__{prompt}"
                                     f"__chunk{chunk}.json")
    return cells


SCORES = score_cells()
SCORE_TABLES = expand(f"{OUT}/scores/{{dataset}}.json", dataset=DATASETS)

wildcard_constraints:
    dataset="|".join(DATASETS),
    model="|".join(re.escape(m) for m in MODELS),


# ---- targets: one phony target per stage; `all` becomes the technical report at stage 6 --------
rule all:
    input: SAMPLES, PROMPTS

rule sample:
    input: SAMPLES

rule prompts:
    input: PROMPTS

rule score:
    input: SCORE_TABLES


# =====================================================================================
# 0  SMOKE
#
# The tests, in seconds: the concept bank against the schema CONCEPT_BANK.md defines, over all
# twelve committed files; config/medmnist.yaml against the installed `medmnist`, because its label
# maps were read from the package and not retyped; both prompts as properties of the rendered
# strings, so that H2's non-circularity - the concept prompt names no class, the zero-shot prompt
# mentions no concept - fails here rather than after an archive has been written; and the AUC
# convention the study reports, pinned to the package that defines it.
#
# Every rule below takes the marker as an input, so nothing is computed on code that fails its
# tests, and the edge also fixes the order: the tests finish before any job that could waste an
# LLM call starts.
#
# What this rule does NOT take as an input is the twelve bank files, even though the bank tests
# read them. A marker that every rule depends on propagates: anything that reruns the tests
# reruns everything below them, and one dataset's bank edit would then invalidate every other
# dataset's response archive. Keeping the bank out preserves the per-dataset edge that matters -
# a bank file is an input of its own `render_prompts` job and of nothing else - at the price of
# the schema tests not re-running by themselves after a bank edit. Re-run them on demand:
#
#     snakemake --profile profiles/local -j 2 -F smoke
#
# The release description and the code are in, because both are global: a change to either
# already invalidates every rule that reads them, so the marker adds nothing. `ancient()` would
# have been the tidier way to say "a gate, not a data dependency", and was tried and rejected: it
# suppresses rerun detection for the whole job, so a changed bank file stopped re-rendering its
# own prompt. After a change that cannot have moved a number (a new test, a comment), the honest
# move is `snakemake --touch <targets>`.
# =====================================================================================

rule smoke:
    """The tests. Nothing below runs until they pass. x1, local, seconds."""
    input:
        code=code("data", "prompts", "stages", "manifest"),
        release=config["release"],
        tests=TEST_FILES,
    params:
        datasets=",".join(DATASETS),
        size=config["size"],
    output: touch(SMOKE)
    log: "logs/smoke.log"
    conda: "envs/priors.yml"
    shell: "python -m pytest tests -q > {log} 2>&1"


# =====================================================================================
# 1  SAMPLE
#
# The two seeded samples every later stage is defined over: 500 test images per dataset, shared by
# every arm and every model so that every comparison in the study is paired, and a 2000-image
# labelled pool from the official train split, the largest point of the learning curve. One seed
# from config for both.
#
# The releases are prior work and no rule fetches them (WORKFLOW.md section 4): each job reads its
# file straight through the `data/raw` symlink, and records the MD5 the pinned release already
# carries rather than recomputing it. Their members are deflated, so there is no random access -
# `np.load` would materialise a 13.5 GB array to keep 2000 images of it - and priors/sample.py
# instead inflates the member as a stream and copies out the wanted rows, one row at a time.
#
# Two outputs per job. The JSON is the unit of work and carries what defines the sample: the drawn
# indices, their labels, and the sample's class balance beside the whole split's, so that the
# report can show what the seed drew against what it drew from. The images go to the cache on the
# project filesystem, because a quarter of a gigabyte of pixels per dataset is an input to the
# score and features stages rather than a result anything reads.
# =====================================================================================

rule sample_dataset:
    """One dataset's test sample and labelled pool, streamed out of its release file. x6."""
    input:
        raw=lambda w: f"{config['rawdir']}/{RELEASE[w.dataset]['file']}",
        release=config["release"],
        smoke=SMOKE,
        code=CODE_SAMPLE,
    params:
        test_n=config["sample"]["test_n"],
        pool_n=config["sample"]["pool_n"],
        seed=config["sample"]["seed"],
    output:
        json=f"{OUT}/sample/{{dataset}}.json",
        arrays=f"{config['cachedir']}/{{dataset}}.npz",
    log: "logs/sample/{dataset}.log"
    benchmark: "benchmarks/sample/{dataset}.tsv"
    conda: "envs/priors.yml"
    threads: RES["sample"]["cpus"]
    resources: **res("sample")
    shell: STAGE + "sample {wildcards.dataset} --out {output.json} --arrays {output.arrays} > {log} 2>&1"


# =====================================================================================
# 2  SCORE
#
# The stage where the prior enters, and the one that tests principle 7 (the LLM boundary is
# explicit): every response is archived raw, and everything downstream is a deterministic
# function of that archive.
#
# Prompt rendering is its own rule rather than a step inside the scoring loop. A prompt that is
# formatted where it is sent exists three times over - in the call, in the manifest's hash, and in
# whatever the report or the live demo prints - and those three copies drift. Here the two prompt
# strings are one artifact per dataset, hashed, and every score job reads it (WORKFLOW.md
# section 7).
#
# The concept prompt asks for a level per concept and never names a class; the zero-shot prompt
# asks for a distribution over the class names and never mentions a concept. H2 compares the two,
# so their separation is a property of this rule rather than a promise in the prose.
# =====================================================================================

rule render_prompts:
    """Both prompt strings for one dataset, from the bank and the pinned label map. x6, local."""
    input:
        bank=lambda w: f"{config['conceptdir']}/{w.dataset}.yaml",
        release=config["release"],
        code=CODE_PROMPTS,
        smoke=SMOKE,
    params:
        size=config["size"],
        anchors=config["vlm"]["prompt"]["anchors"],
    output: f"{OUT}/prompts/{{dataset}}.json"
    log: "logs/render_prompts/{dataset}.log"
    conda: "envs/priors.yml"
    shell: STAGE + "render-prompts {wildcards.dataset} --out {output} > {log} 2>&1"


rule probe:
    """Ten images of one dataset through one model, outside `rule all`. Build one by name:

        snakemake --profile profiles/palmetto results/probe/pneumoniamnist__qwen3.8-27b-fp8.json

    Why it is opt-in: it is the only rule that spends calls without producing a number the study
    reports. What it is for (WORKFLOW.md section 9, step 3) is everything that cannot be tested
    without the service - that a compute node reaches it, that the manifest carries the served
    model name and the prompt hash, and that a malformed answer is recorded as missing rather than
    guessed. The last one is not simulated: one extra call goes out with a token budget of one, so
    the reply really is truncated and the content retry really fires.

    It writes nothing into results/score/. That archive is written by the scoring rules alone and
    is fixed from the moment it exists, so re-scoring stays a decision rather than an accident."""
    input:
        prompts=f"{OUT}/prompts/{{dataset}}.json",
        sample=f"{OUT}/sample/{{dataset}}.json",
        arrays=f"{config['cachedir']}/{{dataset}}.npz",
        smoke=SMOKE,
        code=CODE_SCORE,
    params:
        n=config["vlm"]["probe"]["n"],
        temperature=config["vlm"]["temperature"],
        reasoning=config["vlm"]["reasoning"],
        max_tokens=config["vlm"]["max_tokens"],
        retries=config["vlm"]["retries"],
    output: f"{OUT}/probe/{{dataset}}__{{model}}.json"
    log: "logs/probe/{dataset}__{model}.log"
    benchmark: "benchmarks/probe/{dataset}__{model}.tsv"
    conda: "envs/priors.yml"
    threads: RES["probe"]["cpus"]
    resources: **res("probe")
    shell: STAGE + "probe {wildcards.dataset} {wildcards.model} --out {output} > {log} 2>&1"


# One rule per model rather than one rule with a model wildcard, because each model gets its own
# `llm_<model>` resource and Snakemake resource names are fixed per rule. The cap for each lives in
# profiles/palmetto/config.yaml, below the concurrency the service publishes; a job holds one unit
# for as long as it runs, so the number of jobs in flight for a model is the number of calls in
# flight for it. The smoke tier checks the profile's caps against config's.
for _model in MODELS:
    # The command is built here rather than inline: Snakemake's parser rejects a `shell:` whose
    # expression spans lines inside a rule generated in a loop, though it accepts one in a rule
    # declared with a name.
    _cmd = (STAGE + "score {wildcards.dataset} " + _model +
            " {wildcards.split} {wildcards.prompt} {wildcards.chunk} --out {output} > {log} 2>&1")
    # x30 for the primary model (test concept, test zero-shot, pool concept, six datasets each)
    # and x30 for each ladder model; 270 jobs of a hundred images in all.
    rule:
        name: f"score_{slug(_model)}"
        input:
            prompts=f"{OUT}/prompts/{{dataset}}.json",
            sample=f"{OUT}/sample/{{dataset}}.json",
            arrays=f"{config['cachedir']}/{{dataset}}.npz",
            smoke=SMOKE,
            code=CODE_SCORE,
        params:
            chunk_size=CHUNK,
            temperature=config["vlm"]["temperature"],
            reasoning=config["vlm"]["reasoning"],
            max_tokens=config["vlm"]["max_tokens"],
            retries=config["vlm"]["retries"],
        # protected(): Snakemake makes the file read-only once written, which is principle 7 with
        # teeth. Re-scoring then costs an explicit chmod, so 27,000 calls cannot be spent again by
        # a stray rerun.
        output: protected(f"{OUT}/score/{{dataset}}__{_model}__{{split}}__{{prompt}}__chunk{{chunk}}.json")
        log: f"logs/score/{{dataset}}__{_model}__{{split}}__{{prompt}}__chunk{{chunk}}.log"
        benchmark: f"benchmarks/score/{{dataset}}__{_model}__{{split}}__{{prompt}}__chunk{{chunk}}.tsv"
        conda: "envs/priors.yml"
        threads: RES["score"]["cpus"]
        resources: **res("score"), **{f"llm_{slug(_model)}": 1}
        shell: _cmd


rule collect_scores:
    """One dataset's chunks gathered into the table the classify stage reads. x6, local."""
    input:
        chunks=lambda w: [f for f in SCORES if f.startswith(f"{OUT}/score/{w.dataset}__")],
        prompts=f"{OUT}/prompts/{{dataset}}.json",
        code=code("stages"),
    params:
        missing_max_frac=config["classify"]["missing_max_frac"],
    output: f"{OUT}/scores/{{dataset}}.json"
    log: "logs/collect_scores/{dataset}.log"
    conda: "envs/priors.yml"
    shell: STAGE + "collect-scores {wildcards.dataset} --out {output} > {log} 2>&1"


# =====================================================================================
# STILL TO COME, in this order, each one tested before the next is written:
#
#   0  smoke              two tiers of it are still missing, and arrive with the code they test:
#                         the arm-B estimator on a fixture (with priors/classify.py) and the LLM
#                         client's retry on a malformed answer (with priors/llm.py)
#   3  pixel_features     x6, submitted, the torch environment: ResNet-18 penultimate features
#   4  classify_dataset   x6: arms A, B, C, P over the curve and the permutation controls
#   5  evaluate_dataset   x6: AUC per arm, the paired bootstrap, n_B
#   5  evaluate_across    x1: the sign tests, the ladder, the Friedman test
#   6  figures, tables, technical_report
#
# Extensions (WORKFLOW.md section 10), each outside `all`: bare_levels, generic_prompt,
# primary_upgrade.
# =====================================================================================
