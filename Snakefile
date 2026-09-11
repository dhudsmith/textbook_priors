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

from pathlib import Path

configfile: "config/config.yaml"

# Seconds-long bookkeeping runs in the submitting process rather than paying a SLURM round-trip.
# Anything with a real toolchain or a real cost is submitted so it runs with declared resources.
localrules:
    all, prompts, smoke, render_prompts,


OUT = config["outdir"]
DATASETS = config["datasets"]

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


CODE_PROMPTS = code("data", "prompts", "stages")

TEST_FILES = sorted(str(p) for p in Path("tests").glob("*.py"))

SMOKE = f"{OUT}/smoke_ok.txt"
PROMPTS = expand(f"{OUT}/prompts/{{dataset}}.json", dataset=DATASETS)

wildcard_constraints:
    dataset="|".join(DATASETS),


# ---- targets: one phony target per stage; `all` becomes the technical report at stage 6 --------
rule all:
    input: PROMPTS

rule prompts:
    input: PROMPTS


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


# =====================================================================================
# STILL TO COME, in this order, each one tested before the next is written:
#
#   0  smoke              two tiers of it are still missing, and arrive with the code they test:
#                         the arm-B estimator on a fixture (with priors/classify.py) and the LLM
#                         client's retry on a malformed answer (with priors/llm.py)
#   1  sample_dataset     x6, submitted: the seeded test sample and labelled pool, streamed out
#                         of the compressed npz
#   2  probe              opt-in, outside `all`: ten images on the primary model, to prove a
#                         compute node reaches the service and the archive is right
#   2  score_<model>      one rule per model, throttled by an llm_<model> resource; 270 jobs
#   2  collect_scores     x6, local: the chunk archive gathered into one table per dataset
#   3  pixel_features     x6, submitted, the torch environment: ResNet-18 penultimate features
#   4  classify_dataset   x6: arms A, B, C, P over the curve and the permutation controls
#   5  evaluate_dataset   x6: AUC per arm, the paired bootstrap, n_B
#   5  evaluate_across    x1: the sign tests, the ladder, the Friedman test
#   6  figures, tables, technical_report
#
# Extensions (WORKFLOW.md section 10), each outside `all`: bare_levels, generic_prompt,
# primary_upgrade.
# =====================================================================================
