import { useState } from "react";
import { useTalk } from "../state";
import { Band, Bullets, ChartFrame, Deep, Dots, Header } from "../components/ui";
import { Ladder } from "../charts/Ladder";
import { ThinkingScatter } from "../charts/ThinkingScatter";
import { thinking as copy } from "../content";
import { widestSpread } from "../charts/primitives";

/* One figure on the spine - what thinking did, against how well the model read without it - and
   the reader chain and the limits in panels under it. The effort prediction moved to Extra on
   2026-09-19: it is a footnote about one dataset, and the room does not need it to read H4. The strip of the day
   this was designed and decided was dropped on 2026-09-19: the section that is about how the work
   unfolded carries that material, and here it was a chart nobody had a question for. */

export function Thinking() {
  const { study } = useTalk();
  const h4 = study.across.h4;
  const v4 = study.verdicts.find((x) => x.id === "h4")!;
  const [step, setStep] = useState<"h4a" | "h4b">("h4a");

  // The reader chain, in the order the study built it: the four thinking-off models, then the
  // thinking primary, then the gateway readers. Both lists come from the config in the snapshot.
  const chain = [...Object.keys(study.study.models), ...Object.keys(study.study.readers)]
    .filter((r) => h4.readers.includes(r));

  // The frontier step H4b measured: the gateway reader the primary was compared against, at the
  // effort they share. Read from the reader table rather than named in the copy.
  const frontier = Object.entries(study.study.readers)
    .find(([id, r]) => r.api === "gateway" && id.endsWith("-medium"))?.[1].model
    ?? Object.values(study.study.readers).find((r) => r.api === "gateway")!.model;


  return (
    <Band id="thinking">
      <Header id="thinking">{copy.header}</Header>
      <p className="lede">
        {copy.ledeShape
          .replace("{primary}", study.study.primary)
          .replace("{frontier}", frontier)}
      </p>

      {/* One chart, either step. The frontier half used to be a claim in a sentence with no
          figure behind it. */}
      <div className="controls" role="group" aria-label="Which step">
        <span className="group-label">what changed</span>
        <button className="chip" aria-pressed={step === "h4a"} onClick={() => setStep("h4a")}>
          {copy.toggle.thinking}
        </button>
        <button className="chip" aria-pressed={step === "h4b"} onClick={() => setStep("h4b")}>
          {copy.toggle.frontier}
        </button>
      </div>

      <ChartFrame
        caption={(step === "h4a" ? copy.captionShapes.thinking : copy.captionShapes.frontier)
          .replace(/\{primary\}/g, study.study.primary)
          .replace(/\{frontier\}/g, frontier)}>
        <ThinkingScatter step={step} />
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
                        "Only the datasets with the widest spread between their highest and " +
                        "lowest point are named and coloured, along with dermamnist, which the " +
                        "effort prediction in Extra is about; the rest stay grey, and hovering " +
                        "any line isolates it."} />
        </ChartFrame>
      </Deep>

      <Deep summary="Limitations">
        {copy.limits.map((p, i) => <p key={i}>{p}</p>)}
      </Deep>

    </Band>
  );
}
