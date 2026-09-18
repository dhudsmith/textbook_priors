import { useTalk } from "../state";
import { Band, Bullets, ChartFrame, Deep, Dots, Header } from "../components/ui";
import { Ladder } from "../charts/Ladder";
import { ThinkingScatter } from "../charts/ThinkingScatter";
import { Forest } from "../charts/Forest";
import { TimelineStrip } from "../charts/TimelineStrip";
import { thinking as copy } from "../content";
import { useAsync } from "../hooks";
import { loadTimeline } from "../data";
import { widestSpread } from "../charts/primitives";

/* One figure on the spine - what thinking did, against how well the model read without it - and
   the reader chain, the effort prediction and the day it happened in panels under it. */

export function Thinking() {
  const { study, armHue } = useTalk();
  const h4 = study.across.h4;
  const h6 = study.across.h6;
  const v4 = study.verdicts.find((x) => x.id === "h4")!;
  const v6 = study.verdicts.find((x) => x.id === "h6")!;
  const { data: timeline } = useAsync(loadTimeline);

  // The reader chain, in the order the study built it: the four thinking-off models, then the
  // thinking primary, then the gateway readers. Both lists come from the config in the snapshot.
  const chain = [...Object.keys(study.study.models), ...Object.keys(study.study.readers)]
    .filter((r) => h4.readers.includes(r));

  // The frontier step H4b measured: the gateway reader the primary was compared against, at the
  // effort they share. Read from the reader table rather than named in the copy.
  const frontier = Object.entries(study.study.readers)
    .find(([id, r]) => r.api === "gateway" && id.endsWith("-medium"))?.[1].model
    ?? Object.values(study.study.readers).find((r) => r.api === "gateway")!.model;

  const h6rows = Object.entries(h6.differences).map(([dataset, d]) => ({
    dataset, ...(d as { median: number; lo: number; hi: number }),
  }));
  const h6clear = h6rows.filter((r) => r.lo > 0 || r.hi < 0);

  return (
    <Band id="thinking">
      <Header id="thinking">{copy.header}</Header>
      <p className="lede">
        {copy.ledeShape
          .replace("{primary}", study.study.primary)
          .replace("{frontier}", frontier)}
      </p>

      <ChartFrame
        caption="Thinking's effect against how well the same model scored the visual features without it.">
        <ThinkingScatter />
      </ChartFrame>

      <p>
        The thinking step wins on {h4.h4a.wins} of {h4.n_datasets}{" "}
        (p = {h4.h4a.sign_test_p.toFixed(4)}) and the frontier model on {h4.h4b.wins}{" "}
        (p = {h4.h4b.sign_test_p.toFixed(4)}), against the {h4.min_wins} needed to count as
        support:{" "}
        {v4.verdict}. Each of the {h4.readers.length} readers gets its own classifier, fitted the
        same way on the same {h4.subsample} images, so every difference is paired.
      </p>
      <Bullets items={copy.bullets} />

      <p className="tally">
        <Dots per={v4.per_dataset} order={study.study.arm_b_datasets} label="H4a per dataset" />{" "}
        <span className="note" style={{ display: "inline" }}>
          thinking over no thinking: {h4.h4a.wins} of {h4.n_datasets} — {v4.verdict}.
        </span>
      </p>

      <Deep summary="Every reader on the same images, in the order they were tried">
        <ChartFrame
          caption={`Probe AUC on the same ${h4.subsample} images, one line per dataset. Hover a ` +
                   "line to isolate it."}>
          <Ladder order={chain} values={h4.probe_auc} yLabel="probe AUC"
                  label={`Probe AUC for each dataset across the ${chain.length} readers, ` +
                         "one line per dataset"} height={420}
                  named={widestSpread(h4.probe_auc, chain, 4, ["dermamnist"])}
                  note={"The first four readers are the models with thinking off. Each label " +
                        "is a model and the effort it was given. " +
                        "Only the datasets with the widest spread between their highest and lowest point are named and coloured, along with dermamnist, which the prediction below turns on; the rest stay grey, and hovering any line isolates it."} />
        </ChartFrame>
      </Deep>

      <Deep summary="A prediction made before the calls: was the frontier model thinking too hard?">
        <p>
          The archive showed the frontier model giving one dermoscopy feature the same score on
          every image, so a rule was written — before the calls — saying that less effort would
          fix that dataset and no other. Lowering the effort wins on {h6.wins} of {h6.n_datasets} and
          raising it on {h6.wins_for_more}, against the {h6.min_wins} either direction would need:{" "}
          {v6.verdict}. Exactly {h6clear.length} interval of the {h6rows.length} clears zero, and
          it is {h6clear.map((r) => r.dataset).join(", ")} — the one the prediction named.
        </p>
        <ChartFrame
          caption={"gpt-5.6-terra at low effort minus the same model at medium, each read by " +
                   "a classifier of its own, fitted the same way."}>
          <Forest rows={h6rows} colour={armHue("C")}
                  label="gpt-5.6-terra: low minus medium, probe AUC" />
        </ChartFrame>
        <p>
          <Dots per={v6.per_dataset} order={study.study.arm_b_datasets} label="H6 per dataset" />{" "}
          <span className="note" style={{ display: "inline" }}>
            low over medium: {v6.wins} of {v6.n_datasets} — {v6.verdict}.
          </span>
        </p>
      </Deep>

      <Deep summary="Limitations">
        {copy.limits.map((p, i) => <p key={i}>{p}</p>)}
      </Deep>

      {timeline && (
        <Deep summary="The day this was designed, run and decided">
          <ChartFrame caption="Click a tick for the entry it came from.">
            <TimelineStrip timeline={timeline} days={["2026-09-12"]} height={110} />
          </ChartFrame>
        </Deep>
      )}

    </Band>
  );
}
