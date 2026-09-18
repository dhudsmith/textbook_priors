import { useTalk } from "../state";
import { Band, Body, Callouts, ChartFrame, Deep, Dots, Header, Slide } from "../components/ui";
import { Dumbbell, PermutationDrops } from "../charts/Dumbbell";
import { h2 as copy } from "../content";
import { fmt3, signed } from "../charts/primitives";

export function H2() {
  const { study } = useTalk();
  const h2 = study.across.h2;
  const v = study.verdicts.find((x) => x.id === "h2")!;
  const primary = study.study.primary;
  const armB = study.study.arm_b_datasets;
  const tissue = study.per_dataset["tissuemnist"];

  return (
    <Band id="h2">
      <Slide title={<Header id="h2" eyebrow="6">{copy.header}</Header>}>
      <p className="lede">{copy.lede}</p>
      <p>
        Arm B beat arm A on {h2.b_beats_a_wins} of {armB.length}, against the {h2.min_wins} the
        rule asks for (p = {h2.b_beats_a_sign_test_p.toFixed(4)}): {v.verdict}. But both arms lose
        AUC under their permutation controls on every dataset they run on — {" "}
        {Object.values(h2.b_loses_under_permutation).filter(Boolean).length} of {armB.length} for
        arm B, {Object.values(h2.c_loses_under_permutation).filter(Boolean).length} of{" "}
        {study.study.datasets.length} for arm C.
      </p>
      <p>
        On tissuemnist the model's own guess is {fmt3(tissue.auc["A"])} — at chance — while the
        textbook readout reaches {fmt3(tissue.auc[`B__${primary}`])}.
      </p>
      <Body paras={[copy.body[0]]} bullets={copy.bullets} />
      <Deep summary="Why the comparison cannot be circular">
        {copy.body.slice(1).map((p, i) => <p key={i}>{p}</p>)}
      </Deep>
      </Slide>

      <Slide cont title={<div className="conthead">{copy.header}</div>}>
      <ChartFrame
        caption="Arm A against arm B on the same images. The letter at the right is which arm won."
        source="public/data/study.json ← results/evaluate/*.json"
        summary={
          <table className="data" style={{ maxWidth: "40rem" }}>
            <thead>
              <tr><th>dataset</th><th>arm A</th><th>arm B</th>
                  <th style={{ textAlign: "left" }}>B − A, 95%</th></tr>
            </thead>
            <tbody>
              {armB.map((d) => {
                const p = study.per_dataset[d];
                const diff = p.differences["B_minus_A"];
                return (
                  <tr key={d}>
                    <td>{d}</td><td>{fmt3(p.auc["A"])}</td>
                    <td>{fmt3(p.auc[`B__${primary}`])}</td>
                    <td style={{ textAlign: "left" }}>
                      {signed(diff.median)} [{fmt3(diff.lo)}, {fmt3(diff.hi)}]
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        }>
        <Dumbbell />
      </ChartFrame>

      </Slide>

      <Slide cont title={<div className="conthead">{copy.header}</div>}>
      <ChartFrame
        caption="What each arm loses when the bank's structure is destroyed. Both lose everywhere."
        source="public/data/study.json ← results/evaluate/*.json (permutation controls)"
        summary={
          <p>
            Arm B's fingerprints permuted across classes and arm C's concept columns permuted
            across images. Both drops are positive on every dataset either arm runs on, which is
            what says the concept answers carry real class information rather than a constant.
          </p>
        }>
        <PermutationDrops />
      </ChartFrame>

      <p className="tally">
        <Dots per={v.per_dataset} order={armB} label="H2 per dataset" />{" "}
        <span className="note" style={{ display: "inline" }}>
          arm B over arm A: {v.wins} of {v.n_datasets}, against {v.threshold} needed — {v.verdict}.
        </span>
      </p>

      <Callouts items={copy.callouts} />
      </Slide>
    </Band>
  );
}
