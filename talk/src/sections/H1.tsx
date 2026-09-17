import { useTalk } from "../state";
import { Band, Callout, ChartFrame, DatasetPicker, Deep, Dots, Header } from "../components/ui";
import { LearningCurve } from "../charts/LearningCurve";
import { Contention } from "../charts/Contention";
import { h1 as copy } from "../content";
import { useAsync } from "../hooks";
import { loadContention } from "../data";
import { fmt3, signed } from "../charts/primitives";

export function H1() {
  const { study, dataset, setDataset } = useTalk();
  const v = study.verdicts.find((x) => x.id === "h1")!;
  const h1 = study.across.h1;
  const { data: contention } = useAsync(loadContention);
  const per = study.per_dataset[dataset];
  const diff = per.differences["C_minus_P__n50"];
  const firstN = study.study.curve.n[0];

  // n_B is "<=50" wherever the pixel arm was already above arm B at the first grid point, so the
  // count of non-numeric n_B values is the count of tasks the textbook was worth less than one
  // grid step on. The datasets that do cross are the ones worth showing the idea on.
  const nbs = h1.n_b as Record<string, string>;
  const belowGrid = Object.values(nbs).filter((s) => !/^\d+$/.test(s)).length;
  const crossing = study.study.arm_b_datasets
    .filter((d) => /^\d+$/.test(study.per_dataset[d].n_b?.point ?? ""))
    .sort((a, b) => Number(study.per_dataset[b].n_b!.point)
                    - Number(study.per_dataset[a].n_b!.point));
  const crosses = per.n_b != null && /^\d+$/.test(per.n_b.point);
  const elsewhere = crossing.find((d) => d !== dataset);

  return (
    <Band id="h1">
      <Header id="h1" eyebrow="5">{copy.header}</Header>
      <p className="lede">
        Concept answers lose to pixel features at every labelled-set size we tried: the textbook
        is worth fewer than {firstN} labels on {belowGrid} tasks of{" "}
        {study.study.arm_b_datasets.length}. {copy.lede}
      </p>
      <p>
        The pixel arm is already above the textbook arm at the first grid point on{" "}
        {h1.datasets_where_the_probe_starts_above_arm_b} of the{" "}
        {study.study.arm_b_datasets.length} datasets that have one, and reaches it on every
        dataset. The concept arm beats the pixel arm at n = {study.study.curve.n[0]} on{" "}
        {h1.c_beats_p_wins} of {h1.n_datasets}, against the {h1.min_wins} the rule asks for
        (p = {h1.c_beats_p_sign_test_p.toFixed(4)}).
      </p>
      {copy.body.map((p, i) => <p key={i}>{p}</p>)}

      <DatasetPicker />
      <ChartFrame
        caption={`Arms on ${dataset}: test AUC against labelled images, with 95% bootstrap bands. ` +
                 "Toggle a series in the legend; hover a point for its interval."}
        source="public/data/study.json ← results/evaluate/*.json"
        summary={
          <p>
            On {dataset} the concept arm minus the pixel arm at n = 50 is {signed(diff.median)},
            95% interval [{fmt3(diff.lo)}, {fmt3(diff.hi)}]. n_B, the labels the pixel arm needs
            to reach the zero-label textbook arm, is {per.n_b?.point ?? "not defined (no arm B)"}.
            The published fully supervised ceiling for this task is {fmt3(per.ceiling.auc)} (
            {per.ceiling.method}).
          </p>
        }>
        {/* Two series by default - the flat textbook arm and the rising pixel arm - and the rest
            behind the legend, so the projected chart is one comparison the speaker builds on. */}
        <LearningCurve height={440} initialHidden={["C", "CP", "A", "lit"]} />
      </ChartFrame>
      {!crosses && elsewhere && (
        <p className="note">
          No crossing here: the pixel arm starts above the textbook arm. See{" "}
          <button className="inline" onClick={() => setDataset(elsewhere)}>{elsewhere}</button>,
          where it crosses at {study.per_dataset[elsewhere].n_b!.point}.
        </p>
      )}

      <h3>Where the concept arm beat the pixel arm at n = {study.study.curve.n[0]}</h3>
      <p>
        <Dots per={v.per_dataset} order={study.study.datasets} label="H1 per dataset" />{" "}
        <span className="note" style={{ display: "inline" }}>
          {v.wins} of {v.n_datasets}, against {v.threshold} needed — {v.verdict}.
        </span>
      </p>

      <Deep summary="n_B per dataset, and its interval">
        <table className="data" style={{ maxWidth: "36rem" }}>
          <thead>
            <tr><th>dataset</th><th>n_B</th><th style={{ textAlign: "left" }}>95% interval</th></tr>
          </thead>
          <tbody>
            {study.study.arm_b_datasets.map((d) => {
              const nb = study.per_dataset[d].n_b!;
              return (
                <tr key={d}>
                  <td>{d}</td>
                  <td className="mono">{nb.point}</td>
                  <td style={{ textAlign: "left" }} className="mono">[{nb.lo}, {nb.hi}]</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <p className="note">
          <span className="mono">&lt;=50</span> means the pixel arm was already above arm B at
          the first grid point; the resolution of n_B is the grid and nothing finer.
        </p>
      </Deep>

      <div className="callouts">
        <Callout spec={copy.callouts[0]} />
      </div>
      {contention && (
        <ChartFrame
          caption="Seconds per call against our own jobs in flight. Two points per series, not a curve."
          source="public/data/contention.json ← CHANGELOG.md 2026-09-12"
          summary={
            <>
              <table className="data" style={{ maxWidth: "36rem" }}>
                <thead>
                  <tr><th>series</th><th>jobs</th><th>s/call</th><th>calls/s</th></tr>
                </thead>
                <tbody>
                  {contention.series.flatMap((s) => s.points.map((p) => (
                    <tr key={`${s.id}-${p.jobs}`}>
                      <td>{s.label}</td><td>{p.jobs}</td><td>{p.s_per_call}</td>
                      <td>{p.calls_per_s}</td>
                    </tr>
                  )))}
                </tbody>
              </table>
              <p>{contention.note}</p>
            </>
          }>
          <Contention data={contention} />
        </ChartFrame>
      )}
    </Band>
  );
}
