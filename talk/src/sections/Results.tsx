import { useState } from "react";
import { useTalk } from "../state";
import { Band, Bullets, ChartFrame, DatasetPicker, Deep, Dots, Header } from "../components/ui";
import { LearningCurve } from "../charts/LearningCurve";
import { Dumbbell, PermutationDrops } from "../charts/Dumbbell";
import { Forest } from "../charts/Forest";
import { results as copy } from "../content";
import { fmt3, signed } from "../charts/primitives";

/* The one results figure the talk shows. A question picker presets which arms are drawn, so the
   same axes answer three questions instead of three sections doing it. Everything that supports
   one of the three sits in a closed panel under it: the room pays nothing, a reader can open it. */

export function Results() {
  const { study, dataset, setDataset, armHue } = useTalk();
  const [choice, setChoice] = useState<string>("h1");
  const sel = copy.choices.find((c) => c.id === choice)!;
  const v = study.verdicts.find((x) => x.id === choice)!;

  const h1 = study.across.h1;
  const h2 = study.across.h2;
  const h5 = study.across.h5;
  const armB = study.study.arm_b_datasets;
  const firstN = study.study.curve.n[0];
  const per = study.per_dataset[dataset];
  const tissue = study.per_dataset["tissuemnist"];

  // H1's crossing point only exists where arm P started below arm B.
  const crossing = armB
    .filter((d) => /^\d+$/.test(study.per_dataset[d].n_b?.point ?? ""))
    .sort((a, b) => Number(study.per_dataset[b].n_b!.point)
                    - Number(study.per_dataset[a].n_b!.point));
  const crosses = per.n_b != null && /^\d+$/.test(per.n_b.point);
  const elsewhere = crossing.find((d) => d !== dataset);

  const median = (xs: number[]) => {
    const s = [...xs].sort((a, b) => a - b); const m = Math.floor(s.length / 2);
    return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
  };
  const h5rows = study.study.datasets
    .map((d) => {
      const byN = h5.differences_by_n[d]?.[String(h5.n)];
      return byN ? { dataset: d, ...(byN as { median: number; lo: number; hi: number }) } : null;
    })
    .filter(Boolean) as { dataset: string; median: number; lo: number; hi: number }[];

  return (
    <Band id="results">
      <Header id="results" eyebrow="6">{copy.header}</Header>
      <p className="lede">
        {copy.ledeShape.replace("{primary}", study.study.primary)}
      </p>

      <div className="controls" role="group" aria-label="Question">
        <span className="group-label">question</span>
        {copy.choices.map((c) => (
          <button key={c.id} className="chip" aria-pressed={choice === c.id}
                  onClick={() => setChoice(c.id)}>
            {c.chip}
          </button>
        ))}
      </div>
      <p>{sel.asks}</p>

      <DatasetPicker />
      <ChartFrame
        caption={`${dataset}: test AUC against the number of labelled images. Toggle any arm in ` +
                 "the legend."}>
        <LearningCurve height={440} initialHidden={sel.hidden} />
      </ChartFrame>

      {choice === "h1" && (
        <>
          <p>
            At n = {firstN} a classifier fitted on the feature scores beats one fitted on
            pretrained image features on {h1.c_beats_p_wins} of {h1.n_datasets}, against the{" "}
            {h1.min_wins} needed to count as support
            (p = {h1.c_beats_p_sign_test_p.toFixed(4)}). On{" "}
            {h1.datasets_where_the_probe_starts_above_arm_b} of the {armB.length} datasets that
            have an arm B, pretrained image features are already ahead of it at n = {firstN}.
          </p>
          {!crosses && elsewhere && (
            <p className="note">
              No crossing here: arm P starts above arm B. See{" "}
              <button className="inline" onClick={() => setDataset(elsewhere)}>{elsewhere}</button>,
              where it crosses at {study.per_dataset[elsewhere].n_b!.point}.
            </p>
          )}
          <Deep summary="How many labelled images arm P needed to match arm B">
            <table className="data" style={{ maxWidth: "36rem" }}>
              <thead>
                <tr><th>dataset</th><th className="nowrap">labels needed</th>
                    <th style={{ textAlign: "left" }}>95% interval</th></tr>
              </thead>
              <tbody>
                {armB.map((d) => {
                  const nb = study.per_dataset[d].n_b!;
                  return (
                    <tr key={d}>
                      <td>{d}</td>
                      <td className="mono">{nb.point}</td>
                      <td style={{ textAlign: "left" }} className="mono">
                        [{nb.lo}, {nb.hi}]
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <p className="note">
              <span className="mono">&lt;=50</span> means arm P was already ahead at the
              smallest labelled set we tried.
            </p>
          </Deep>
        </>
      )}

      {choice === "h2" && (
        <>
          <p>
            Arm B, the feature scores read against what the literature expects, beat arm A
            on{" "}
            {h2.b_beats_a_wins} of {armB.length}, against the {h2.min_wins} needed to count as
            support (p = {h2.b_beats_a_sign_test_p.toFixed(4)}). On tissuemnist the model's own guess is{" "}
            {fmt3(tissue.auc["A"])} — chance — and the feature scores still reach{" "}
            {fmt3(tissue.auc[`B__${study.study.primary}`])}.
          </p>
          <Deep summary="The two arms side by side, and what is left when the bank is shuffled">
            <ChartFrame
              caption="Arm A against arm B on the same images. The letter at the right is which arm won.">
              <Dumbbell />
            </ChartFrame>
            <ChartFrame
              caption="What each arm loses when the bank is shuffled. Both lose everywhere, so the feature scores carry real class information.">
              <PermutationDrops />
            </ChartFrame>
          </Deep>
          <Deep summary="Why the comparison cannot be circular">
            {copy.circular.map((p, i) => <p key={i}>{p}</p>)}
          </Deep>
        </>
      )}

      {choice === "h5" && (
        <>
          <p>
            At n = {h5.n} the combined arm beats pretrained image features alone on {h5.wins} of{" "}
            {h5.n_datasets}, against the {h5.min_wins} needed to count as support
            (p = {h5.sign_test_p.toFixed(4)}): <strong>{v.verdict}</strong>. Median gain{" "}
            {signed(median(Object.values(h5.differences).map((d) => (d as { median: number }).median)))}{" "}
            AUC.
          </p>
          <Deep summary="The gain on every dataset, with its interval">
            <ChartFrame
              caption={`Arm C+P minus arm P at n = ${h5.n}: two classifiers fitted the same ` +
                       "way, one on the image features alone and one on those features with " +
                       "the feature scores alongside them."}>
              <Forest rows={h5rows} colour={armHue("CP")}
                      label={`arm C+P minus arm P at n = ${h5.n}`}
                      annotate={["no gain", "gain"]} />
            </ChartFrame>
          </Deep>
        </>
      )}

      <p className="tally">
        <Dots per={v.per_dataset} order={study.study.datasets} label={`${v.id} per dataset`} />{" "}
        <span className="note" style={{ display: "inline" }}>
          {v.wins} of {v.n_datasets}, against {v.threshold} needed — {v.verdict}.
        </span>
      </p>

      <Bullets items={copy.bullets} />
    </Band>
  );
}
