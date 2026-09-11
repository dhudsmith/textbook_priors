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

configfile: "config/config.yaml"

# Seconds-long bookkeeping runs in the submitting process rather than paying a SLURM round-trip.
# Anything with a real toolchain or a real cost is submitted so it runs with declared resources.
localrules:
    all, prompts, render_prompts,


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

PROMPTS = expand(f"{OUT}/prompts/{{dataset}}.json", dataset=DATASETS)

wildcard_constraints:
    dataset="|".join(DATASETS),


# ---- targets: one phony target per stage; `all` becomes the technical report at stage 6 --------
rule all:
    input: PROMPTS

rule prompts:
    input: PROMPTS


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
#   0  smoke              the tests of CONCEPT_BANK.md's schema rules, the label maps against the
#                         installed medmnist package, both prompts, the arm-B estimator on a
#                         fixture, the metric convention, the client's retry. Every rule above
#                         gains its marker as an input when it lands.
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
