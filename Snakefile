# =====================================================================================
# TEXTBOOK PRIORS OVER VISUAL FEATURES
#
# Can a vision-language model's textbook knowledge of what pathology looks like stand in for
# labelled data? Six MedMNIST benchmarks, four arms, four hypotheses (WORKFLOW.md sections 1-3).
#
#     snakemake --profile profiles/palmetto              # everything, on SLURM
#     snakemake --profile profiles/palmetto -n           # dry run: inspect the DAG
#     snakemake --profile profiles/local -j 2 smoke      # the tests, seconds
#     snakemake --profile profiles/local -j 2 prompts    # one stage by name
#
# The workflow reads top to bottom through seven stages (WORKFLOW.md section 6):
#
#   0  SMOKE      bank schema and anchors, label maps against the pinned release, both prompts,
#                 the estimators on fixtures, metric conventions, the client's request bodies
#   1  SAMPLE     per dataset: the seeded 500-image test sample and 2000-image labelled pool
#   2  SCORE      per dataset: render the concept and zero-shot prompts from the bank;
#                 then, per model x split x prompt x chunk of 100, the VLM calls, archived raw;
#                 plus H4's two readers on a 200-image prefix of the test sample
#   3  FEATURES   per dataset: ImageNet ResNet-18 penultimate features of the sampled images
#   4  CLASSIFY   per dataset: arms A, B, C, P at every n and seed, the permutation controls,
#                 and every reader's cross-validated probe on the shared prefix (H4)
#   5  EVALUATE   AUC per arm; the paired bootstrap; n_B; the sign tests, the ladder, the chain
#   6  REPORT     five figures, tables, number macros, the technical report PDF
#
# Every unit of work is one entry point of priors/stages.py, a pure function of its inputs, its
# config values and its own seed, writing one JSON with a run manifest. Tables and figures read
# only those files. The three fixed inputs - the concept bank, the raw MedMNIST releases and the
# published literature benchmarks - were completed before the workflow and no rule refetches or
# re-verifies them (WORKFLOW.md section 4).
# =====================================================================================

import os
import re
import sys
from pathlib import Path

import yaml

from snakemake.exceptions import WorkflowError

configfile: "config/config.yaml"


# ---- one checkout runs this workflow, and it is the one the results live in --------------------
#
# results/, the write-protected response archive under results/score/, benchmarks/, logs/ and
# Snakemake's own .snakemake/ metadata all sit beside this file, so where the workflow is RUN from
# decides where they land. An agent session is given a throwaway git worktree that is recreated
# without warning, and a run from there puts 58,186 calls' worth of archive somewhere nobody will
# look for it and that will not survive the week.
#
# Reading the workflow from anywhere is fine and useful - a dry run, a lint, a --touch, an --unlock
# from a session worktree are all legitimate - so this refuses execution alone. Set
# PRIORS_ALLOW_ANY_CWD=1 to override it deliberately, which is the only way results should ever
# land anywhere else.
RUN_ROOT = Path(config["run_root"]).expanduser().resolve()
_READS_ONLY = {"-n", "--dry-run", "--dryrun", "--lint", "--touch", "-t", "--unlock", "--list",
               "--list-target-rules", "--summary", "--detailed-summary", "--dag", "--rulegraph",
               "--filegraph", "--report", "--version", "--help", "-h"}
if (Path.cwd().resolve() != RUN_ROOT and not _READS_ONLY.intersection(sys.argv)
        and os.environ.get("PRIORS_ALLOW_ANY_CWD") != "1"):
    raise WorkflowError(
        "This workflow writes its results beside the Snakefile, so it runs in one checkout:\n"
        f"    run_root (config/config.yaml):  {RUN_ROOT}\n"
        f"    this working directory:         {Path.cwd().resolve()}\n\n"
        "Run it from the checkout above. Editing, committing and dry-running from anywhere else\n"
        "is fine and needs no override; if you really mean to write results here, set\n"
        "PRIORS_ALLOW_ANY_CWD=1.")

# Seconds-long bookkeeping runs in the submitting process rather than paying a SLURM round-trip.
# Anything with a real toolchain or a real cost is submitted so it runs with declared resources.
localrules:
    all, sample, prompts, score, features, classify, evaluate, report, smoke, render_prompts,
    collect_scores, evaluate_across, tables, prompts_txt, render_prompts_txt,


OUT = config["outdir"]
DATASETS = config["datasets"]
RES = config["resources"]

# The pinned release description: each dataset's release file (the file a sample job reads has to
# be a declared input, and this file is the authority on what it is called), its size and MD5 for
# the fetch rule, its split sizes for the sample caps, and its task, which decides which arms a
# dataset can have (WORKFLOW.md sections 3 and 4).
RELEASE_DOC = yaml.safe_load(Path(config["release"]).read_text())
RELEASE = RELEASE_DOC["datasets"]
ZENODO = f"https://zenodo.org/records/{RELEASE_DOC['zenodo_record']}"
# chestmnist: fourteen co-occurring findings. Arms A and B are not defined over such a label space,
# so it is scored by the primary model alone, concept prompt alone, and joins arms C and P only.
MULTI_LABEL = {d for d in DATASETS if RELEASE[d]["medmnist_task"].startswith("multi-label")}

# BLAS sizes its thread pool from the machine, not the cgroup; pin it to the allocation.
PIN = "export OMP_NUM_THREADS={threads} MKL_NUM_THREADS={threads} OPENBLAS_NUM_THREADS={threads}; "
STAGE = PIN + "python -m priors.stages "

# pdflatex loads libz, and this cluster's login environment puts a spack zlib-ng ahead of the
# system library whose optimised path is an illegal instruction on the older compute nodes: TeX
# ships page one and then dies of SIGILL, leaving a truncated but readable PDF.
TEX = "env -u LD_LIBRARY_PATH "


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
CODE_PROMPTS_TXT = code("prompts", "stages")    # formats the file render_prompts already wrote
CODE_SCORE = code("llm", "score", "stages")     # the prompts arrive as a file, not as a module
CODE_FEATURES = code("features", "stages")
CODE_CLASSIFY = code("classify", "data", "stages")
CODE_EVALUATE = code("evaluate", "data", "stages")
CODE_REPORT = code("report", "stages")          # figures never depend on the estimators

TEST_FILES = sorted(str(p) for p in Path("tests").glob("*.py"))

SMOKE = f"{OUT}/smoke_ok.txt"
SAMPLES = expand(f"{OUT}/sample/{{dataset}}.json", dataset=DATASETS)
PROMPTS = expand(f"{OUT}/prompts/{{dataset}}.json", dataset=DATASETS)
PROMPTS_TXT = expand(f"{OUT}/prompts_txt/{{dataset}}.txt", dataset=DATASETS)

MODELS = list(config["vlm"]["models"])
READERS = list(config["vlm"].get("readers", {}))     # H4, H6, H7: model + effort, on a prefix
# Which readers speak the gateway dialect (max_completion_tokens, a service tier, no temperature).
# Derived from config rather than listed, so adding a reader cannot leave the rule behind.
GATEWAY_READERS = [r for r, spec in config["vlm"].get("readers", {}).items()
                   if spec.get("api") == "gateway"]
PRIMARY = config["vlm"]["primary"]
CHUNK = config["vlm"]["chunk"]


def slug(model):
    """A model name as a rule name and a resource name: `qwen3.8-27b-fp8` is neither."""
    return re.sub(r"[^a-z0-9]+", "_", model.lower())


def split_n(dataset, split):
    """How many images a dataset's sample of `split` holds: config's size, capped at the official
    split (breastmnist has 156 test and 546 train images, retinamnist 400 and 1080; WORKFLOW.md
    section 4). The sample stage draws the same number, so the chunk count here and the rows in
    the cache agree by construction."""
    wanted = config["sample"]["test_n" if split == "test" else "pool_n"]
    return min(wanted, RELEASE[dataset]["n_samples"]["test" if split == "test" else "train"])


def chunk_ids(dataset, split, n=None):
    """The chunk numbers one dataset's split is cut into, zero-padded so they sort.

    `n` overrides the split's size for a reader that scores only a prefix of it (H4)."""
    if n is None:
        n = split_n(dataset, split)
    return [f"{k:02d}" for k in range((n + CHUNK - 1) // CHUNK)]


def score_cells(model=None):
    """Every (dataset, model, split, prompt, chunk) the fan-out covers.

    `splits` per model comes from config, because arm B is training-free and only the primary model
    ever needs the labelled pool. The zero-shot prompt is the primary model's alone and on the test
    split alone: arm A is H2's baseline, not one more arm per model."""
    cells = []
    for name in ([model] if model else MODELS):
        for split in config["vlm"]["models"][name]["splits"]:
            for dataset in DATASETS:
                if dataset in MULTI_LABEL and name != PRIMARY:
                    continue                    # no arm B, so the ladder has nothing to score
                zero_shot = name == PRIMARY and split == "test" and dataset not in MULTI_LABEL
                for prompt in ["concept"] + (["zero_shot"] if zero_shot else []):
                    for chunk in chunk_ids(dataset, split):
                        cells.append(f"{OUT}/score/{dataset}__{name}__{split}__{prompt}"
                                     f"__chunk{chunk}.json")
    return cells


def reader_cells(reader=None):
    """Every chunk of H4's readers: the concept prompt on a prefix of the test split.

    A reader scores no pool and asks no zero-shot question. It needs neither: H4 is read through
    the concept answers alone (the cross-validated probe of WORKFLOW.md section 3), and arm A is
    not a property of a reader but of the one model that was asked for a diagnosis.
    """
    cells = []
    for name in ([reader] if reader else READERS):
        spec = config["vlm"]["readers"][name]
        for dataset in DATASETS:
            if dataset in MULTI_LABEL:
                continue                        # the probe H4 reads is not defined over findings
            for chunk in chunk_ids(dataset, "test", min(spec["subsample"], split_n(dataset, "test"))):
                cells.append(f"{OUT}/score/{dataset}__{name}__test__concept__chunk{chunk}.json")
    return cells


SCORES = score_cells() + reader_cells()
SCORE_TABLES = expand(f"{OUT}/scores/{{dataset}}.json", dataset=DATASETS)
FEATURES = expand(f"{OUT}/features/{{dataset}}.json", dataset=DATASETS)
CLASSIFIED = expand(f"{OUT}/classify/{{dataset}}.json", dataset=DATASETS)
EVALUATED = expand(f"{OUT}/evaluate/{{dataset}}.json", dataset=DATASETS)
EVALUATION = f"{OUT}/evaluation.json"
FIGS, TABS = config["figdir"], config["tabdir"]
FIG_FILES = (expand(f"{FIGS}/fig_{{f}}.png",
                    f=["curve", "n_b", "ladder", "readers", "thinking", "h5", "h6", "h7"])
             # One montage per dataset for the sampled-image appendix.
             + expand(f"{FIGS}/fig_samples_{{dataset}}.png", dataset=DATASETS))
TABLE_TEX = expand(f"{TABS}/{{t}}.tex",
                   t=["h1", "h2", "h3", "h4", "h5", "h6h7", "literature", "completeness",
                      "features", "appendix_prompts", "appendix_samples", "numbers"])

wildcard_constraints:
    dataset="|".join(DATASETS),
    # Readers are named `<model>-<effort>`, so the model alternatives have to be tried longest
    # first or `qwen3.8-27b-fp8` would match the head of `qwen3.8-27b-fp8-medium` and two rules
    # would claim one file.
    model="|".join(re.escape(m) for m in sorted(MODELS + READERS, key=len, reverse=True)),


# ---- targets: one phony target per stage; `all` becomes the technical report at stage 6 --------
rule all:
    input: "report/report.pdf"

rule sample:
    input: SAMPLES

rule prompts:
    input: PROMPTS

rule prompts_txt:
    """Opt-in, outside `all`: a human-readable txt render of every dataset's prompts, decides no
    hypothesis (WORKFLOW.md section 7)."""
    input: PROMPTS_TXT

rule score:
    input: SCORE_TABLES

rule features:
    input: FEATURES

rule classify:
    input: CLASSIFIED

rule evaluate:
    input: EVALUATION

rule report:
    """Tables and figures without the PDF."""
    input: TABLE_TEX, FIG_FILES


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
        literature=config["literature"],
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
#
# Eight of the twelve release files were downloaded, checksummed and set aside before the workflow
# existed; the four the talk version never needed (chestmnist, organcmnist, organsmnist,
# tissuemnist) are fetched by the rule below from the same pinned record, in parallel byte ranges
# because Zenodo serves about 105 KB/s per connection, resumable, and checked against the MD5 the
# release description carries. A file already on disk is never fetched again.
# =====================================================================================

RAW_FILES = sorted(RELEASE[d]["file"] for d in DATASETS)


def described(file):
    """The release entry behind one file name."""
    return next(RELEASE[d] for d in DATASETS if RELEASE[d]["file"] == file)


def segments(file):
    """Parallel byte ranges for one release file: one per fetch.segment_mb, at most
    fetch.max_segments. chestmnist_224.npz (3.9 GB) is 15 ranges, so about 40 minutes at Zenodo's
    per-connection rate where one stream would take ten hours."""
    f = config["fetch"]
    per_segment = int(f["segment_mb"]) * 2 ** 20
    return max(1, min(int(f["max_segments"]), -(-described(file)["size_bytes"] // per_segment)))


rule fetch:
    """One release file from the pinned record, in parallel byte ranges, MD5-checked. Runs only
    for a file that is not on disk. x4 from the talk version's storage root."""
    output: f"{config['rawdir']}/{{file}}"
    wildcard_constraints:
        file="|".join(re.escape(f) for f in RAW_FILES),
    params:
        url=lambda w: f"{ZENODO}/files/{w.file}?download=1",
        md5=lambda w: described(w.file)["md5_224"],
        bytes=lambda w: described(w.file)["size_bytes"],
        segments=lambda w: segments(w.file),
    log: "logs/fetch/{file}.log"
    benchmark: "benchmarks/fetch/{file}.tsv"
    threads: RES["fetch"]["cpus"]
    resources: **res("fetch"), zenodo=lambda w: segments(w.file)
    shell:
        "scripts/fetch_medmnist.sh {params.url} {params.md5} {params.bytes} {params.segments} "
        "{output} " + config["storage_root"] + " > {log} 2>&1"


rule sample_dataset:
    """One dataset's test sample and labelled pool, streamed out of its release file. x6."""
    input:
        raw=lambda w: f"{config['rawdir']}/{RELEASE[w.dataset]['file']}",
        release=config["release"],
        smoke=SMOKE,
        code=CODE_SAMPLE,
    params:
        test_n=lambda w: split_n(w.dataset, "test"),
        pool_n=lambda w: split_n(w.dataset, "pool"),
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
        gloss=lambda w: (config["vlm"]["prompt"].get("class_gloss") or {}).get(w.dataset),
    output: f"{OUT}/prompts/{{dataset}}.json"
    log: "logs/render_prompts/{dataset}.log"
    conda: "envs/priors.yml"
    shell: STAGE + "render-prompts {wildcards.dataset} --out {output} > {log} 2>&1"


rule render_prompts_txt:
    """One dataset's rendered prompts as plain text, for a human reader. x6, local, opt-in (build
    with `prompts_txt`, WORKFLOW.md section 7): formats the JSON `render_prompts` already wrote,
    so the text a person reads is the same artifact hashed into every score manifest rather than a
    second copy of the prompt logic. Decides no hypothesis and feeds no rule below it."""
    input:
        rendered=f"{OUT}/prompts/{{dataset}}.json",
        code=CODE_PROMPTS_TXT,
        smoke=SMOKE,
    output: f"{OUT}/prompts_txt/{{dataset}}.txt"
    log: "logs/render_prompts_txt/{dataset}.log"
    conda: "envs/priors.yml"
    shell: STAGE + "prompts-txt {wildcards.dataset} --out {output} > {log} 2>&1"


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


SCORE_CMD = STAGE + ("score {wildcards.dataset} {wildcards.model} {wildcards.split}"
                     " {wildcards.prompt} {wildcards.chunk} --out {output} > {log} 2>&1")


# One rule per model rather than one rule with a model wildcard, because each model gets its own
# `llm_<model>` resource and Snakemake resource names are fixed per rule. The cap for each lives in
# profiles/palmetto/config.yaml, below the concurrency the service publishes; a job holds one unit
# for as long as it runs, so the number of jobs in flight for a model is the number of calls in
# flight for it. The smoke tier checks the profile's caps against config's.
#
# Written out four times rather than generated in a loop, and the repetition is deliberate. The
# loop version ran once and wrote gemma-4-31b's answers into the file named for the primary model:
# each generated rule kept its own `output:` but they all shared the LAST iteration's `shell:`, and
# Snakemake printed the command it had not run. Four explicit rules cannot do that, and the model
# each one names is visible in the rule the reader is looking at. The stage refuses a mismatch
# between the model it is told to use and the file it is told to write, so the same class of error
# now fails before the first call rather than after a hundred.

rule score_qwen3_5_9b:
    """One chunk of qwen3.5-9b: a hundred images, one prompt. x30."""
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
    wildcard_constraints:
        model="qwen3\.5\-9b",
    # protected(): the file is read-only once written, which is principle 7 with teeth. Re-scoring
    # then costs an explicit chmod, so 27,000 calls cannot be spent again by a stray rerun.
    output: protected(f"{OUT}/score/{{dataset}}__{{model}}__{{split}}__{{prompt}}__chunk{{chunk}}.json")
    log: "logs/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.log"
    benchmark: "benchmarks/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.tsv"
    conda: "envs/priors.yml"
    threads: RES["score"]["cpus"]
    resources: **res("score"), **{"llm_qwen3_5_9b": 1}
    shell: SCORE_CMD


rule score_gemma_4_12b:
    """One chunk of gemma-4-12b: a hundred images, one prompt. x30."""
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
    wildcard_constraints:
        model="gemma\-4\-12b",
    # protected(): the file is read-only once written, which is principle 7 with teeth. Re-scoring
    # then costs an explicit chmod, so 27,000 calls cannot be spent again by a stray rerun.
    output: protected(f"{OUT}/score/{{dataset}}__{{model}}__{{split}}__{{prompt}}__chunk{{chunk}}.json")
    log: "logs/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.log"
    benchmark: "benchmarks/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.tsv"
    conda: "envs/priors.yml"
    threads: RES["score"]["cpus"]
    resources: **res("score"), **{"llm_gemma_4_12b": 1}
    shell: SCORE_CMD


rule score_qwen3_8_27b_fp8:
    """One chunk of qwen3.8-27b-fp8: a hundred images, one prompt. x180. The primary model: the only one that scores the labelled pool,
    and the only one asked the zero-shot prompt (arm A)."""
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
    wildcard_constraints:
        model="qwen3\.8\-27b\-fp8",
    # protected(): the file is read-only once written, which is principle 7 with teeth. Re-scoring
    # then costs an explicit chmod, so 27,000 calls cannot be spent again by a stray rerun.
    output: protected(f"{OUT}/score/{{dataset}}__{{model}}__{{split}}__{{prompt}}__chunk{{chunk}}.json")
    log: "logs/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.log"
    benchmark: "benchmarks/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.tsv"
    conda: "envs/priors.yml"
    threads: RES["score"]["cpus"]
    resources: **res("score"), **{"llm_qwen3_8_27b_fp8": 1}
    shell: SCORE_CMD


rule score_gemma_4_31b:
    """One chunk of gemma-4-31b: a hundred images, one prompt. x30."""
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
    wildcard_constraints:
        model="gemma\-4\-31b",
    # protected(): the file is read-only once written, which is principle 7 with teeth. Re-scoring
    # then costs an explicit chmod, so 27,000 calls cannot be spent again by a stray rerun.
    output: protected(f"{OUT}/score/{{dataset}}__{{model}}__{{split}}__{{prompt}}__chunk{{chunk}}.json")
    log: "logs/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.log"
    benchmark: "benchmarks/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.tsv"
    conda: "envs/priors.yml"
    threads: RES["score"]["cpus"]
    resources: **res("score"), **{"llm_gemma_4_31b": 1}
    shell: SCORE_CMD


# ---- H4's two readers: the same concept prompt, read differently ------------------------------
#
# A *reader* is a model plus a reasoning effort (WORKFLOW.md section 2). The four rules above are
# readers at effort `none`, which is what the whole existing archive was bought under. These two
# are the new ones, and each scores the concept prompt on the first 200 images of the same seeded
# test sample - so the four archives above join H4 by being subset, not by being re-bought.
#
# Two rules rather than one because the dialects differ, and the difference is worth seeing in the
# rule a reader is looking at: the local model takes `max_tokens` and holds a unit of the primary
# model's own `llm_` resource, because it is the same endpoint under a different setting and two
# rules pointed at one endpoint must share one cap. The gateway model is somebody else's capacity,
# metered in credits rather than in concurrency, so it gets a resource of its own.

rule score_reader:
    """One chunk of a thinking reader on the local service: a hundred images, concept prompt. x12."""
    input:
        prompts=f"{OUT}/prompts/{{dataset}}.json",
        sample=f"{OUT}/sample/{{dataset}}.json",
        arrays=f"{config['cachedir']}/{{dataset}}.npz",
        smoke=SMOKE,
        code=CODE_SCORE,
    params:
        chunk_size=CHUNK,
        temperature=config["vlm"]["temperature"],
        reader=lambda w: config["vlm"]["readers"][w.model],
        retries=config["vlm"]["retries"],
    wildcard_constraints:
        model="qwen3\.8\-27b\-fp8\-medium",
        split="test",
        prompt="concept",
    output: protected(f"{OUT}/score/{{dataset}}__{{model}}__{{split}}__{{prompt}}__chunk{{chunk}}.json")
    log: "logs/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.log"
    benchmark: "benchmarks/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.tsv"
    conda: "envs/priors.yml"
    threads: RES["score_reader"]["cpus"]
    # Its own resource rather than the primary model's, capped at 4 in the profile. It is the same
    # endpoint, so the two caps have to be read together as a promise about total concurrency; it
    # gets its own because a thinking chunk is an order of magnitude longer than a thinking-off one
    # and needs to be throttled harder to finish inside its time limit, which one shared cap cannot
    # express. Nothing else is scheduled against this model while H4's readers run.
    resources: **res("score_reader"), **{"llm_reader_medium": 1}
    shell: SCORE_CMD


rule score_reader_gateway:
    """One chunk of a gateway reader: a hundred images, concept prompt. x88 over four readers."""
    input:
        prompts=f"{OUT}/prompts/{{dataset}}.json",
        sample=f"{OUT}/sample/{{dataset}}.json",
        arrays=f"{config['cachedir']}/{{dataset}}.npz",
        smoke=SMOKE,
        code=CODE_SCORE,
    params:
        chunk_size=CHUNK,
        temperature=config["vlm"]["temperature"],
        reader=lambda w: config["vlm"]["readers"][w.model],
        retries=config["vlm"]["retries"],
    wildcard_constraints:
        model="|".join(re.escape(m) for m in sorted(GATEWAY_READERS, key=len, reverse=True)),
        split="test",
        prompt="concept",
    output: protected(f"{OUT}/score/{{dataset}}__{{model}}__{{split}}__{{prompt}}__chunk{{chunk}}.json")
    log: "logs/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.log"
    benchmark: "benchmarks/score/{dataset}__{model}__{split}__{prompt}__chunk{chunk}.tsv"
    conda: "envs/priors.yml"
    threads: RES["score_reader_gateway"]["cpus"]
    resources: **res("score_reader_gateway"), **{"llm_gateway": 1}
    shell: SCORE_CMD


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
# 3  FEATURES
#
# Arm P's half of the H1 comparison. A vision-language model is an enormous pretrained model, so
# the fair pixel baseline is pretrained too: frozen ImageNet ResNet-18 features under the same
# classifier, the same regularisation search and the same labelled subsets as arm C, so that the
# features are the only difference between the two curves.
#
# Nothing is trained here and nothing is random. The weights are a fixed input like the releases:
# they live under storage_root/torch_home, which the rule passes as TORCH_HOME, so no job needs the
# internet and every run uses the same bytes. Torch enters in its own environment and nowhere else.
# =====================================================================================

rule pixel_features:
    """Frozen ImageNet features of one dataset's sampled images. x6."""
    input:
        sample=f"{OUT}/sample/{{dataset}}.json",
        arrays=f"{config['cachedir']}/{{dataset}}.npz",
        smoke=SMOKE,
        code=CODE_FEATURES,
    params:
        arch=config["features"]["arch"],
        weights=config["features"]["weights"],
        batch=config["features"]["batch"],
    output:
        json=f"{OUT}/features/{{dataset}}.json",
        arrays=f"{config['featuredir']}/{{dataset}}.npz",
    log: "logs/features/{dataset}.log"
    benchmark: "benchmarks/features/{dataset}.tsv"
    conda: "envs/priors_torch.yml"
    threads: RES["features"]["cpus"]
    resources: **res("features")
    shell:
        "export TORCH_HOME=" + config["torch_home"] + "; " + STAGE +
        "features {wildcards.dataset} --out {output.json} --arrays {output.arrays} > {log} 2>&1"


# =====================================================================================
# 4  CLASSIFY
#
# The four arms, on the same 500 test images, so that every comparison the study makes is paired.
# Arms A and B use no labels; C and P are the same regularised logistic regression on different
# features, over class-stratified nested subsets of the labelled pool at six sizes and three seeds.
#
# The permutation controls live here too, because they are re-analyses of the archive and cost no
# calls: arm B's fingerprints attached to the wrong classes, and arm C's concept columns shuffled
# across images. If either arm survives its control, it was not reading what it claims to read.
#
# Nothing is measured in this stage. It writes scores and the evaluate stage turns them into AUCs,
# because the paired bootstrap has to resample the test images once for every arm at the same time.
# =====================================================================================

rule classify_dataset:
    """Every arm's scores on the test sample, for one dataset. x6."""
    input:
        scores=f"{OUT}/scores/{{dataset}}.json",
        features=f"{OUT}/features/{{dataset}}.json",
        feature_arrays=f"{config['featuredir']}/{{dataset}}.npz",
        sample=f"{OUT}/sample/{{dataset}}.json",
        arrays=f"{config['cachedir']}/{{dataset}}.npz",
        prompts=f"{OUT}/prompts/{{dataset}}.json",
        bank=lambda w: f"{config['conceptdir']}/{w.dataset}.yaml",
        smoke=SMOKE,
        code=CODE_CLASSIFY,
    params:
        curve_n=",".join(str(n) for n in config["curve"]["n"]),
        curve_seeds=",".join(str(s) for s in config["curve"]["seeds"]),
        l2_grid=",".join(str(c) for c in config["classify"]["l2_grid"]),
        cv_folds=config["classify"]["cv_folds"],
        permute_seeds=",".join(str(s) for s in config["classify"]["permute"]["seeds"]),
    output:
        json=f"{OUT}/classify/{{dataset}}.json",
        arrays=f"{OUT}/classify/{{dataset}}.npz",
    log: "logs/classify/{dataset}.log"
    benchmark: "benchmarks/classify/{dataset}.tsv"
    conda: "envs/priors.yml"
    threads: RES["classify"]["cpus"]
    resources: **res("classify")
    shell: STAGE + "classify {wildcards.dataset} --out {output.json} --arrays {output.arrays} > {log} 2>&1"


# =====================================================================================
# 5  EVALUATE
#
# Where the arms become numbers. One bootstrap per dataset, shared by every arm: a replicate
# resamples the 500 test images once and every arm is recomputed on that same resample, so the
# interval on a difference contains only the noise that does not cancel. That is the whole reason
# the study fixes one test sample and makes every arm predict on it.
#
# n_B is computed here: the smallest grid n at which the pixel probe's seed-mean AUC reaches the
# zero-label textbook arm, with `<=50` and `>2000` coded rather than clipped, because "already
# above at the first point" and "never gets there" are different facts from a number.
#
# The across-dataset rule then applies the decision rules of WORKFLOW.md section 2 as written -
# one-sided sign tests over six datasets, the within-family reading of the ladder - and says
# supported or not, with the per-dataset differences beside it where the reading actually lives.
# =====================================================================================

rule evaluate_dataset:
    """AUC per arm, the paired bootstrap, and n_B, for one dataset. x6."""
    input:
        classify=f"{OUT}/classify/{{dataset}}.json",
        arrays=f"{OUT}/classify/{{dataset}}.npz",
        release=config["release"],
        smoke=SMOKE,
        code=CODE_EVALUATE,
    params:
        bootstrap=config["evaluate"]["bootstrap"],
        ci=config["evaluate"]["ci"],
        seed=config["evaluate"]["seed"],
        curve_n=",".join(str(n) for n in config["curve"]["n"]),
    output: f"{OUT}/evaluate/{{dataset}}.json"
    log: "logs/evaluate/{dataset}.log"
    benchmark: "benchmarks/evaluate/{dataset}.tsv"
    conda: "envs/priors.yml"
    threads: RES["evaluate"]["cpus"]
    resources: **res("evaluate")
    shell: STAGE + "evaluate {wildcards.dataset} --out {output} > {log} 2>&1"

rule evaluate_across:
    """The five hypotheses, decided by the rules fixed before the numbers existed. x1, local."""
    input:
        per_dataset=EVALUATED,
        code=CODE_EVALUATE,
    params:
        alpha=config["evaluate"]["alpha"],
        datasets=",".join(DATASETS),
    output: EVALUATION
    log: "logs/evaluate_across.log"
    conda: "envs/priors.yml"
    shell: STAGE + "evaluate-across --out {output} > {log} 2>&1"


# =====================================================================================
# 6  REPORT
#
# The technical report is the complete record of what was computed: the question, the provenance,
# the methods as executed, every table and figure, the diagnostics and the run record. It is not a
# manuscript - interpretation stays with the authors - and no number in it is typed by hand. Every
# table is generated into report/tables/, and the sentences whose direction depends on a value read
# a macro from numbers.tex, so the prose cannot state something the run did not produce.
#
# One table reads a fixed input rather than results/ alone: `literature`, this study's zero-label
# and largest-labelled-subset arms against published, fully supervised numbers for the same six
# tasks (data/literature/benchmarks.yaml, WORKFLOW.md section 10). It is an extension -
# cheap, decides no hypothesis - and sits in `rule all` for the same reason: nothing here is
# recomputed, only read alongside numbers the workflow already produced.
# =====================================================================================

rule tables:
    """Every table and number macro, from results/ alone. x1, local."""
    input:
        evaluation=EVALUATION, per_dataset=EVALUATED, code=CODE_REPORT,
        # The feature-dimension table reads the classify stage's own record of the matrices it
        # fitted, and the appendix reads the rendered prompts the archive was hashed against, so
        # both are declared here rather than reached for behind Snakemake's back.
        classify=CLASSIFIED, prompts=PROMPTS,
        literature=config["literature"],
    output: TABLE_TEX
    log: "logs/tables.log"
    conda: "envs/priors.yml"
    shell: STAGE + "tables --dest " + TABS + " > {log} 2>&1"

rule figures:
    """Six figures plus a sampled-image montage per dataset. x1."""
    input:
        evaluation=EVALUATION, per_dataset=EVALUATED, code=CODE_REPORT,
        # The montages draw the cached sample arrays every arm was scored on, and name their rows
        # from the rendered prompts, so both are declared rather than reached for.
        arrays=expand(f"{config['cachedir']}/{{dataset}}.npz", dataset=DATASETS),
        prompts=PROMPTS,
        literature=config["literature"],
    output: FIG_FILES
    log: "logs/figures.log"
    benchmark: "benchmarks/figures.tsv"
    conda: "envs/priors.yml"
    threads: RES["report"]["cpus"]
    resources: **res("report")
    shell: STAGE + "figures --dest " + FIGS + " > {log} 2>&1"

rule technical_report:
    """The PDF, from the generated tables and figures. x1."""
    input: tex="report/report.tex", bib="report/references.bib", tables=TABLE_TEX, figs=FIG_FILES
    output: "report/report.pdf"
    log: "logs/technical_report.log"
    threads: RES["report_pdf"]["cpus"]
    resources: **res("report_pdf")
    shell:
        # pdflatex, bibtex, pdflatex twice more: the later passes resolve the citations and the
        # references. The last line asserts the document was finished, because a pdflatex that dies
        # part-way still leaves a readable PDF behind. TeX runs without the login environment's
        # LD_LIBRARY_PATH: a spack zlib-ng there is an illegal instruction on the older nodes.
        "cd report && " + TEX + "pdflatex -interaction=nonstopmode -halt-on-error report.tex > ../{log} 2>&1 "
        "&& (" + TEX + "bibtex report >> ../{log} 2>&1 || test $? -lt 2) "
        "&& " + TEX + "pdflatex -interaction=nonstopmode -halt-on-error report.tex >> ../{log} 2>&1 "
        "&& " + TEX + "pdflatex -interaction=nonstopmode -halt-on-error report.tex >> ../{log} 2>&1 "
        "&& grep -q 'Output written on report.pdf' ../{log}"


# =====================================================================================
# Extensions (WORKFLOW.md section 10), each one rule and a config block if ever wanted, none
# built: bare_levels, generic_prompt, primary_upgrade, reasoning_sweep.
# =====================================================================================
