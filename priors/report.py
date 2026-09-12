"""report: every figure, table and number the technical report states, from results/ alone.

No number in the report is typed by hand. Each table is generated here and included by report.tex,
and the sentences whose direction depends on a value read a macro from `numbers.tex` rather than
asserting something a later run could contradict. If a figure and the prose ever disagree, it is
because someone edited the prose.

Three figures, one per hypothesis (WORKFLOW.md section 6): the learning curve with arm B's line,
n_B per dataset, and the model ladder. Arm D rides along on the curve figure and gets one table of
its own, always labelled post-hoc: it was designed after the first results and decides nothing.

One table, `literature`, and one line on the curve figure read a fixed input besides results/:
`data/literature/benchmarks.yaml`, published fully supervised numbers for the same six tasks
(WORKFLOW.md section 10). Both are another extension that decides nothing — a reconciliation
point, not a comparison arm — so the line is drawn distinctly from the four arms and carries no
interval.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ARM_LABEL = {"C": "arm C: concept scores", "P": "arm P: ImageNet features",
             "B": "arm B: textbook only (no labels)", "A": "arm A: zero-shot (no labels)",
             "D": "arm D: bank in the prompt (post-hoc, no labels)"}
ARM_COLOUR = {"C": "#1f77b4", "P": "#d62728", "B": "#2ca02c", "A": "#7f7f7f", "D": "#9467bd"}

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


def fmt(value, places=3) -> str:
    """A number as the report prints it, or a dash where there is nothing to print."""
    if value is None:
        return "--"
    return f"{float(value):.{places}f}"


# ---- figures -------------------------------------------------------------------------------------

def figure_curve(per, datasets, curve_n, dest, literature=None):
    """H1: what the labels buy, against what the textbook gives for nothing.

    One panel per dataset. Arms C and P are the same classifier on different features, so the gap
    between the curves is the features; arm B is a horizontal line because it uses no labels at all,
    and where the red curve crosses it is n_B.

    `literature`, if given, adds one more horizontal line: the published, fully supervised
    ResNet-18 (224) AUC for the same task (data/literature/benchmarks.yaml). It is drawn distinctly
    from the four arms - a different colour, a sparser dash, no fill - because it is not one: it
    was not computed by this study, does not share the paired bootstrap, and carries no interval.
    """
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5), sharex=True)
    for ax, dataset in zip(axes.flat, datasets):
        got = per[dataset]
        for arm in ("C", "P"):
            point = [got["curve"][f"{arm}__n{n}"]["point"] for n in curve_n]
            lo = [got["curve"][f"{arm}__n{n}"]["lo"] for n in curve_n]
            hi = [got["curve"][f"{arm}__n{n}"]["hi"] for n in curve_n]
            ax.plot(curve_n, point, "o-", color=ARM_COLOUR[arm], label=ARM_LABEL[arm], markersize=4)
            ax.fill_between(curve_n, lo, hi, color=ARM_COLOUR[arm], alpha=0.15, linewidth=0)
        b_key = next(k for k in got["auc"] if k.startswith("B__"))
        ax.axhline(got["auc"][b_key], color=ARM_COLOUR["B"], linestyle="--", label=ARM_LABEL["B"])
        ax.axhline(got["auc"]["A"], color=ARM_COLOUR["A"], linestyle=":", label=ARM_LABEL["A"])
        # Arm D is a third horizontal line for the same reason as A and B: it uses no labels, so it
        # does not move with n. It is drawn here because the question the figure already asks - how
        # many labels is the textbook worth - is the one arm D gives a second answer to.
        if "D" in got["auc"]:
            ax.axhline(got["auc"]["D"], color=ARM_COLOUR["D"], linestyle="-.", label=ARM_LABEL["D"])
        if literature is not None:
            ax.axhline(literature.dataset(dataset)["resnet18_224"]["auc"], color=LIT_COLOUR,
                      linestyle=(0, (1, 1)), linewidth=1.5, label=LIT_LABEL)
        ax.set_xscale("log")
        ax.set_xticks(curve_n, [str(n) for n in curve_n])
        ax.set_title(f"{dataset}  (n$_B$ = {got['n_b']['point']})", fontsize=10)
        ax.grid(alpha=0.25)
    for ax in axes[:, 0]:
        ax.set_ylabel("test AUC")
    for ax in axes[-1]:
        ax.set_xlabel("labelled images")
    axes.flat[0].legend(fontsize=8, loc="lower right")
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
    fig, ax = plt.subplots(figsize=(8, 4.2))
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
    fig, ax = plt.subplots(figsize=(8.5, 4.6))
    for dataset in datasets:
        values = [across["h3"]["arm_b_auc"][dataset][m] for m in order]
        ax.plot(range(len(order)), values, "o-", label=dataset, markersize=5, alpha=0.85)
    ax.set_xticks(range(len(order)), [m.replace("-", "\n") for m in order], fontsize=8)
    ax.set_ylabel("arm B test AUC (no labels)")
    ax.axhline(0.5, color="grey", linestyle=":", linewidth=1)
    ax.grid(alpha=0.25)
    ax.legend(fontsize=8, ncol=2)
    ax.set_title("The textbook arm across the model ladder, smallest to largest", fontsize=11)
    fig.tight_layout()
    fig.savefig(Path(dest) / "fig_ladder.png", dpi=200)
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
        rows.append([tex_escape(d), got["n_b"]["point"], f"[{got['n_b']['lo']}, {got['n_b']['hi']}]",
                     fmt(got["curve"][f"C__n{smallest}"]["point"]),
                     fmt(got["curve"][f"P__n{smallest}"]["point"]),
                     f"{fmt(diff['median'])} [{fmt(diff['lo'])}, {fmt(diff['hi'])}]"])
    _table(dest, "h1", ["dataset", r"n$_B$", "95\\% interval", f"AUC(C, n={curve_n[0]})",
                        f"AUC(P, n={curve_n[0]})", "difference C--P"], rows,
           "H1. The labelled images the pixel probe needed to reach the textbook arm, and the "
           "concept probe against the pixel probe at the smallest labelled subset.", "h1")


def table_h2(per, datasets, curve_n, primary, dest):
    rows = []
    for d in datasets:
        got = per[d]
        diff = got["differences"]["B_minus_A"]
        b_drop = got["controls"][f"B__{primary}"]["drop"]
        c_drop = got["controls"][f"C__n{max(curve_n)}"]["drop"]
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
    rows = [[tex_escape(d)] + [fmt(across["h3"]["arm_b_auc"][d][m]) for m in order] for d in datasets]
    _table(dest, "h3", ["dataset"] + [tex_escape(m) for m in order], rows,
           "H3. Arm B's AUC for every model, smallest to largest. Read within family: size and "
           "training data are confounded across families, and both size steps also change "
           "quantisation.", "h3")


def table_arm_d(per, across, datasets, primary, dest):
    """The post-hoc arm, against the two arms it was built to sit between.

    Arm A is the same question with no bank; arm B is the same bank with the arithmetic done
    outside the model. D $-$ B is the number that says whether H2's failure was the readout rather
    than the bank, and the caption says post-hoc because it is.
    """
    rows = []
    for d in datasets:
        got = per[d]
        d_a, d_b = got["differences"]["D_minus_A"], got["differences"]["D_minus_B"]
        rows.append([tex_escape(d), fmt(got["auc"]["D"]), fmt(got["auc"]["A"]),
                     fmt(got["auc"][f"B__{primary}"]),
                     f"{fmt(d_a['median'])} [{fmt(d_a['lo'])}, {fmt(d_a['hi'])}]",
                     f"{fmt(d_b['median'])} [{fmt(d_b['lo'])}, {fmt(d_b['hi'])}]"])
    arm_d = across["extensions"]["arm_d"]
    _table(dest, "arm_d", ["dataset", "AUC(D)", "AUC(A)", "AUC(B)", "D $-$ A", "D $-$ B"], rows,
           "Arm D (post-hoc). The zero-shot question asked with the whole concept bank in the "
           "prompt, against the same question without it (A) and against the same bank read by the "
           "nearest-fingerprint rule outside the model (B). Arm D was designed after the first "
           f"results and tests nothing: D beats A on {arm_d['d_beats_a_wins']} of {len(datasets)} "
           f"datasets and B on {arm_d['d_beats_b_wins']} of {len(datasets)}.", "armd")


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
        # Every arm, not only arm B: the ceiling is a reference point for the study, and the study
        # has five arms. The three zero-label arms come first because they are the ones the ceiling
        # is most interesting against - what the model brings before any label is bought.
        rows.append([
            tex_escape(d),
            fmt(got["auc"]["A"]),
            fmt(got["auc"][f"B__{primary}"]),
            fmt(got["auc"]["D"]) if "D" in got["auc"] else "--",
            fmt(got["curve"][f"C__n{largest}"]["point"]),
            fmt(got["curve"][f"P__n{largest}"]["point"]),
            fmt(best["auc"]),
            tex_escape(LIT_METHOD_LABEL[best_method]),
        ])
    _table(dest, "literature",
           ["dataset", "A", "B", "D", f"C (n={largest})", f"P (n={largest})",
            "published", "published method"],
           rows,
           "Literature reconciliation (extension, decides no hypothesis). Every arm of this study "
           "against the best of five fully supervised methods reported for the same task on the "
           r"same 224-pixel release \cite{yang2023}. The published methods are trained on the whole "
           "official training split, thousands to tens of thousands of images, not this study's "
           "n$\\le$2000 pool; A, B and D see no labels at all. Read the last column as a ceiling for "
           "the task, not as a same-conditions comparison. ACC is pinned beside AUC in "
           r"\texttt{data/literature/benchmarks.yaml} and not shown, because this study computes no "
           "ACC to set beside it.", "literature")


def table_completeness(per, datasets, dest):
    models = sorted(next(iter(per.values()))["complete_frac"])
    rows = [[tex_escape(d)] + [f"{100 * per[d]['complete_frac'][m]:.1f}" for m in models]
            for d in datasets]
    _table(dest, "completeness", ["dataset"] + [tex_escape(m) for m in models], rows,
           "Percentage of test images for which every concept came back with a level on that "
           "concept's own scale. An image with any missing answer counts as incomplete; a cell "
           "more than 5\\% incomplete is excluded from the headline.", "completeness")


def numbers(per, across, datasets, curve_n, primary, dest, literature=None):
    """The macros the prose reads, so no sentence states a number the run did not produce."""
    h1, h2, h3 = across["h1"], across["h2"], across["h3"]
    lines = {
        "numDatasets": len(datasets),
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
    for family, spec in h3["ladder"].items():
        lines[f"ladder{family.capitalize()}Wins"] = spec["wins"]
        lines[f"ladder{family.capitalize()}P"] = fmt(spec["sign_test_p"], 4)
    arm_d = across.get("extensions", {}).get("arm_d")
    if arm_d:
        lines["armDBeatsAWins"] = arm_d["d_beats_a_wins"]
        lines["armDBeatsBWins"] = arm_d["d_beats_b_wins"]
        lines["armDBeatsAp"] = fmt(arm_d["sign_test_p_vs_a"], 4)
        lines["armDBeatsBp"] = fmt(arm_d["sign_test_p_vs_b"], 4)
    if literature is not None:
        # The gap to the published ceiling, per label budget. Stated as a median over datasets
        # because an AUC on pathmnist and one on octmnist are not commensurable to average -
        # the same reason the hypotheses use sign tests rather than pooled AUCs.
        largest = max(curve_n)
        gaps = {"Zero": [], "Concept": [], "Pixel": []}
        for d in datasets:
            top = ceiling(literature, d)[1]["auc"]
            zero = [per[d]["auc"]["A"], per[d]["auc"][f"B__{primary}"]]
            if "D" in per[d]["auc"]:
                zero.append(per[d]["auc"]["D"])
            gaps["Zero"].append(top - max(zero))
            gaps["Concept"].append(top - per[d]["curve"][f"C__n{largest}"]["point"])
            gaps["Pixel"].append(top - per[d]["curve"][f"P__n{largest}"]["point"])
        for name, values in gaps.items():
            lines[f"litGap{name}Median"] = fmt(sorted(values)[len(values) // 2])
        lines["litLargestN"] = largest
        lines["litPixelWithinTwoPoints"] = sum(1 for g in gaps["Pixel"] if g <= 0.02)
        lines["litZeroWithinFivePoints"] = sum(1 for g in gaps["Zero"] if g <= 0.05)

    for d in datasets:
        key = "".join(part.capitalize() for part in d.replace("mnist", "").split("_")) or d
        if literature is not None:
            lines[f"aucLit{key}"] = fmt(ceiling(literature, d)[1]["auc"])
        lines[f"nB{key}"] = per[d]["n_b"]["point"].replace("<=", r"$\leq$").replace(">", "$>$")
        lines[f"aucB{key}"] = fmt(per[d]["auc"][f"B__{primary}"])
        lines[f"aucA{key}"] = fmt(per[d]["auc"]["A"])
        if "D" in per[d]["auc"]:
            lines[f"aucD{key}"] = fmt(per[d]["auc"]["D"])
    text = "\n".join(rf"\newcommand{{\{k}}}{{{v}}}" for k, v in lines.items()) + "\n"
    (Path(dest) / "numbers.tex").write_text(text)
    return lines
