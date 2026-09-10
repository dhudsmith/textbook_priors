# =====================================================================================
# Textbook priors over visual features: can a vision-language model's textbook knowledge of what
# pathology looks like stand in for labelled images? (WORKFLOW.md)
#
#     snakemake --profile profiles/palmetto                 # everything, on SLURM: the report
#     snakemake --profile profiles/palmetto -n              # dry run: inspect the DAG
#     snakemake --profile profiles/local -j 2 smoke         # the tests, seconds
#     snakemake --profile profiles/palmetto cache           # one stage by name
#     snakemake --profile profiles/palmetto results/score_probe/probe.json   # the ten-image probe
#
# The workflow reads top to bottom through nine stages:
#
#   0  SMOKE      bank schema, anchors and label maps, both prompts, the arm-B estimator on a
#                 fixture, metric conventions, client retry; the torch tier's checks separately
#   1  FETCH      MedMNIST from the pinned Zenodo record, MD5-checked; data/raw on scratch
#   2  CACHE      per dataset x {224, 28}: uint8 arrays per official split, streamed to .npy;
#                 the seeded test sample and labelled pool at 224
#   3  SCORE      per dataset x model x split x prompt x chunk of 100: concept levels, or the
#                 zero-shot class distribution; every raw response archived and protected
#   4  FEATURES   per dataset: ImageNet ResNet-18 penultimate features of the sampled images
#   5  TRAIN      per dataset x {224, 28} x seed: ResNet-18 from scratch on the official splits
#   6  CLASSIFY   per dataset: arms A, B, C, P at every n and seed, plus the permutation controls
#   7  EVALUATE   every arm through the medmnist evaluator; the paired bootstrap; n_B; then the
#                 sign tests and the H3 ladder analysis across datasets
#   8  REPORT     reconciliation against the published table; three figures, tables, number
#                 macros, the technical report
#
# Every unit of work is one entry point of priors/stages.py, a pure function of its inputs, its
# config values and its own seed, writing one JSON with a run manifest (arrays beside it). Tables
# and figures read only those files. Resources per rule come from config/config.yaml and are set
# from the benchmarks/ each job writes.
# =====================================================================================

import math
import os
import re

import yaml

configfile: "config/config.yaml"

_RELEASE = yaml.safe_load(open(config["release"]))
RELEASE = _RELEASE["datasets"]
RECORD = _RELEASE["record"]

# Seconds-long bookkeeping runs in the submitting process rather than paying a SLURM round-trip.
# Anything with a real toolchain or a real cost is submitted so it runs with declared resources.
localrules:
    all, smoke_target, cache_target, score_target, features_target, train_target, classify_target,
    evaluate_target, report_target, fetch_weights,


OUT = config["outdir"]
STORAGE = config["storage_root"]
RAW = config["rawdir"]
CACHE = config["cachedir"]
FIGS = config["figdir"]
TABS = config["tabdir"]
RES = config["resources"]
DATASETS = config["datasets"]
ARM_B = [ds for ds in DATASETS if ds not in config["arm_b_exclude"]]
VLM = config["vlm"]
MODELS = list(VLM["models"])
PRIMARY = VLM["primary"]
SIZE = int(config["size"])
SIZES = [int(s) for s in config["recon_sizes"]]
CURVE_SEEDS = config["curve"]["seeds"]
TRAIN_SEEDS = config["train"]["seeds"]

# BLAS sizes its thread pool from the machine, not the cgroup; pin it to the allocation.
PIN = "export OMP_NUM_THREADS={threads} MKL_NUM_THREADS={threads} OPENBLAS_NUM_THREADS={threads}; "
STAGE = PIN + "python -m priors.stages "

# pdflatex loads libz; this cluster's login environment puts a spack zlib-ng ahead of the system
# library that is an illegal instruction on the older compute nodes (research-workflow skill,
# references/palmetto.md).
TEX = "env -u LD_LIBRARY_PATH "


def res(name):
    """Per-rule resources from config, as the keyword arguments `resources:` wants."""
    r = RES[name]
    return dict(mem_mb=r["mem_mb"], runtime=r["runtime"], cpus_per_task=r["cpus"])


def code(*modules):
    """The priors modules whose contents determine a rule's output.

    Snakemake's `code` rerun trigger inspects the rule's own shell line, not the Python it invokes,
    so editing a module leaves downstream outputs stale without notice. Listing the modules puts
    them under the ordinary input trigger. Keep these lists minimal: adding classify.py to a figure
    rule would refit the project when a colour changes. The config is deliberately NOT listed; the
    values a rule's numbers depend on are declared as params instead (tracked value by value)."""
    return [f"priors/{m}.py" for m in modules]


def slug(model):
    """A model name as a Snakemake resource name: qwen3.8-27b-fp8 -> qwen3_8_27b_fp8."""
    return re.sub(r"[^0-9A-Za-z]+", "_", model)


def sample_n(ds, split):
    """The sampled split size: min(config, official split), test from test and pool from train."""
    s = config["sample"]
    return min(int(s["test_n"]), int(RELEASE[ds]["n_samples"]["test"])) if split == "test" \
        else min(int(s["pool_n"]), int(RELEASE[ds]["n_samples"]["train"]))


def nchunks(n):
    return math.ceil(n / int(VLM["chunk"]))


def gpu_res(section, base):
    """The base request, or the section's GPU request with Palmetto2's --gpus syntax when enabled.
    The executor passes slurm_extra verbatim to sbatch; the quoting matters."""
    g = section["gpu"]
    r = dict(res(base))
    if g["enabled"]:
        r.update(cpus_per_task=g["cpus"], mem_mb=g["mem_mb"], runtime=g["runtime"],
                 slurm_extra=f"'--gpus={g['type']}:1'")
    return r


def train_mem_mb(ds, size):
    """A training job holds every split of the dataset in RAM as uint8 (WORKFLOW.md section 8 says
    cache the full split, never cap it), so its memory is the array size: n x size^2 x channels
    bytes, times 1.3 for the torch copies and the prediction matrices, plus 8 GB for torch, CUDA
    and the model. pathmnist at 224 is 16 GB of images and asks for ~29 GB; the config floor covers
    the small ones."""
    n = sum(RELEASE[ds]["n_samples"].values())
    ch = int(RELEASE[ds]["n_channels"])
    array_mb = n * int(size) ** 2 * ch / 2 ** 20
    return int(max(config["train"]["gpu"]["mem_mb"], 1.3 * array_mb + 8000))


def train_res(w):
    r = gpu_res(config["train"], "features")
    r["mem_mb"] = train_mem_mb(w.dataset, w.size)
    return r


def score_params():
    """Config values a scoring chunk's answers depend on. Changing one flags the archive; since the
    archive is protected(), that is a stop and a decision rather than a silent re-score."""
    v = VLM
    return dict(temperature=v["temperature"], reasoning=v["reasoning"], reasoning_extra_body=str(v.get("reasoning_extra_body")),
                json_mode=str(v.get("json_mode")), max_tokens=v.get("max_tokens"), anchors=v["prompt"]["anchors"],
                retries=v["retries"], zeroshot_names=str(v.get("zeroshot_names")))


def classify_params():
    c = config["classify"]
    return dict(l2_grid=",".join(map(str, c["l2_grid"])), l2_default=c["l2_default"], cv_folds=c["cv_folds"],
                missing_max_frac=c["missing_max_frac"], permute_seeds=",".join(map(str, c["permute"]["seeds"])),
                curve_n=",".join(map(str, config["curve"]["n"])), curve_seeds=",".join(map(str, CURVE_SEEDS)),
                primary=PRIMARY, models=",".join(MODELS))


def train_params():
    t = config["train"]
    return dict(**{k: str(t[k]) for k in ("arch", "pretrained", "epochs", "batch", "lr", "milestones", "gamma", "select_on", "amp")})


CODE_CACHE = code("data", "cache", "stages")
CODE_SCORE = code("data", "prompts", "llm", "score", "stages")
CODE_FEATURES = code("data", "features", "stages")
CODE_TRAIN = code("data", "train", "stages")
CODE_CLASSIFY = code("data", "classify", "evaluate", "stages")   # classify picks L2 by evaluate.macro_auc
CODE_EVALUATE = code("data", "evaluate", "stages")
CODE_REPORT = code("data", "report", "stages")

# ---- the cell grids, from config ---------------------------------------------------------------
RAW_NAMES = {RELEASE[ds]["files"][s]["name"]: (ds, s) for ds in DATASETS for s in SIZES}
RAW_FILES = [f"{RAW}/{name}" for name in RAW_NAMES]
CACHE_JSON = expand(f"{CACHE}/{{dataset}}_{{size}}.json", dataset=DATASETS, size=SIZES)
SAMPLES = expand(f"{CACHE}/{{dataset}}_sample.json", dataset=DATASETS)


def score_files():
    """The archive: concept scores for every (model, dataset, split) the hypotheses read, zero-shot
    distributions for the primary model on the arm-A datasets. The ladder models serve arm B
    alone, so they skip chestmnist; only the primary scores the labelled pool (section 4)."""
    files = []
    for m, mc in VLM["models"].items():
        for ds in (DATASETS if m == PRIMARY else ARM_B):
            for split in mc["splits"]:
                files += [f"{OUT}/score/{ds}__{m}__{split}__concept__chunk{k}.json" for k in range(nchunks(sample_n(ds, split)))]
    for ds in ARM_B:
        files += [f"{OUT}/score/{ds}__{PRIMARY}__test__zeroshot__chunk{k}.json" for k in range(nchunks(sample_n(ds, "test")))]
    return files


SCORE_FILES = score_files()
N_CALLS = sum(sample_n(ds, sp) for m, mc in VLM["models"].items() for ds in (DATASETS if m == PRIMARY else ARM_B) for sp in mc["splits"]) \
    + sum(sample_n(ds, "test") for ds in ARM_B)
FEATURE_FILES = expand(f"{OUT}/features/{{dataset}}.json", dataset=DATASETS)
TRAIN_FILES = expand(f"{OUT}/train/{{dataset}}__s{{size}}__seed{{seed}}.json", dataset=DATASETS, size=SIZES, seed=TRAIN_SEEDS)
CLASSIFY_FILES = expand(f"{OUT}/classify/{{dataset}}.json", dataset=DATASETS)
EVALUATE_FILES = expand(f"{OUT}/evaluate/{{dataset}}.json", dataset=DATASETS)
TABLE_TEX = expand(f"{TABS}/{{t}}.tex", t=["h1", "h2", "ladder", "ladder_anova", "reconciliation", "completeness", "numbers"])
FIG_FILES = expand(f"{FIGS}/{{f}}.png", f=["fig_curve", "fig_ladder", "fig_nb"])
WEIGHTS = f"{CACHE}/torch/hub/checkpoints/resnet18-f37072fd.pth"

wildcard_constraints:
    dataset="|".join(DATASETS),
    size="|".join(str(s) for s in SIZES),
    split="test|pool",
    prompt="concept|zeroshot",
    k=r"\d+",
    seed=r"\d+",
    file="|".join(re.escape(n) for n in RAW_NAMES),


# ---- targets: `all` is the report; one phony target per stage ------------------------------------
rule all:
    input: "report/report.pdf"

rule smoke_target:
    input: f"{OUT}/smoke_ok.txt", f"{OUT}/smoke_torch_ok.txt"

rule cache_target:
    input: CACHE_JSON, SAMPLES

rule score_target:
    input: SCORE_FILES

rule features_target:
    input: FEATURE_FILES

rule train_target:
    input: TRAIN_FILES

rule classify_target:
    input: CLASSIFY_FILES

rule evaluate_target:
    input: EVALUATE_FILES, f"{OUT}/evaluate/summary.json"

rule report_target:
    """Tables and figures without the PDF."""
    input: TABLE_TEX, FIG_FILES


# =====================================================================================
# 0  SMOKE
#
# The tests: every rule of CONCEPT_BANK.md over the twelve committed files (schema, anchors,
# label maps against the pinned release, the shared organ concept set, retinamnist's monotone
# grades), both prompt renderers (the concept prompt names no class, the zero-shot prompt no
# concept), the arm-B estimator on a fixture, the rank-based AUC against the medmnist evaluator,
# the crossing codes and the sign-test p-values the plan states, the client's backoff, the streamed
# cache on a tiny npz, and the profile's throttles against the config caps. Seconds, in the light
# tier. The torch tier's checks (model shapes at 28 and 224, one training step, the feature
# extractor) run as a submitted job in the torch environment; features and train depend on it.
# =====================================================================================

rule smoke:
    input: code("data", "cache", "prompts", "llm", "score", "classify", "evaluate", "report", "stages"),
           expand("data/concepts/{dataset}.yaml", dataset=DATASETS), config["release"], "profiles/palmetto/config.yaml"
    output: touch(f"{OUT}/smoke_ok.txt")
    log: "logs/smoke.log"
    conda: "envs/priors.yml"
    shell: "python -m pytest tests -q -x --ignore=tests/test_torch.py > {log} 2>&1"

rule smoke_torch:
    input: code("data", "features", "train"), f"{OUT}/smoke_ok.txt"
    output: touch(f"{OUT}/smoke_torch_ok.txt")
    log: "logs/smoke_torch.log"
    benchmark: "benchmarks/smoke_torch.tsv"
    conda: "envs/priors_torch.yml"
    threads: RES["smoke_torch"]["cpus"]
    resources: **res("smoke_torch")
    shell: PIN + "python -m pytest tests/test_torch.py -q -x > {log} 2>&1"


# =====================================================================================
# 1  FETCH
#
# MedMNIST v2 from Zenodo record 10519652 (data version 3), one job per file, each verified against
# the MD5 the medmnist package records (config/medmnist.yaml). data/raw is a symlink into
# /scratch/$USER, which is purged periodically: a purge makes these rules run again. The 224 files
# are up to ~10 GB, so downloads resume and land atomically, and the `zenodo` resource in the profile
# caps how many run at once.
# =====================================================================================

def release_file(name):
    ds, size = RAW_NAMES[name]
    return RELEASE[ds]["files"][size]


def segments(name):
    """Parallel byte ranges for one file: one per fetch.segment_mb, at most fetch.max_segments. Zenodo
    serves ~105 KB/s per connection, so pathmnist_224.npz (11.8 GB) takes ~2 hours in 24 ranges
    where one stream would take ~31."""
    f = config["fetch"]
    return max(1, min(int(f["max_segments"]), math.ceil(release_file(name)["bytes"] / (int(f["segment_mb"]) * 2 ** 20))))


rule fetch:
    """One release file from the pinned record, in parallel byte ranges, MD5-checked. x{len(RAW_FILES)}."""
    output: f"{RAW}/{{file}}"
    params:
        url=lambda w: f"{RECORD}/files/{w.file}?download=1",
        md5=lambda w: release_file(w.file)["md5"],
        bytes=lambda w: release_file(w.file)["bytes"],
        segments=lambda w: segments(w.file),
    log: "logs/fetch/{file}.log"
    benchmark: "benchmarks/fetch/{file}.tsv"
    threads: RES["fetch"]["cpus"]
    resources: **res("fetch"), zenodo=lambda w: segments(w.file)
    shell: "scripts/fetch_medmnist.sh {params.url} {params.md5} {params.bytes} {params.segments} {output} {STORAGE} > {log} 2>&1"

rule fetch_weights:
    """torchvision's ImageNet ResNet-18 weights, pinned by URL and the sha256 prefix in the file
    name, fetched once so twelve features jobs never race for the same download."""
    output: WEIGHTS
    log: "logs/fetch_weights.log"
    shell:
        "curl -sS -L --fail --retry 5 -o {output}.part https://download.pytorch.org/models/resnet18-f37072fd.pth > {log} 2>&1 "
        "&& test \"$(sha256sum {output}.part | cut -c1-8)\" = f37072fd && mv {output}.part {output}"


# =====================================================================================
# 2  CACHE
#
# The npz members are DEFLATE-compressed, so reading one split decompresses it whole into RAM
# (13.5 GB for pathmnist at 224). This stage streams each member into a memory-mappable uint8 .npy
# once, at a memory that does not scale with the dataset, and verifies the split sizes against the
# pinned release. Both sizes are cached in full: a cap on the cached arrays would change what arm E
# trains on and quietly break the reconciliation. The sample rule then draws the seeded test sample
# and labelled pool at 224 by index, with their images, so every later stage reads one small file.
# =====================================================================================

rule cache:
    """One dataset at one size -> six .npy files and their manifest. x{len(CACHE_JSON)}."""
    input: raw=lambda w: f"{RAW}/{RELEASE[w.dataset]['files'][int(w.size)]['name']}", smoke=f"{OUT}/smoke_ok.txt", code=CODE_CACHE
    output: f"{CACHE}/{{dataset}}_{{size}}.json"
    log: "logs/cache/{dataset}_{size}.log"
    benchmark: "benchmarks/cache/{dataset}_{size}.tsv"
    conda: "envs/priors.yml"
    threads: RES["cache"]["cpus"]
    resources: **res("cache")
    shell: f"scripts/link_storage.sh {STORAGE} > {{log}} 2>&1 && " + STAGE + "cache {wildcards.dataset} {wildcards.size} --out {output} >> {log} 2>&1"

rule sample:
    """The seeded test sample (min(500, test)) and labelled pool (min(2000, train)) at 224. x{len(SAMPLES)}."""
    input: cache=f"{CACHE}/{{dataset}}_{SIZE}.json", code=CODE_CACHE
    params: **config["sample"]
    output: f"{CACHE}/{{dataset}}_sample.json"
    log: "logs/cache/{dataset}_sample.log"
    benchmark: "benchmarks/cache/{dataset}_sample.tsv"
    conda: "envs/priors.yml"
    threads: RES["cache"]["cpus"]
    resources: **res("cache")
    shell: STAGE + "sample {wildcards.dataset} --out {output} > {log} 2>&1"


# =====================================================================================
# 3  SCORE
#
# The LLM boundary (WORKFLOW.md section 7). One job is one chunk of 100 sampled images through one
# model with one prompt; each image's raw reply is archived before it is parsed against the bank's
# scales, one retry on a malformed reply, then missing. The concept prompt renders every scale
# level's cited anchor and never names a class; the zero-shot prompt lists the class names and
# never mentions a concept, and the two are separate calls so H2 is a comparison, not a tautology.
# Only the primary model scores the labelled pool; the ladder models score the test sample of the
# arm-B datasets, which is what pays for keeping all twelve datasets (section 4). One rule per model
# so each carries its own llm_<model> throttle; outputs are protected(): a rerun that would rewrite
# the archive stops with an error, and re-scoring becomes a deliberate act.
# =====================================================================================

for _model in MODELS:
    rule:
        name: f"score_{slug(_model)}"
        input: sample=f"{CACHE}/{{dataset}}_sample.json", bank="data/concepts/{dataset}.yaml", smoke=f"{OUT}/smoke_ok.txt", code=CODE_SCORE
        params: model=_model, **score_params()
        output: protected(f"{OUT}/score/{{dataset}}__{_model}__{{split}}__{{prompt}}__chunk{{k}}.json")
        log: f"logs/score/{{dataset}}__{_model}__{{split}}__{{prompt}}__chunk{{k}}.log"
        benchmark: f"benchmarks/score/{{dataset}}__{_model}__{{split}}__{{prompt}}__chunk{{k}}.tsv"
        conda: "envs/priors_llm.yml"
        threads: RES["score"]["cpus"]
        resources: **res("score"), **{f"llm_{slug(_model)}": 1}
        shell: STAGE + "score {wildcards.dataset} {params.model} {wildcards.split} {wildcards.prompt} {wildcards.k} --out {output} > {log} 2>&1"

rule probe:
    """Opt-in, outside `all`: vlm.probe.n images of vlm.probe.dataset on the primary model, after
    checking that every configured model is served. Build with
    snakemake --profile profiles/palmetto results/score_probe/probe.json"""
    input: sample=f"{CACHE}/{VLM['probe']['dataset']}_sample.json", bank=f"data/concepts/{VLM['probe']['dataset']}.yaml",
           smoke=f"{OUT}/smoke_ok.txt", code=CODE_SCORE
    params: **score_params(), probe_n=VLM["probe"]["n"]
    output: f"{OUT}/score_probe/probe.json"
    log: "logs/score_probe/probe.log"
    benchmark: "benchmarks/score_probe/probe.tsv"
    conda: "envs/priors_llm.yml"
    threads: RES["probe"]["cpus"]
    resources: **res("probe"), **{f"llm_{slug(PRIMARY)}": 1}
    shell: STAGE + "probe --out {output} > {log} 2>&1"


# =====================================================================================
# 4  FEATURES
#
# Arm P's features: torchvision's ImageNet ResNet-18, frozen, 512-d penultimate layer, on the same
# test sample and labelled pool. The fair pixel baseline is transfer learning without the textbook,
# sharing the classifier, the regularisation search and the subsets with arm C, so features are the
# only difference (section 3). At most 2,500 images per dataset: CPU by default (features.gpu).
# =====================================================================================

rule features:
    """ImageNet ResNet-18 features of one dataset's sample. x{len(FEATURE_FILES)}."""
    input: sample=f"{CACHE}/{{dataset}}_sample.json", weights=WEIGHTS, smoke=f"{OUT}/smoke_torch_ok.txt", code=CODE_FEATURES
    params: **{k: config["features"][k] for k in ("arch", "weights", "layer")}
    output: f"{OUT}/features/{{dataset}}.json"
    log: "logs/features/{dataset}.log"
    benchmark: "benchmarks/features/{dataset}.tsv"
    conda: "envs/priors_torch.yml"
    threads: config["features"]["gpu"]["cpus"] if config["features"]["gpu"]["enabled"] else RES["features"]["cpus"]
    resources: **gpu_res(config["features"], "features")
    shell: f"export TORCH_HOME={CACHE}/torch; " + STAGE + "features {wildcards.dataset} --out {output} > {log} 2>&1"


# =====================================================================================
# 5  TRAIN
#
# Arm E: ResNet-18 from scratch on the official splits with the published recipe, the fully
# supervised ceiling and the number reconciled against the MedMNIST table before anything else is
# trusted (section 9, step 3). At 28 the MedMNIST ResNet-18 variant, at 224 torchvision's; best
# epoch by validation AUC; evaluated on the full official test split and on the shared sample.
# One A100 per job; memory follows the dataset's array size (train_mem_mb).
# =====================================================================================

rule train:
    """One dataset at one size and seed. x{len(TRAIN_FILES)}."""
    input: cache=f"{CACHE}/{{dataset}}_{{size}}.json", sample=f"{CACHE}/{{dataset}}_sample.json",
           smoke=f"{OUT}/smoke_torch_ok.txt", code=CODE_TRAIN
    params: **train_params()
    output: f"{OUT}/train/{{dataset}}__s{{size}}__seed{{seed}}.json"
    log: "logs/train/{dataset}__s{size}__seed{seed}.log"
    benchmark: "benchmarks/train/{dataset}__s{size}__seed{seed}.tsv"
    conda: "envs/priors_torch.yml"
    threads: config["train"]["gpu"]["cpus"] if config["train"]["gpu"]["enabled"] else RES["features"]["cpus"]
    resources: **{k: v for k, v in gpu_res(config["train"], "features").items() if k != "mem_mb"},
               mem_mb=lambda w: train_mem_mb(w.dataset, w.size)
    shell: STAGE + "train {wildcards.dataset} {wildcards.size} {wildcards.seed} --out {output} > {log} 2>&1"


# =====================================================================================
# 6  CLASSIFY
#
# Every arm's class scores on the shared test sample, one job per dataset, so EVALUATE is uniform
# over arms. A and B are parameter-free readings of the archive (B for every model, with its
# fingerprint-permutation control); C and P are the same L2 logistic regression on nested,
# class-stratified subsets of the pool at every n and seed, L2 chosen by CV inside the n labels,
# with C's column-permutation control. chestmnist skips A and B (section 3).
# =====================================================================================

def classify_inputs(w):
    files = [f for f in SCORE_FILES if os.path.basename(f).startswith(f"{w.dataset}__")]
    return files + [f"{OUT}/features/{w.dataset}.json", f"{CACHE}/{w.dataset}_sample.json", f"data/concepts/{w.dataset}.yaml"]

rule classify:
    """Arms A, B, C, P and the permutation controls for one dataset. x{len(CLASSIFY_FILES)}."""
    input: classify_inputs, code=CODE_CLASSIFY
    params: **classify_params()
    output: f"{OUT}/classify/{{dataset}}.json"
    log: "logs/classify/{dataset}.log"
    benchmark: "benchmarks/classify/{dataset}.tsv"
    conda: "envs/priors.yml"
    threads: RES["classify"]["cpus"]
    resources: **res("classify")
    shell: STAGE + "classify {wildcards.dataset} --out {output} > {log} 2>&1"


# =====================================================================================
# 7  EVALUATE
#
# Test AUC (the primary metric) and ACC from medmnist.evaluator for every arm; a paired bootstrap
# over the test images that yields every interval at once, n_B included, because the predictions
# are fixed; then, across datasets, the one-sided sign tests for H1 and H2 and, for H3, the blocked
# two-way ANOVA of AUC(B) on family x size tier with the planned log10-parameter trend, and the
# Friedman test with Nemenyi post-hoc (section 2). Arm E enters as the ceiling on the sample.
# =====================================================================================

rule evaluate:
    """AUC, ACC, the bootstrap and n_B for one dataset. x{len(EVALUATE_FILES)}."""
    input: classify=f"{OUT}/classify/{{dataset}}.json",
           train=expand(f"{OUT}/train/{{{{dataset}}}}__s{{size}}__seed{{seed}}.json", size=SIZES, seed=TRAIN_SEEDS),
           code=CODE_EVALUATE
    params: bootstrap=config["evaluate"]["bootstrap"], ci=config["evaluate"]["ci"], sample_seed=config["sample"]["seed"], primary=PRIMARY
    output: f"{OUT}/evaluate/{{dataset}}.json"
    log: "logs/evaluate/{dataset}.log"
    benchmark: "benchmarks/evaluate/{dataset}.tsv"
    conda: "envs/priors.yml"
    threads: RES["evaluate"]["cpus"]
    resources: **res("evaluate")
    shell: STAGE + "evaluate {wildcards.dataset} --out {output} > {log} 2>&1"

rule summary:
    """The decision rules of section 2 across datasets: sign tests, the ladder ANOVA, Friedman."""
    input: EVALUATE_FILES, code=CODE_EVALUATE
    params: alpha=config["ladder"]["alpha"], friedman=config["ladder"]["friedman"], models=",".join(MODELS), primary=PRIMARY
    output: f"{OUT}/evaluate/summary.json"
    log: "logs/evaluate/summary.log"
    benchmark: "benchmarks/evaluate/summary.tsv"
    conda: "envs/priors.yml"
    threads: RES["summary"]["cpus"]
    resources: **res("summary")
    shell: STAGE + "summary --out {output} > {log} 2>&1"


# =====================================================================================
# 8  REPORT
#
# Arm E against the published table (principle 10), then every table, number macro and figure the
# technical report states, generated from results/ alone so the document cannot drift from its own
# results. The PDF runs TeX without the login LD_LIBRARY_PATH and asserts the build finished.
# =====================================================================================

rule reconcile:
    """Arm E's full-split AUC and ACC against config/published.yaml, per dataset and size."""
    input: TRAIN_FILES, published=config["published"], code=CODE_REPORT
    params: **config["reconcile"]
    output: f"{OUT}/report/reconciliation.json"
    log: "logs/report/reconcile.log"
    benchmark: "benchmarks/report/reconcile.tsv"
    conda: "envs/priors.yml"
    threads: RES["reconcile"]["cpus"]
    resources: **res("reconcile")
    shell: STAGE + "reconcile --out {output} > {log} 2>&1"

rule tables:
    input: summary=f"{OUT}/evaluate/summary.json", evaluate=EVALUATE_FILES, reconciliation=f"{OUT}/report/reconciliation.json", code=CODE_REPORT
    output: TABLE_TEX
    log: "logs/report/tables.log"
    benchmark: "benchmarks/report/tables.tsv"
    conda: "envs/priors.yml"
    threads: RES["report"]["cpus"]
    resources: **res("report")
    shell: STAGE + f"tables --dest {TABS} > {{log}} 2>&1"

rule figures:
    input: summary=f"{OUT}/evaluate/summary.json", evaluate=EVALUATE_FILES, code=CODE_REPORT
    params: modality_order=",".join(config["modality_order"])
    output: FIG_FILES
    log: "logs/report/figures.log"
    benchmark: "benchmarks/report/figures.tsv"
    conda: "envs/priors.yml"
    threads: RES["report"]["cpus"]
    resources: **res("report")
    shell: STAGE + f"figures --dest {FIGS} > {{log}} 2>&1"

rule paper:
    input: tex="report/report.tex", bib="report/references.bib", tables=TABLE_TEX, figs=FIG_FILES
    output: "report/report.pdf"
    log: "logs/report/paper.log"
    threads: RES["paper"]["cpus"]
    resources: **res("paper")
    shell:
        # pdflatex, bibtex, pdflatex twice more: the later passes resolve citations and references.
        # The last line asserts the document was finished; a pdflatex that dies part-way still
        # leaves a readable PDF behind.
        "cd report && " + TEX + "pdflatex -interaction=nonstopmode -halt-on-error report.tex > ../{log} 2>&1 "
        "&& (" + TEX + "bibtex report >> ../{log} 2>&1 || test $? -lt 2) "
        "&& " + TEX + "pdflatex -interaction=nonstopmode -halt-on-error report.tex >> ../{log} 2>&1 "
        "&& " + TEX + "pdflatex -interaction=nonstopmode -halt-on-error report.tex >> ../{log} 2>&1 "
        "&& grep -q 'Output written on report.pdf' ../{log}"


# =====================================================================================
# EXTENSIONS (WORKFLOW.md section 10) are not rules yet: fusion, description_embedding,
# generic_prompt, primary_upgrade and bare_levels each become one rule and a config block when
# they are wanted, outside `rule all`. bare_levels is a re-score into a second archive.
# =====================================================================================
