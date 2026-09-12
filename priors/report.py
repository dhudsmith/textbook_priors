"""report: every figure, table and number the technical report states, from results/ alone.

No number in the report is typed by hand. Each table is generated here and included by report.tex,
and the sentences whose direction depends on a value read a macro from `numbers.tex` rather than
asserting something a later run could contradict. If a figure and the prose ever disagree, it is
because someone edited the prose.

Three figures, one per hypothesis (WORKFLOW.md section 6): the learning curve with arm B's line,
n_B per dataset, and the model ladder.
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ARM_LABEL = {"C": "arm C: concept scores", "P": "arm P: ImageNet features",
             "B": "arm B: textbook only (no labels)", "A": "arm A: zero-shot (no labels)"}
ARM_COLOUR = {"C": "#1f77b4", "P": "#d62728", "B": "#2ca02c", "A": "#7f7f7f"}


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

def figure_curve(per, datasets, curve_n, dest):
    """H1: what the labels buy, against what the textbook gives for nothing.

    One panel per dataset. Arms C and P are the same classifier on different features, so the gap
    between the curves is the features; arm B is a horizontal line because it uses no labels at all,
    and where the red curve crosses it is n_B.
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


def table_completeness(per, datasets, dest):
    models = sorted(next(iter(per.values()))["complete_frac"])
    rows = [[tex_escape(d)] + [f"{100 * per[d]['complete_frac'][m]:.1f}" for m in models]
            for d in datasets]
    _table(dest, "completeness", ["dataset"] + [tex_escape(m) for m in models], rows,
           "Percentage of test images for which every concept came back with a level on that "
           "concept's own scale. An image with any missing answer counts as incomplete; a cell "
           "more than 5\\% incomplete is excluded from the headline.", "completeness")


def numbers(per, across, datasets, curve_n, primary, dest):
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
        "medianNB": fmt(h1["median_n_b_over_numeric"], 1) if h1["median_n_b_over_numeric"] else "--",
        "neverReached": h1["datasets_where_the_probe_never_reaches_arm_b"],
        "startedAbove": h1["datasets_where_the_probe_starts_above_arm_b"],
        "friedmanP": fmt(h3["friedman"]["p"], 4),
    }
    for family, spec in h3["ladder"].items():
        lines[f"ladder{family.capitalize()}Wins"] = spec["wins"]
        lines[f"ladder{family.capitalize()}P"] = fmt(spec["sign_test_p"], 4)
    for d in datasets:
        key = "".join(part.capitalize() for part in d.replace("mnist", "").split("_")) or d
        lines[f"nB{key}"] = per[d]["n_b"]["point"].replace("<=", r"$\leq$").replace(">", "$>$")
        lines[f"aucB{key}"] = fmt(per[d]["auc"][f"B__{primary}"])
        lines[f"aucA{key}"] = fmt(per[d]["auc"]["A"])
    text = "\n".join(rf"\newcommand{{\{k}}}{{{v}}}" for k, v in lines.items()) + "\n"
    (Path(dest) / "numbers.tex").write_text(text)
    return lines
