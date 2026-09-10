"""report: the reconciliation, every table and number macro, and the three figures, from results/ alone
(WORKFLOW.md section 5, principles 2, 7 and 10).

Nothing here computes a statistic: the numbers come from results/evaluate/*.json, summary.json and
results/train/*.json, and are only formatted. The one exception the plan allows is the ladder
figure's within-dataset centring, which belongs to the figure and not to a new statistic.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np

from . import data as D
from .manifest import Run

MARK = {"qwen": "o", "gemma": "s"}
COL = {"qwen": "#1f77b4", "gemma": "#d62728"}


def _load(cfg, rel):
    return json.loads((D._path(cfg["outdir"]) / rel).read_text())


def fmt(x, d=3):
    if x is None or (isinstance(x, float) and not math.isfinite(x)):
        return "--"
    return f"{x:.{d}f}"


def pval(p):
    if p is None or not math.isfinite(p):
        return "--"
    return "$<$0.001" if p < 0.001 else f"{p:.3f}"


def tex(s) -> str:
    return str(s).replace("_", r"\_").replace("&", r"\&").replace("%", r"\%").replace("<=", r"$\leq$").replace(">", r"$>$")


def _write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


# ---- reconciliation -----------------------------------------------------------------------------

def reconcile(cfg: dict, out, log=print) -> None:
    pub = D.load_yaml(cfg["published"])["resnet18"]
    tol = cfg["reconcile"]
    rows = []
    for ds in cfg["datasets"]:
        for size in cfg["recon_sizes"]:
            res = []
            for s in cfg["train"]["seeds"]:
                p = D._path(cfg["outdir"]) / "train" / f"{ds}__s{size}__seed{s}.json"
                if p.exists():
                    res.append(json.loads(p.read_text())["metrics"]["test_full"])
            if not res:
                continue
            auc = np.array([r["auc"] for r in res])
            acc = np.array([r["acc"] for r in res])
            pa, pc = pub[ds][int(size)]["auc"], pub[ds][int(size)]["acc"]
            rows.append({"dataset": ds, "size": int(size), "n_seeds": len(res),
                         "auc_mean": float(auc.mean()), "auc_sd": float(auc.std(ddof=1)) if len(auc) > 1 else None,
                         "acc_mean": float(acc.mean()), "acc_sd": float(acc.std(ddof=1)) if len(acc) > 1 else None,
                         "published_auc": pa, "published_acc": pc,
                         "d_auc": float(auc.mean() - pa), "d_acc": float(acc.mean() - pc),
                         "agrees": bool(abs(auc.mean() - pa) <= tol["tol_auc"] and abs(acc.mean() - pc) <= tol["tol_acc"])})
    with Run("reconcile", dict(tol_auc=tol["tol_auc"], tol_acc=tol["tol_acc"], seeds=cfg["train"]["seeds"])) as run:
        run.write(out, {"rows": rows, "n_rows": len(rows), "n_agree": int(sum(r["agrees"] for r in rows)),
                        "expected_rows": len(cfg["datasets"]) * len(cfg["recon_sizes"])})
    log(f"reconciliation: {sum(r['agrees'] for r in rows)} of {len(rows)} cells within tolerance")


# ---- tables --------------------------------------------------------------------------------------

def _ci(v, d=3):
    return f"[{fmt(v[0], d)}, {fmt(v[2], d)}]"


def tables(cfg: dict, dest, log=print) -> None:
    dest = Path(dest)
    summ = _load(cfg, "evaluate/summary.json")
    per = {ds: _load(cfg, f"evaluate/{ds}.json") for ds in cfg["datasets"]}
    rec = _load(cfg, "report/reconciliation.json")
    primary = cfg["vlm"]["primary"]
    models = list(cfg["vlm"]["models"])
    n0 = str(cfg["curve"]["n"][0])
    H1, H2, H3 = summ["H1"], summ["H2"], summ["H3"]

    # H1: the substitution table
    L = [r"\begin{tabular}{lrrrcl}", r"\toprule",
         rf"dataset & AUC(B) & AUC(C, $n={n0}$) & AUC(P, $n={n0}$) & C $>$ P & $n_B$ [95\% CI] \\", r"\midrule"]
    for ds in cfg["datasets"]:
        r = per[ds]
        b = fmt(r["auc"]["B"][primary]) if r["arm_b"] else "--"
        c = f"{fmt(r['auc']['C'][n0]['mean'])} {_ci(r['bootstrap']['C'][n0])}"
        p = f"{fmt(r['auc']['P'][n0]['mean'])} {_ci(r['bootstrap']['P'][n0])}"
        win = r"$\checkmark$" if r["auc"]["C"][n0]["mean"] > r["auc"]["P"][n0]["mean"] else ""
        nb = f"{tex(r['n_b']['label'])} [{tex(r['n_b']['ci_labels'][0])}, {tex(r['n_b']['ci_labels'][1])}]" if r["arm_b"] else "--"
        flag = r"$^\dagger$" if summ["flagged"].get(ds) else ""
        L.append(f"{tex(ds)}{flag} & {b} & {c} & {p} & {win} & {nb} \\\\")
    L += [r"\midrule", rf"wins & & & & {H1['wins']} of {H1['n']} (p = {pval(H1['p'])}) & median {tex(H1['median_n_b_label'])} \\",
          r"\bottomrule", r"\end{tabular}"]
    _write(dest / "h1.tex", "\n".join(L) + "\n")

    # H2: the bank against the undirected model, and the permutation controls
    L = [r"\begin{tabular}{lrrlrr}", r"\toprule",
         rf"dataset & AUC(A) & AUC(B) & B $-$ A [95\% CI] & B drop (perm.\ fingerprints) & C drop (perm.\ columns, $n={n0}$) \\", r"\midrule"]
    for ds in H2["datasets"]:
        r = per[ds]
        L.append(f"{tex(ds)} & {fmt(r['auc']['A'])} & {fmt(r['auc']['B'][primary])} & {fmt(r['bootstrap']['diff_B_minus_A'][1])} "
                 f"{_ci(r['bootstrap']['diff_B_minus_A'])} & {fmt(H2['perm_drop_B'][ds])} & {fmt(H2['perm_drop_C_at_first_n'][ds])} \\\\")
    L += [r"\midrule", rf"wins B $>$ A & & {H2['wins']} of {H2['n']} & p = {pval(H2['p'])} & & \\", r"\bottomrule", r"\end{tabular}"]
    _write(dest / "h2.tex", "\n".join(L) + "\n")

    # H3: the ladder table and its analysis
    L = [r"\begin{tabular}{l" + "r" * len(models) + "}", r"\toprule",
         "dataset & " + " & ".join(tex(m) for m in models) + r" \\", r"\midrule"]
    for ds in H3["datasets"]:
        L.append(f"{tex(ds)} & " + " & ".join(fmt(H3["table"][ds][m]) for m in models) + r" \\")
    if "anova" in H3:
        a = H3["anova"]
        L += [r"\midrule", "mean & " + " & ".join(fmt(a["model_means"][m]) for m in models) + r" \\"]
        if H3.get("friedman"):
            L.append("average rank & " + " & ".join(fmt(H3["friedman"]["average_ranks"][m], 2) for m in models) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    _write(dest / "ladder.tex", "\n".join(L) + "\n")
    L = [r"\begin{tabular}{lrrrr}", r"\toprule", r"source & df & F & p & estimate \\", r"\midrule"]
    if "anova" in H3:
        a = H3["anova"]["anova"]
        for name, key in (("model (4 levels)", "model"), ("dataset (block)", "block")):
            L.append(f"{name} & {a[key]['df']} & {fmt(a[key]['F'], 2)} & {pval(a[key]['p'])} & \\\\")
        for name, key in (("family", "family"), ("size tier", "size_tier"), (r"family $\times$ size", "interaction")):
            L.append(f"{name} & 1 & {fmt(a[key]['F'], 2)} & {pval(a[key]['p'])} & {fmt(a[key]['estimate'])} \\\\")
        t = H3["anova"]["trend_log10_params"]
        L.append(rf"linear trend on $\log_{{10}}$ parameters & 1 & {fmt(t['F'], 2)} & {pval(t['p_one_sided_positive'])} (one-sided) & {fmt(t['estimate'])} AUC per decade \\")
        L.append(f"error & {a['error']['df']} & & & MSE {fmt(a['error']['mse'], 5)} \\\\")
        if H3.get("friedman"):
            f = H3["friedman"]
            L += [r"\midrule", rf"Friedman $\chi^2$ & {len(models) - 1} & {fmt(f['chi2'], 2)} & {pval(f['p'])} & Nemenyi CD {fmt(f['critical_difference'], 2)} \\"]
    L += [r"\bottomrule", r"\end{tabular}"]
    _write(dest / "ladder_anova.tex", "\n".join(L) + "\n")

    # reconciliation
    L = [r"\begin{tabular}{lrrrrrrl}", r"\toprule",
         r"dataset & size & AUC (ours) & AUC (published) & ACC (ours) & ACC (published) & $\Delta$AUC & agrees \\", r"\midrule"]
    for r in rec["rows"]:
        sd = f" $\\pm$ {fmt(r['auc_sd'])}" if r["auc_sd"] is not None else ""
        L.append(f"{tex(r['dataset'])} & {r['size']} & {fmt(r['auc_mean'])}{sd} & {fmt(r['published_auc'])} & {fmt(r['acc_mean'])} & "
                 f"{fmt(r['published_acc'])} & {r['d_auc']:+.3f} & {'yes' if r['agrees'] else 'no'} \\\\")
    L += [r"\midrule", rf"within tolerance & & & & & & & {rec['n_agree']} of {rec['n_rows']} \\", r"\bottomrule", r"\end{tabular}"]
    _write(dest / "reconciliation.tex", "\n".join(L) + "\n")

    # completeness
    cells = sorted({k for r in per.values() for k in r["completeness"]})
    L = [r"\begin{tabular}{l" + "r" * len(cells) + "}", r"\toprule",
         "dataset & " + " & ".join(tex(c) for c in cells) + r" \\", r"\midrule"]
    for ds in cfg["datasets"]:
        vals = []
        for c in cells:
            v = per[ds]["completeness"].get(c)
            vals.append("--" if v is None else f"{100 * v['frac_incomplete']:.1f}\\%" + (r"$^\dagger$" if v.get("flagged") else ""))
        L.append(f"{tex(ds)} & " + " & ".join(vals) + r" \\")
    L += [r"\bottomrule", r"\end{tabular}"]
    _write(dest / "completeness.tex", "\n".join(L) + "\n")

    # number macros, including the sentences whose direction depends on a value
    calls = sum(v.get("calls", 0) for r in per.values() for v in r["completeness"].values())
    M = {
        "hOneWins": f"{H1['wins']}", "hOneN": f"{H1['n']}", "hOneP": pval(H1["p"]), "nBmedian": tex(H1["median_n_b_label"]),
        "hOneVerdict": "supported" if H1["supported"] else "not supported",
        "hTwoWins": f"{H2['wins']}", "hTwoN": f"{H2['n']}", "hTwoP": pval(H2["p"]),
        "hTwoVerdict": "supported" if H2["supported"] else "not supported",
        "hTwoControls": "both controls lose AUC on every dataset" if H2["controls_lose"] else "at least one control does not lose AUC on some dataset",
        "hThreeVerdict": "supported" if H3.get("supported") else "not supported",
        "reconAgree": f"{rec['n_agree']}", "reconRows": f"{rec['n_rows']}", "reconExpected": f"{rec['expected_rows']}",
        "callsArchived": f"{calls:,}", "primaryModel": tex(primary), "firstN": n0,
        "nDatasets": f"{len(cfg['datasets'])}", "nArmB": f"{len([d for d in cfg['datasets'] if d not in cfg['arm_b_exclude']])}",
        "flaggedCells": f"{sum(len(v) for v in summ['flagged'].values())}",
    }
    if "anova" in H3:
        t = H3["anova"]["trend_log10_params"]
        M.update({"hThreeSlope": fmt(t["estimate"]), "hThreeP": pval(t["p_one_sided_positive"]),
                  "hThreeInteractionP": pval(H3["anova"]["anova"]["interaction"]["p"]),
                  "hThreeDirection": "rises" if t["estimate"] > 0 else "does not rise"})
        if H3.get("friedman"):
            M.update({"friedmanP": pval(H3["friedman"]["p"]),
                      "friedmanAgrees": "agrees with" if H3.get("agree") else "disagrees with"})
    _write(dest / "numbers.tex", "".join(f"\\newcommand{{\\{k}}}{{{v}}}\n" for k, v in M.items()))
    log(f"wrote {len(list(dest.glob('*.tex')))} tables to {dest}")


# ---- figures -------------------------------------------------------------------------------------

def figures(cfg: dict, dest, log=print) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    summ = _load(cfg, "evaluate/summary.json")
    per = {ds: _load(cfg, f"evaluate/{ds}.json") for ds in cfg["datasets"]}
    primary = cfg["vlm"]["primary"]
    models = list(cfg["vlm"]["models"])
    mcfg = cfg["vlm"]["models"]

    # the learning curve: C against P, arm B's line, arm E's ceiling (H1)
    ds_list = cfg["datasets"]
    ncol = 4
    nrow = math.ceil(len(ds_list) / ncol)
    fig, axes = plt.subplots(nrow, ncol, figsize=(3.4 * ncol, 2.9 * nrow), sharex=True, squeeze=False)
    for ax, ds in zip(axes.flat, ds_list):
        r = per[ds]
        grid = r["grid"]
        for arm, col, lab in (("C", "#2ca02c", "C: concept scores"), ("P", "#7f7f7f", "P: ImageNet features")):
            m = [r["auc"][arm][str(n)]["mean"] for n in grid]
            lo = [r["bootstrap"][arm][str(n)][0] for n in grid]
            hi = [r["bootstrap"][arm][str(n)][2] for n in grid]
            ax.plot(grid, m, "-o", color=col, ms=3, lw=1.4, label=lab)
            ax.fill_between(grid, lo, hi, color=col, alpha=0.15, lw=0)
        if r["arm_b"]:
            b = r["auc"]["B"][primary]
            ax.axhline(b, color="#d62728", lw=1.2, ls="--", label="B: textbook only, 0 labels")
            bl, _, bh = r["bootstrap"]["B"][primary]
            ax.axhspan(bl, bh, color="#d62728", alpha=0.1, lw=0)
            pos = r["n_b"]["position"]
            if 0 <= pos < len(grid):
                ax.plot([grid[pos]], [b], marker="v", color="k", ms=6, zorder=5)
        e = r["auc"]["E"].get(str(cfg["size"]))
        if e:
            ax.axhline(e["sample_auc_mean"], color="k", lw=1.0, ls=":", label="E: ResNet-18, full split")
        ax.set_xscale("log")
        ax.set_title(ds + (f"  $n_B$ = {r['n_b']['label']}" if r["arm_b"] else "  (not in arm B)"), fontsize=9, loc="left")
        ax.spines[["top", "right"]].set_visible(False)
        ax.tick_params(labelsize=7)
    for ax in axes.flat[len(ds_list):]:
        ax.axis("off")
    for ax in axes[-1]:
        ax.set_xlabel("labelled images n", fontsize=8)
    for ax in axes[:, 0]:
        ax.set_ylabel("test AUC", fontsize=8)
    h, l = axes.flat[0].get_legend_handles_labels()
    fig.legend(h, l, loc="lower center", ncol=4, frameon=False, fontsize=8)
    fig.tight_layout(rect=[0, 0.05, 1, 1])
    fig.savefig(dest / "fig_curve.png", dpi=170)
    plt.close(fig)

    # the model ladder (H3)
    H3 = summ["H3"]
    ds3 = H3["datasets"]
    order = sorted(models, key=lambda m: mcfg[m]["params_b"])
    x = np.arange(len(order))
    A = np.array([[H3["table"][ds][m] for m in order] for ds in ds3]) if ds3 else np.zeros((0, len(order)))
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.5, 4.8), sharex=True)
    for i, ds in enumerate(ds3):
        ax1.plot(x, A[i], lw=0.9, alpha=0.55, color="0.45", zorder=1)
        ax1.annotate(ds, (x[-1], A[i, -1]), xytext=(6, 0), textcoords="offset points", fontsize=6, va="center", color="0.35")
    for j, m in enumerate(order):
        fam = mcfg[m]["family"]
        ax1.scatter([x[j]] * len(ds3), A[:, j], s=16, marker=MARK[fam], color=COL[fam], zorder=3, linewidths=0)
    ax1.set_ylabel("arm B test AUC")
    ax1.set_title("per dataset, as measured", fontsize=10, loc="left")
    if len(ds3):
        cent = A - A.mean(axis=1, keepdims=True)
        for i in range(len(ds3)):
            ax2.plot(x, cent[i], lw=0.9, alpha=0.45, color="0.6", zorder=1)
        m_ = cent.mean(axis=0)
        from scipy import stats as st
        ci = st.t.ppf(0.975, max(len(ds3) - 1, 1)) * cent.std(axis=0, ddof=1) / np.sqrt(len(ds3)) if len(ds3) > 1 else np.zeros_like(m_)
        ax2.errorbar(x, m_, yerr=ci, color="k", lw=1.6, capsize=4, zorder=4, label="mean $\\pm$ 95% CI")
        for j, m in enumerate(order):
            fam = mcfg[m]["family"]
            ax2.scatter([x[j]], [m_[j]], s=70, marker=MARK[fam], color=COL[fam], edgecolor="k", linewidths=0.8, zorder=5)
        ax2.legend(frameon=False, fontsize=8, loc="upper left")
    ax2.axhline(0, color="0.7", lw=0.8, ls=":", zorder=0)
    ax2.set_ylabel("AUC centred within dataset")
    ax2.set_title("centred within dataset: read the trend here", fontsize=10, loc="left")
    for ax in (ax1, ax2):
        ax.set_xticks(x)
        ax.set_xticklabels([f"{m}\n{mcfg[m]['params_b']}B" for m in order], fontsize=8)
        ax.set_xlabel("model, ordered by parameter count")
        ax.spines[["top", "right"]].set_visible(False)
    handles = [plt.Line2D([], [], marker=MARK[f], color=COL[f], ls="", label=f) for f in MARK]
    ax1.legend(handles=handles, frameon=False, fontsize=8, loc="upper left", title="family", title_fontsize=8, ncols=2)
    ax1.set_xlim(-0.35, len(order) - 0.55)
    if "anova" in H3:
        t = H3["anova"]["trend_log10_params"]
        fig.suptitle(f"linear trend on log10 parameters: {t['estimate']:+.4f} AUC per decade, one-sided p = {t['p_one_sided_positive']:.3f}; "
                     f"Friedman p = {H3['friedman']['p']:.3f}" if H3.get("friedman") else "", fontsize=9, y=0.995)
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(dest / "fig_ladder.png", dpi=170)
    plt.close(fig)

    # n_B per dataset, ordered by modality (H1 detail)
    rows = [ds for ds in cfg["modality_order"] if ds in per and per[ds]["arm_b"]]
    fig, ax = plt.subplots(figsize=(7, 0.42 * len(rows) + 1.2))
    nmax = max(cfg["curve"]["n"])
    for i, ds in enumerate(rows):
        nb = per[ds]["n_b"]
        grid = per[ds]["grid"]

        def val(label):
            return grid[-1] * 1.5 if label.startswith(">") else float(label[2:]) if label.startswith("<=") else float(label)
        v = val(nb["label"])
        lo, hi = val(nb["ci_labels"][0]), val(nb["ci_labels"][1])
        ax.plot([lo, hi], [i, i], color="0.6", lw=2, solid_capstyle="round", zorder=1)
        marker = ">" if nb["label"].startswith(">") else "<" if nb["label"].startswith("<=") else "o"
        ax.plot([v], [i], marker=marker, color="#d62728" if marker != "o" else "k", ms=7, zorder=3)
        if summ["flagged"].get(ds):
            ax.annotate("flagged", (v, i), xytext=(8, 0), textcoords="offset points", fontsize=7, va="center", color="0.4")
    ax.set_yticks(range(len(rows)))
    ax.set_yticklabels(rows, fontsize=8)
    ax.set_xscale("log")
    ax.set_xlabel("$n_B$: labelled images at which the pixel probe reaches the textbook (95% CI); arrows are censored at the grid edge", fontsize=8)
    ax.axvline(nmax, color="0.8", lw=0.8, ls=":")
    ax.invert_yaxis()
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(dest / "fig_nb.png", dpi=170)
    plt.close(fig)
    log(f"wrote 3 figures to {dest}")
