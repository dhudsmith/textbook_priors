"""report: every figure, table and number the technical report states, from results/ alone.

No number in the report is typed by hand. Each table is generated here and included by report.tex,
and the sentences whose direction depends on a value read a macro from `numbers.tex` rather than
asserting something a later run could contradict. If a figure and the prose ever disagree, it is
because someone edited the prose.

Six figures (WORKFLOW.md section 6): the learning curve with arm B's line (H1), n_B per dataset
(H1), the model ladder (H3), the reader chain and thinking's effect against the baseline (H4), and
arm PC's gain over arm P along the curve (H5).

One table, `literature`, and one line on the curve figure read a fixed input besides results/:
`data/literature/benchmarks.yaml`, published fully supervised numbers for the same six tasks
(WORKFLOW.md section 10). Both are another extension that decides nothing — a reconciliation
point, not a comparison arm — so the line is drawn distinctly from the five arms and carries no
interval.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ARM_LABEL = {"C": "arm C: concept scores", "P": "arm P: ImageNet features",
             "PC": "arm PC: ImageNet features + concept scores",
             "B": "arm B: textbook only (no labels)", "A": "arm A: zero-shot (no labels)"}
ARM_COLOUR = {"C": "#1f77b4", "P": "#d62728", "PC": "#9467bd", "B": "#2ca02c", "A": "#7f7f7f"}

# Not an arm: the published, fully supervised ceiling (data/literature/benchmarks.yaml), read onto
# the same axes as a fixed reference rather than a line that moves with n. One colour, used nowhere
# else, so it cannot be mistaken for a fifth arm.
LIT_LABEL = "published ResNet-18 (224), fully supervised (Yang et al. 2023)"
LIT_COLOUR = "#8c564b"


def ceiling(literature, dataset) -> tuple[str, dict]:
    """The published ceiling for one task: the best of the five methods, by AUC.

    Defined once because the table and the number macros both read it, and a report whose table
    said one thing and whose prose said another would be worse than either alone. The figure
    deliberately does NOT use this - it draws the ResNet-18 (224) row, the one backbone trained at
    this study's own input resolution - and the prose says which is which.
    """
    return max(literature.dataset(dataset).items(), key=lambda kv: kv[1]["auc"])


def load(outdir, datasets) -> tuple[dict, dict]:
    per = {d: json.loads(Path(f"{outdir}/evaluate/{d}.json").read_text()) for d in datasets}
    across = json.loads(Path(f"{outdir}/evaluation.json").read_text())
    return per, across


def tex_escape(text: str) -> str:
    return str(text).replace("_", r"\_").replace("&", r"\&").replace("%", r"\%")


def median(values) -> float:
    """The middle of an even-length list is the mean of the two middle values, not the upper one.

    Spelled out because the first version of the literature macros took `sorted(v)[len(v) // 2]`
    and called it a median: with six datasets that is the fourth smallest, which put 0.115 in a
    sentence whose real answer was 0.094. numpy is not imported here and one line is cheaper than
    the import.
    """
    ordered = sorted(values)
    mid = len(ordered) // 2
    return ordered[mid] if len(ordered) % 2 else (ordered[mid - 1] + ordered[mid]) / 2


def fmt(value, places=3) -> str:
    """A number as the report prints it, or a dash where there is nothing to print."""
    if value is None:
        return "--"
    return f"{float(value):.{places}f}"


# ---- figures -------------------------------------------------------------------------------------

def figure_curve(per, datasets, curve_n, dest, literature=None):
    """H1: what the labels buy, against what the textbook gives for nothing.

    One panel per dataset. Arms C, P and PC are the same classifier on different features, so the
    gap between the curves is the features; arm B is a horizontal line because it uses no labels at
    all, and where the red curve crosses it is n_B. Arm PC (H5) is drawn without a band, because
    the question it answers is a paired difference from arm P and that difference, with its
    interval, has its own figure.

    `literature`, if given, adds one more horizontal line: the published, fully supervised
    ResNet-18 (224) AUC for the same task (data/literature/benchmarks.yaml). It is drawn distinctly
    from the five arms - a different colour, a sparser dash, no fill - because it is not one: it
    was not computed by this study, does not share the paired bootstrap, and carries no interval.
    """
    # Three panels a row for the talk's six datasets, four a row for twelve; a dataset whose pool
    # stops short of the grid draws only the points it reached (`curve_n` in its evaluate file).
    cols = 3 if len(datasets) <= 6 else 4
    rows = -(-len(datasets) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(4.3 * cols, 3.7 * rows), sharex=True, squeeze=False)
    for ax in axes.flat[len(datasets):]:
        ax.set_visible(False)
    legend_ax = None
    for ax, dataset in zip(axes.flat, datasets):
        got = per[dataset]
        own_n = list(got.get("curve_n", curve_n))
        for arm in ("C", "P"):
            point = [got["curve"][f"{arm}__n{n}"]["point"] for n in own_n]
            lo = [got["curve"][f"{arm}__n{n}"]["lo"] for n in own_n]
            hi = [got["curve"][f"{arm}__n{n}"]["hi"] for n in own_n]
            ax.plot(own_n, point, "o-", color=ARM_COLOUR[arm], label=ARM_LABEL[arm], markersize=4)
            ax.fill_between(own_n, lo, hi, color=ARM_COLOUR[arm], alpha=0.15, linewidth=0)
        if all(f"PC__n{n}" in got["curve"] for n in own_n):
            ax.plot(own_n, [got["curve"][f"PC__n{n}"]["point"] for n in own_n], "s--",
                    color=ARM_COLOUR["PC"], label=ARM_LABEL["PC"], markersize=3.5, linewidth=1.2)
        if got.get("n_b") is not None:
            b_key = next(k for k in got["auc"] if k.startswith("B__"))
            ax.axhline(got["auc"][b_key], color=ARM_COLOUR["B"], linestyle="--", label=ARM_LABEL["B"])
            ax.axhline(got["auc"]["A"], color=ARM_COLOUR["A"], linestyle=":", label=ARM_LABEL["A"])
            ax.set_title(f"{dataset}  (n$_B$ = {got['n_b']['point']})", fontsize=10)
            legend_ax = legend_ax or ax
        else:
            # The multi-label task: arms C and P only, so no horizontal lines and no crossing.
            ax.set_title(f"{dataset}  (multi-label: arms C and P only)", fontsize=10)
        if literature is not None:
            ax.axhline(literature.dataset(dataset)["resnet18_224"]["auc"], color=LIT_COLOUR,
                      linestyle=(0, (1, 1)), linewidth=1.5, label=LIT_LABEL)
        ax.set_xscale("log")
        ax.set_xticks(curve_n, [str(n) for n in curve_n])
        ax.grid(alpha=0.25)
    for ax in axes[:, 0]:
        ax.set_ylabel("test AUC")
    for ax in axes[-1]:
        ax.set_xlabel("labelled images")
    (legend_ax or axes.flat[0]).legend(fontsize=8, loc="lower right")
    fig.suptitle("What labelled images buy, and what the textbook gives for nothing", fontsize=12)
    fig.tight_layout()
    fig.savefig(Path(dest) / "fig_curve.png", dpi=200)
    plt.close(fig)


def figure_n_b(per, datasets, curve_n, dest):
    """H1's headline, per dataset: how many labelled images the pixel probe needed to catch up.

    A coded value is drawn at the edge of the grid and annotated, never silently turned into a
    number: `<=50` means the probe was already ahead at the first grid point and `>2000` that it
    never caught up inside the curve.
    """
    datasets = [d for d in datasets if per[d].get("n_b") is not None]      # no arm B, no n_B
    fig, ax = plt.subplots(figsize=(8, 3.4 + 0.15 * len(datasets)))
    for i, dataset in enumerate(datasets):
        n_b = per[dataset]["n_b"]
        code = n_b["point"]
        value = float(code) if code.isdigit() else (curve_n[0] if code.startswith("<=") else curve_n[-1])
        ax.plot([value], [i], "o", color=ARM_COLOUR["C"], markersize=9,
                markerfacecolor="white" if not code.isdigit() else ARM_COLOUR["C"])
        lo, hi = n_b["lo"], n_b["hi"]
        lo_v = float(lo) if lo.isdigit() else (curve_n[0] if lo.startswith("<=") else curve_n[-1])
        hi_v = float(hi) if hi.isdigit() else (curve_n[0] if hi.startswith("<=") else curve_n[-1])
        ax.plot([lo_v, hi_v], [i, i], color=ARM_COLOUR["C"], alpha=0.45, linewidth=2)
        ax.annotate(code, (value, i), textcoords="offset points", xytext=(0, 9),
                    ha="center", fontsize=9)
    ax.set_yticks(range(len(datasets)), datasets)
    ax.set_xscale("log")
    ax.set_xticks(curve_n, [str(n) for n in curve_n])
    ax.set_xlabel("labelled images the pixel probe needed to reach the textbook arm (n$_B$)")
    ax.grid(alpha=0.25, axis="x")
    ax.set_title("An open circle is a coded value: the crossing is outside the grid", fontsize=9)
    fig.tight_layout()
    fig.savefig(Path(dest) / "fig_n_b.png", dpi=200)
    plt.close(fig)


def figure_ladder(across, datasets, dest):
    """H3: arm B's AUC against model size, within family, one line per dataset.

    Read within family only: size and training data are confounded across families, and both size
    steps also change quantisation (WORKFLOW.md section 2).
    """
    order = across["h3"]["model_order"]
    datasets = [d for d in datasets if d in across["h3"]["arm_b_auc"]]
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for dataset in datasets:
        values = [across["h3"]["arm_b_auc"][dataset][m] for m in order]
        ax.plot(range(len(order)), values, "o-", label=dataset, markersize=5, alpha=0.85)
    ax.set_xticks(range(len(order)), [m.replace("-", "\n") for m in order], fontsize=8)
    ax.set_ylabel("arm B test AUC (no labels)")
    ax.axhline(0.5, color="grey", linestyle=":", linewidth=1)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=7, ncol=3 if len(datasets) > 6 else 2)
    ax.set_title("The textbook arm across the model ladder, smallest to largest", fontsize=11)
    fig.tight_layout()
    fig.savefig(Path(dest) / "fig_ladder.png", dpi=200)
    plt.close(fig)


def figure_readers(across, datasets, dest):
    """H4: how much class information each reader's concept answers carry.

    One line per dataset across the reader chain, drawn in the order the chain fixes: the baseline
    at effort `none`, the same model asked to think, then a frontier model asked to think as hard.
    Each step changes one thing, so a line that rises at the first step and falls at the second is
    saying something specific and readable off the figure.

    The y axis is the cross-validated probe, not arm B and not arm C: it is what a classifier can
    recover from the concept answers on the images the readers share, and it exists because arm C
    would have needed a labelled pool for every reader (WORKFLOW.md sections 2 and 3).
    """
    order = across["h4"]["readers"]
    chain = [across["h4"]["h4a"]["from"], across["h4"]["h4a"]["to"], across["h4"]["h4b"]["to"]]
    rest = [r for r in order if r not in chain]
    columns = chain + rest
    datasets = [d for d in datasets if d in across["h4"]["probe_auc"]]
    fig, ax = plt.subplots(figsize=(9.0, 4.8))
    for dataset in datasets:
        values = [across["h4"]["probe_auc"][dataset][r] for r in columns]
        ax.plot(range(len(columns)), values, "o-", label=dataset, markersize=5, alpha=0.85)
    # The chain is what the hypothesis reads; the other readers are context and are separated by a
    # rule rather than by being left out, because a reader hidden from the figure is a reader the
    # reader of the figure cannot check.
    ax.axvline(len(chain) - 0.5, color="grey", linestyle="--", linewidth=1)
    ax.text(len(chain) - 0.45, ax.get_ylim()[0], " not in the chain", fontsize=7,
            color="grey", va="bottom")
    ax.set_xticks(range(len(columns)), [r.replace("-", "\n") for r in columns], fontsize=7)
    ax.set_ylabel(f"cross-validated probe AUC\n(concept answers, {across['h4']['subsample']} images)")
    ax.grid(alpha=0.25)
    # Under the axes, not inside them: inside, the legend sat on dermamnist's baseline point.
    ax.legend(fontsize=7, ncol=4 if len(datasets) > 6 else 3, loc="upper center",
              bbox_to_anchor=(0.5, -0.28), frameon=False)
    ax.set_title("H4: what each reader's concept answers carry", fontsize=11)
    fig.tight_layout()
    fig.savefig(Path(dest) / "fig_readers.png", dpi=200, bbox_inches="tight")
    plt.close(fig)


def figure_thinking(across, datasets, dest):
    """H4a read against the baseline: where did asking the model to think help?

    One point per dataset. x is how well the model read the concepts with no reasoning; y is what
    reasoning added, with its paired interval. The hypothesis asked for six points above zero and
    got three, but the picture is not a null: the points fall from left to right, gains where the
    immediate reading was poor and a loss where it was already good. Six points is a pattern to
    state and not a slope to test, so no line is fitted through them.
    """
    h4 = across["h4"]
    base = h4["h4a"]["from"]
    datasets = [d for d in datasets if d in h4["probe_auc"]]
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for dataset in datasets:
        x = h4["probe_auc"][dataset][base]
        d = h4["h4a"]["differences"][dataset]
        clear = d["lo"] > 0 or d["hi"] < 0
        ax.errorbar(x, d["median"], yerr=[[d["median"] - d["lo"]], [d["hi"] - d["median"]]],
                    fmt="o", color=ARM_COLOUR["C"], alpha=1.0 if clear else 0.45, capsize=3,
                    markersize=6, linewidth=1.2)
        ax.annotate(dataset, (x, d["median"]), textcoords="offset points", xytext=(6, 4),
                    fontsize=8, alpha=1.0 if clear else 0.7)
    ax.axhline(0, color="grey", linestyle=":", linewidth=1)
    ax.set_xlabel(f"probe AUC with no reasoning ({base})")
    ax.set_ylabel("what reasoning at medium added\n(probe AUC, paired 95% interval)")
    ax.set_title("H4a: reasoning helped where the model was reading badly", fontsize=11)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(Path(dest) / "fig_thinking.png", dpi=200)
    plt.close(fig)


def figure_complement(per, across, datasets, curve_n, dest):
    """H5: what the concept columns add to the pixel columns, along the curve.

    One panel per dataset; y is the paired difference AUC(PC) - AUC(P) with its 95% interval from
    the shared bootstrap, x is the labelled subset. The hypothesis is decided at one grid point,
    marked by the vertical rule, and the rest of the curve is there so a reader can see where the
    textbook's contribution runs out rather than take a single n on trust. A filled marker is an
    interval clear of zero.
    """
    at_n = across["h5"]["at_n"]
    cols = 3 if len(datasets) <= 6 else 4
    rows = -(-len(datasets) // cols)
    fig, axes = plt.subplots(rows, cols, figsize=(4.3 * cols, 3.2 * rows), sharex=True, squeeze=False)
    for ax in axes.flat[len(datasets):]:
        ax.set_visible(False)
    for ax, dataset in zip(axes.flat, datasets):
        got = per[dataset]
        own_n = list(got.get("curve_n", curve_n))
        diffs = [got["differences"][f"PC_minus_P__n{n}"] for n in own_n]
        mid = [d["median"] for d in diffs]
        ax.fill_between(own_n, [d["lo"] for d in diffs], [d["hi"] for d in diffs],
                        color=ARM_COLOUR["PC"], alpha=0.18, linewidth=0)
        ax.plot(own_n, mid, "-", color=ARM_COLOUR["PC"], linewidth=1.2)
        for n, d in zip(own_n, diffs):
            clear = d["lo"] > 0 or d["hi"] < 0
            ax.plot([n], [d["median"]], "o", color=ARM_COLOUR["PC"], markersize=5,
                    markerfacecolor=ARM_COLOUR["PC"] if clear else "white")
        ax.axhline(0, color="grey", linestyle=":", linewidth=1)
        ax.axvline(at_n, color="grey", linestyle="--", linewidth=0.8, alpha=0.7)
        ax.set_xscale("log")
        ax.set_xticks(curve_n, [str(n) for n in curve_n])
        win = across["h5"]["pc_beats_p"][dataset]
        ax.set_title(f"{dataset}  ({'PC > P' if win else 'PC <= P'} at n = {at_n})", fontsize=10)
        ax.grid(alpha=0.25)
    for ax in axes[:, 0]:
        ax.set_ylabel("AUC(PC) $-$ AUC(P)")
    for ax in axes[-1]:
        ax.set_xlabel("labelled images")
    fig.suptitle("H5: what the concept scores add to the pixel features, at every labelled subset "
                 f"(decided at the dashed rule, n = {at_n}; filled = interval clear of zero)", fontsize=11)
    fig.tight_layout()
    fig.savefig(Path(dest) / "fig_complement.png", dpi=200)
    plt.close(fig)


# ---- tables ---------------------------------------------------------------------------------------

def _table(dest, name, header, rows, caption, label):
    body = "\n".join(" & ".join(r) + r" \\" for r in rows)
    tex = (r"\begin{table}[htbp]\centering\small" "\n"
           r"\begin{tabular}{" + "l" * 1 + "r" * (len(header) - 1) + "}\n"
           r"\hline" "\n" + " & ".join(header) + r" \\" "\n" r"\hline" "\n"
           + body + "\n" r"\hline" "\n" r"\end{tabular}" "\n"
           rf"\caption{{{caption}}}\label{{tab:{label}}}" "\n" r"\end{table}" "\n")
    (Path(dest) / f"{name}.tex").write_text(tex)


def table_h1(per, datasets, curve_n, dest):
    rows = []
    for d in datasets:
        got = per[d]
        smallest = curve_n[0]
        diff = got["differences"][f"C_minus_P__n{smallest}"]
        n_b = got.get("n_b")
        rows.append([tex_escape(d), n_b["point"] if n_b else "--",
                     f"[{n_b['lo']}, {n_b['hi']}]" if n_b else "--",
                     fmt(got["curve"][f"C__n{smallest}"]["point"]),
                     fmt(got["curve"][f"P__n{smallest}"]["point"]),
                     f"{fmt(diff['median'])} [{fmt(diff['lo'])}, {fmt(diff['hi'])}]"])
    _table(dest, "h1", ["dataset", r"n$_B$", "95\\% interval", f"AUC(C, n={curve_n[0]})",
                        f"AUC(P, n={curve_n[0]})", "difference C--P"], rows,
           "H1. The labelled images the pixel probe needed to reach the textbook arm, and the "
           "concept probe against the pixel probe at the smallest labelled subset. The multi-label "
           "task has no arm B and so no n$_B$.", "h1")


def table_h2(per, datasets, curve_n, primary, dest):
    rows = []
    for d in datasets:
        got = per[d]
        if "B_minus_A" not in got["differences"]:       # the multi-label task has no arms A and B
            continue
        diff = got["differences"]["B_minus_A"]
        b_drop = got["controls"][f"B__{primary}"]["drop"]
        c_drop = got["controls"][f"C__n{max(got.get('curve_n', curve_n))}"]["drop"]
        rows.append([tex_escape(d), fmt(got["auc"][f"B__{primary}"]), fmt(got["auc"]["A"]),
                     f"{fmt(diff['median'])} [{fmt(diff['lo'])}, {fmt(diff['hi'])}]",
                     f"{fmt(b_drop['median'])} [{fmt(b_drop['lo'])}, {fmt(b_drop['hi'])}]",
                     f"{fmt(c_drop['median'])} [{fmt(c_drop['lo'])}, {fmt(c_drop['hi'])}]"])
    _table(dest, "h2", ["dataset", "AUC(B)", "AUC(A)", "B $-$ A", "B drop, permuted", "C drop, permuted"],
           rows,
           "H2. The textbook arm against the zero-shot baseline, and what each arm loses when the "
           "structure it claims to read is destroyed: arm B's fingerprints permuted across classes, "
           "arm C's concept columns permuted across images.", "h2")


def table_h3(across, datasets, dest):
    order = across["h3"]["model_order"]
    rows = [[tex_escape(d)] + [fmt(across["h3"]["arm_b_auc"][d][m]) for m in order]
            for d in datasets if d in across["h3"]["arm_b_auc"]]
    _table(dest, "h3", ["dataset"] + [tex_escape(m) for m in order], rows,
           "H3. Arm B's AUC for every model, smallest to largest. Read within family: size and "
           "training data are confounded across families, and both size steps also change "
           "quantisation.", "h3")


def table_h4(across, datasets, dest):
    """H4: the two steps of the reader chain, each changing one thing.

    The columns are AUCs of the cross-validated probe on the shared prefix, so they are not
    comparable with the learning curve's arm C: no labels were spent to produce them. The last two
    columns are the paired differences the hypothesis is decided on.
    """
    h4 = across["h4"]
    base, think, front = h4["h4a"]["from"], h4["h4a"]["to"], h4["h4b"]["to"]
    rows = []
    covered = [d for d in datasets if d in h4["probe_auc"]]
    for d in covered:
        got = h4["probe_auc"][d]
        a, b = h4["h4a"]["differences"][d], h4["h4b"]["differences"][d]
        rows.append([tex_escape(d), fmt(got[base]), fmt(got[think]), fmt(got[front]),
                     f"{fmt(a['median'])} [{fmt(a['lo'])}, {fmt(a['hi'])}]",
                     f"{fmt(b['median'])} [{fmt(b['lo'])}, {fmt(b['hi'])}]"])
    _table(dest, "h4",
           ["dataset", tex_escape(base), tex_escape(think), tex_escape(front),
            "H4a: think $-$ base", "H4b: frontier $-$ think"],
           rows,
           f"H4. The cross-validated probe on each reader's concept answers, on the "
           f"{h4['subsample']} images every reader was scored on. H4a holds the model and adds "
           f"reasoning; H4b holds the reasoning effort and changes the model. Won on "
           f"{h4['h4a']['wins']} of {len(covered)} and {h4['h4b']['wins']} of {len(covered)} "
           "respectively. These AUCs are not points on the learning curve: the probe is fitted "
           "inside the same images it scores, so it measures what the answers carry rather than "
           "what a labelled model would achieve.", "h4")


def table_h5(per, across, datasets, dest):
    """H5: arm PC against arm P at the deciding grid point, with the control and the curve's end.

    Every column is a seed mean or a paired difference of seed means on the shared test sample.
    The control column is PC minus PC with its concept block shuffled across images: what the
    textbook's columns add over the same number of columns of noise beside the same pixels. The
    last column is the same difference at the largest subset the dataset's pool reached, so the
    table shows both where the hypothesis is decided and where the contribution ends up.
    """
    h5 = across["h5"]
    at_n = h5["at_n"]
    rows = []
    for d in datasets:
        got = per[d]
        largest = max(got["curve_n"])
        diff = got["differences"][f"PC_minus_P__n{at_n}"]
        drop = got["controls"][f"PC__n{at_n}"]["drop"]
        end = got["differences"][f"PC_minus_P__n{largest}"]
        rows.append([tex_escape(d),
                     fmt(got["curve"][f"P__n{at_n}"]["point"]),
                     fmt(got["curve"][f"PC__n{at_n}"]["point"]),
                     f"{fmt(diff['median'])} [{fmt(diff['lo'])}, {fmt(diff['hi'])}]",
                     f"{fmt(drop['median'])} [{fmt(drop['lo'])}, {fmt(drop['hi'])}]",
                     f"{fmt(end['median'])} [{fmt(end['lo'])}, {fmt(end['hi'])}] ({largest})"])
    _table(dest, "h5",
           ["dataset", f"AUC(P, n={at_n})", f"AUC(PC, n={at_n})", f"PC $-$ P, n={at_n}",
            "PC drop, permuted", "PC $-$ P, largest n"],
           rows,
           f"H5. The pixel probe with and without the concept scores beside its features, at the "
           f"smallest labelled subset (n = {at_n}), where the hypothesis is decided: PC won on "
           f"{h5['wins']} of {h5['n_datasets']} datasets against {h5['min_wins']} needed. "
           "``PC drop, permuted'' is what PC loses when its concept columns are shuffled across "
           "images with the pixel columns left alone, so a drop near zero means the columns were "
           "adding noise rather than the textbook. The last column is the same difference at the "
           "largest subset the dataset's pool reached (in parentheses).", "h5")


LIT_METHOD_LABEL = {"resnet18_224": "ResNet-18 (224)", "resnet50_224": "ResNet-50 (224)",
                    "auto_sklearn": "auto-sklearn", "autokeras": "AutoKeras",
                    "google_automl": "Google AutoML Vision"}


def table_literature(per, literature, datasets, curve_n, primary, dest):
    """This study's arms against the published literature (extension, decides no hypothesis).

    Every value in `literature` is fully supervised, trained on a dataset's whole official training
    split (thousands to tens of thousands of images), against this study's zero-label arm B and its
    largest labelled subset (n = max(curve_n), at most 2,000 images) — a ceiling for the task, not a
    same-conditions baseline. `data/literature/README.md` says so and the caption repeats it.
    """
    largest = max(curve_n)
    rows = []
    for d in datasets:
        got = per[d]
        best_method, best = ceiling(literature, d)
        # The largest labelled subset this dataset's pool reached: the grid's top, or less where
        # the official train split is smaller (breastmnist 500, retinamnist 1000).
        own_largest = max(got.get("curve_n", curve_n))
        # Every arm, not only arm B: the ceiling is a reference point for the study, and the study
        # has five arms. The two zero-label arms come first because they are the ones the ceiling
        # is most interesting against - what the model brings before any label is bought.
        rows.append([
            tex_escape(d),
            fmt(got["auc"].get("A")),
            fmt(got["auc"].get(f"B__{primary}")),
            fmt(got["curve"][f"C__n{own_largest}"]["point"]) + ("" if own_largest == largest else f" ({own_largest})"),
            fmt(got["curve"][f"P__n{own_largest}"]["point"]) + ("" if own_largest == largest else f" ({own_largest})"),
            fmt(best["auc"]),
            tex_escape(LIT_METHOD_LABEL[best_method]),
        ])
    _table(dest, "literature",
           ["dataset", "A", "B", f"C (n={largest})", f"P (n={largest})",
            "published", "published method"],
           rows,
           "Literature reconciliation (extension, decides no hypothesis). Every arm of this study "
           "against the best of five fully supervised methods reported for the same task on the "
           r"same 224-pixel release \cite{yang2023}. The published methods are trained on the whole "
           "official training split, thousands to tens of thousands of images, not this study's "
           "n$\\le$2000 pool; A and B see no labels at all, and are undefined for the multi-label "
           "task. Where a pool is smaller than the grid the subset actually reached is in "
           "parentheses. Read the last column as a ceiling for "
           "the task, not as a same-conditions comparison. ACC is pinned beside AUC in "
           r"\texttt{data/literature/benchmarks.yaml} and not shown, because this study computes no "
           "ACC to set beside it.", "literature")


def table_completeness(per, datasets, dest):
    models = sorted(set().union(*(per[d]["complete_frac"] for d in datasets)))
    rows = [[tex_escape(d)] + [f"{100 * per[d]['complete_frac'][m]:.1f}" if m in per[d]["complete_frac"]
                               else "--" for m in models]
            for d in datasets]
    _table(dest, "completeness", ["dataset"] + [tex_escape(m) for m in models], rows,
           "Percentage of test images for which every concept came back with a level on that "
           "concept's own scale. An image with any missing answer counts as incomplete; a cell "
           "more than 5\\% incomplete is excluded from the headline. Only the primary model "
           "scores the multi-label task.", "completeness")


def numbers(per, across, datasets, curve_n, primary, dest, literature=None):
    """The macros the prose reads, so no sentence states a number the run did not produce."""
    h1, h2, h3 = across["h1"], across["h2"], across["h3"]
    arm_b = across.get("arm_b_datasets", datasets)
    lines = {
        "numDatasets": len(datasets),
        "numArmBDatasets": len(arm_b),
        "minWinsAll": h1.get("min_wins", len(datasets)),
        "minWinsArmB": h2.get("min_wins", len(arm_b)),
        "alphaLevel": across.get("alpha", 0.05),
        "numModels": len(h3["model_order"]),
        "hOneSupported": "supported" if h1["supported"] else "not supported",
        "hTwoSupported": "supported" if h2["supported"] else "not supported",
        "hThreeSupported": "supported" if h3["supported"] else "not supported",
        "cBeatsPWins": h1["c_beats_p_wins"],
        "cBeatsPp": fmt(h1["c_beats_p_sign_test_p"], 4),
        "bBeatsAWins": h2["b_beats_a_wins"],
        "bBeatsAp": fmt(h2["b_beats_a_sign_test_p"], 4),
        "medianNB": str(h1["median_n_b"]).replace("<=", r"$\leq$").replace(">", "$>$"),
        "neverReached": h1["datasets_where_the_probe_never_reaches_arm_b"],
        "startedAbove": h1["datasets_where_the_probe_starts_above_arm_b"],
        "friedmanP": fmt(h3["friedman"]["p"], 4),
    }
    h4 = across.get("h4")
    if h4:
        lines["hFourSupported"] = "supported" if h4["supported"] else "not supported"
        lines["hFourASupported"] = "supported" if h4["h4a"]["supported"] else "not supported"
        lines["hFourBSupported"] = "supported" if h4["h4b"]["supported"] else "not supported"
        lines["hFourAWins"] = h4["h4a"]["wins"]
        lines["hFourBWins"] = h4["h4b"]["wins"]
        lines["hFourAp"] = fmt(h4["h4a"]["sign_test_p"], 4)
        lines["hFourBp"] = fmt(h4["h4b"]["sign_test_p"], 4)
        lines["hFourSubsample"] = h4["subsample"]
        lines["hFourBaseline"] = tex_escape(h4["h4a"]["from"])
        lines["hFourThinking"] = tex_escape(h4["h4a"]["to"])
        lines["hFourFrontier"] = tex_escape(h4["h4b"]["to"])
        lines["numReaders"] = len(h4["readers"])
    h5 = across.get("h5")
    if h5:
        lines["hFiveSupported"] = "supported" if h5["supported"] else "not supported"
        lines["hFiveAtN"] = h5["at_n"]
        lines["pcBeatsPWins"] = h5["wins"]
        lines["pcBeatsPp"] = fmt(h5["sign_test_p"], 4)
        lines["pcControlWins"] = h5["control_wins"]
        # The largest grid point: where the textbook's contribution ends up once labels are
        # plentiful, over the datasets whose pool reaches it.
        top = str(max(int(n) for n in h5["wins_by_n"]))
        lines["pcLargestN"] = top
        lines["pcBeatsPWinsLargest"] = h5["wins_by_n"][top]["wins"]
        lines["pcLargestNDatasets"] = h5["wins_by_n"][top]["n_datasets"]
        # Interval-clear wins at the deciding n: a win whose interval excludes zero.
        lines["pcClearWins"] = sum(1 for d in h5["differences"].values() if d["lo"] > 0)
        lines["pcClearLosses"] = sum(1 for d in h5["differences"].values() if d["hi"] < 0)
    for family, spec in h3["ladder"].items():
        lines[f"ladder{family.capitalize()}Wins"] = spec["wins"]
        lines[f"ladder{family.capitalize()}P"] = fmt(spec["sign_test_p"], 4)
    if literature is not None:
        # The gap to the published ceiling, per label budget. Stated as a median over datasets
        # because an AUC on pathmnist and one on octmnist are not commensurable to average -
        # the same reason the hypotheses use sign tests rather than pooled AUCs.
        largest = max(curve_n)
        gaps = {"Zero": [], "Concept": [], "Pixel": []}
        for d in datasets:
            top = ceiling(literature, d)[1]["auc"]
            own_largest = max(per[d].get("curve_n", curve_n))
            if "A" in per[d]["auc"]:                    # the multi-label task has no zero-label arm
                zero = [per[d]["auc"]["A"], per[d]["auc"][f"B__{primary}"]]
                gaps["Zero"].append(top - max(zero))
            gaps["Concept"].append(top - per[d]["curve"][f"C__n{own_largest}"]["point"])
            gaps["Pixel"].append(top - per[d]["curve"][f"P__n{own_largest}"]["point"])
        for name, values in gaps.items():
            lines[f"litGap{name}Median"] = fmt(median(values))
        lines["litLargestN"] = largest
        # Counted on the printed value, not the float: pneumoniamnist's pixel gap is
        # 0.020000000000000018, and a prose sentence that said "within two points on 5 of 6" while
        # the table beside it printed 0.971 against 0.991 would be reporting a rounding artefact.
        lines["litPixelWithinTwoPoints"] = sum(1 for g in gaps["Pixel"] if round(g, 3) <= 0.02)
        lines["litZeroWithinFivePoints"] = sum(1 for g in gaps["Zero"] if round(g, 3) <= 0.05)
        lines["litPixelAtOrAboveCeiling"] = sum(1 for g in gaps["Pixel"] if round(g, 3) <= 0.0)

    for d in datasets:
        key = "".join(part.capitalize() for part in d.replace("mnist", "").split("_")) or d
        if literature is not None:
            lines[f"aucLit{key}"] = fmt(ceiling(literature, d)[1]["auc"])
        n_b = per[d].get("n_b")
        lines[f"nB{key}"] = n_b["point"].replace("<=", r"$\leq$").replace(">", "$>$") if n_b else "--"
        lines[f"aucB{key}"] = fmt(per[d]["auc"].get(f"B__{primary}"))
        lines[f"aucA{key}"] = fmt(per[d]["auc"].get("A"))
    text = "\n".join(rf"\newcommand{{\{k}}}{{{v}}}" for k, v in lines.items()) + "\n"
    (Path(dest) / "numbers.tex").write_text(text)
    return lines
