import { useState } from "react";
import { useTalk } from "../state";

/* Two structural diagrams: what each arm is made of, and the seven stages. Both are drawn rather
   than described because the shape is the point. In the arm diagram the three arms that get
   labels have a classifier each - three boxes, not one - and each is entered only by the features
   its arm is defined on. The drawing says there are three of them, so the words do not have to:
   the boxes say "classifier" and nothing claims the arms share one. The model's answers are the
   feature scores throughout, here and in the prose. */

/* A white letter on the arm's own light step measured 4.0:1 and its dark step 2.2 to 3.2 - all
   of them under the floor. The letter wears the surface colour, which is white in light and near
   black in dark, and in light the badge takes a darker step of the same hue so the letter has
   something to sit on. The series colours themselves do not move: this is the badge only. */
function step(colour: string, k: number): string {
  const m = /^#([0-9a-f]{6})$/i.exec(colour);
  if (!m) return colour;
  const n = parseInt(m[1], 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255]
    .map((c) => Math.round(c * k).toString(16).padStart(2, "0"));
  return `#${ch.join("")}`;
}

export function ArmDiagram() {
  const { armHue, dark } = useTalk();
  const badge = (id: string) => (dark ? armHue(id) : step(armHue(id), 0.72));
  const box = (x: number, y: number, w: number, h: number, fill: string, stroke?: string) =>
    <rect x={x} y={y} width={w} height={h} rx={6} fill={fill}
          stroke={stroke ?? "var(--rule-strong)"} />;
  const column = (x: number, label: string) => (
    <text x={x} y={18} textAnchor="middle" fill="var(--ink-muted)"
          style={{ fontSize: 10, letterSpacing: "0.09em" }}>{label}</text>
  );

  /* One classifier per arm that gets labels, drawn at the height of its own badge and outlined
     in its own colour, so a reader can follow a colour from a feature block through a classifier
     to an arm. C+P sits in the middle on purpose: both feature blocks reach it without crossing
     anything. Three boxes is the claim - the arms are fitted the same way and share nothing. */
  const heads: [string, number][] = [["C", 112], ["CP", 172], ["P", 232]];

  return (
    <svg className="plot" viewBox="0 0 720 296" width="100%" role="img" style={{ maxWidth: "46rem" }}
         aria-label={
           "One image, read five ways. Asked to name the class, the vision-language model " +
           "answers arm A. Asked to score the visual features the textbook lists, it picks one " +
           "level for each of them; matching those feature scores to the levels the textbook " +
           "expects for each class gives arm B. Neither arm uses a labelled image. An ImageNet " +
           "ResNet-18, pretrained and not retrained here, turns the same image into image " +
           "features. Three more arms each fit a classifier of their own on n labelled images: " +
           "arm C on the feature scores, arm P on the image features, and arm C+P on both."}>
      <g style={{ fontFamily: "var(--sans)", fontSize: 12 }}>
        {column(49, "IMAGE")}
        {column(190, "WHAT READS IT")}
        {column(348, "FEATURES")}
        {column(618, "ARM")}

        {box(8, 120, 82, 42, "var(--surface-sunken)")}
        <text x={49} y={138} textAnchor="middle" fill="var(--ink)">image</text>
        <text x={49} y={153} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>224 px</text>

        {box(116, 30, 148, 40, "var(--surface-raised)")}
        <text x={190} y={55} textAnchor="middle" fill="var(--ink)">VLM: name the class</text>
        {box(116, 96, 148, 50, "var(--surface-raised)")}
        <text x={190} y={116} textAnchor="middle" fill="var(--ink)">VLM: score the features</text>
        <text x={190} y={132} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>one level per feature</text>
        {box(116, 226, 148, 50, "var(--surface-raised)")}
        <text x={190} y={246} textAnchor="middle" fill="var(--ink)">ImageNet ResNet-18</text>
        <text x={190} y={262} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>pretrained, not retrained</text>

        {box(296, 96, 104, 50, "var(--surface-sunken)")}
        <text x={348} y={126} textAnchor="middle" fill="var(--ink)">feature scores</text>
        {box(296, 226, 104, 50, "var(--surface-sunken)")}
        <text x={348} y={255} textAnchor="middle" fill="var(--ink)">image features</text>

        {heads.map(([id, y]) => (
          <g key={`head-${id}`}>
            {box(436, y, 110, 40, "var(--surface-sunken)", armHue(id))}
            <text x={491} y={y + 24} textAnchor="middle" fill="var(--ink)">classifier</text>
          </g>
        ))}

        {[
          ["A", 50, "zero labels"], ["B", 88, "zero labels"],
          ["C", 134, "n labels"], ["C+P", 194, "n labels"], ["P", 254, "n labels"],
        ].map(([id, cy, sub]) => {
          const wide = (id as string).length > 1;
          const y = Number(cy);
          const key = id === "C+P" ? "CP" : (id as string);
          return (
            <g key={key}>
              {wide
                ? <rect x={618 - 22} y={y - 13} width={44} height={26} rx={13} fill={badge(key)} />
                : <circle cx={618} cy={y} r={13} fill={badge(key)} />}
              <text x={618} y={y + 5} textAnchor="middle" fill="var(--surface)"
                    style={{ fontWeight: 700 }}>{id as string}</text>
              <text x={wide ? 646 : 637} y={y + 4} fill="var(--ink-muted)"
                    style={{ fontSize: 10.5 }}>{sub as string}</text>
            </g>
          );
        })}

        <g strokeWidth={1.4} fill="none">
          {/* the image into the three things that read it */}
          <g stroke="var(--rule-strong)">
            <path d="M90 132 C104 132 102 50 116 50" />
            <path d="M90 141 C104 141 104 121 116 121" />
            <path d="M90 150 C104 150 102 251 116 251" />
            <path d="M264 121 H296" />
            <path d="M264 251 H296" />
          </g>

          {/* Every line that reaches an arm wears that arm's colour, because the provenance is
              the point: A never becomes features at all, B reads the feature scores with no
              classifier, and each classifier is entered only by the block or blocks its arm is
              defined on. */}
          <path d="M264 50 C420 50 470 50 605 50" stroke={armHue("A")} />
          <path d="M400 106 C414 106 414 88 605 88" stroke={armHue("B")} />

          <path d="M400 126 C418 126 418 134 436 134" stroke={armHue("C")} />
          <path d="M546 134 H605" stroke={armHue("C")} />

          <path d="M400 140 C414 140 414 154 414 176 C414 185 418 188 436 188"
                stroke={armHue("CP")} />
          <path d="M400 232 C422 232 422 218 422 210 C422 203 424 200 436 200"
                stroke={armHue("CP")} />
          <path d="M546 194 H605" stroke={armHue("CP")} />

          <path d="M400 246 C418 246 418 254 436 254" stroke={armHue("P")} />
          <path d="M546 254 H605" stroke={armHue("P")} />
        </g>
      </g>
    </svg>
  );
}

/* The opening diagram: what the agent built, and where the two different machines called AI sit.
   The agent authored the bank, the workflow and the page - dashed, in the agent's own violet. The
   model under study is not an author at all: it is a service one stage calls, on the data path
   like any other tool, and it is drawn that way on purpose. */
export function WorkflowDiagram() {
  const { study } = useTalk();
  const led = study.ledger;
  const box = (x: number, y: number, w: number, h: number, fill: string, stroke?: string) =>
    <rect x={x} y={y} width={w} height={h} rx={6} fill={fill}
          stroke={stroke ?? "var(--rule-strong)"} />;
  const head = (x: number, label: string) => (
    <text x={x} y={76} textAnchor="middle" fill="var(--ink-muted)"
          style={{ fontSize: 10, letterSpacing: "0.09em" }}>
      {label}
    </text>
  );

  return (
    <svg className="plot" viewBox="0 0 760 400" width="100%" role="img" style={{ maxWidth: "52rem" }}
         aria-label={
           "A person directs an AI coding agent, and the agent wrote three things: the concept " +
           "bank, the Snakemake workflow, and the report and this page. The workflow takes two " +
           "fixed inputs, the concept bank and the twelve MedMNIST datasets, runs seven stages " +
           "and writes three outputs: the archive of replies, which is never overwritten, the " +
           "tables and figures, and the report. The vision-language model this study tests is a " +
           "service the score stage calls. It wrote none of the code."}>
      <defs>
        <marker id="wf-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
                markerHeight="6" orient="auto">
          <path d="M0 0 L10 5 L0 10 z" fill="var(--rule-strong)" />
        </marker>
        <marker id="wf-arrow-back" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="6"
                markerHeight="6" orient="auto">
          <path d="M10 0 L0 5 L10 10 z" fill="var(--rule-strong)" />
        </marker>
        <marker id="wf-arrow-agent" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6"
                markerHeight="6" orient="auto">
          <path d="M0 0 L10 5 L0 10 z" fill="var(--agent)" />
        </marker>
      </defs>

      <g style={{ fontFamily: "var(--sans)", fontSize: 12 }}>
        {/* who authored it */}
        {box(8, 6, 160, 40, "var(--surface-sunken)")}
        <text x={88} y={24} textAnchor="middle" fill="var(--ink)">human</text>
        <text x={88} y={38} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10 }}>asks · reads · decides · catches</text>

        {box(246, 6, 196, 40, "var(--agent-wash)", "var(--agent)")}
        <text x={344} y={24} textAnchor="middle" fill="var(--ink)">AI coding agent</text>
        <text x={344} y={38} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10 }}>writes · runs · records</text>

        <text x={207} y={20} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10 }}>directs</text>

        {head(88, "FIXED INPUTS")}
        {head(360, "ONE WORKFLOW")}
        {head(600, "GENERATED OUTPUTS")}

        {/* fixed inputs */}
        {box(8, 92, 160, 52, "var(--surface-raised)")}
        <text x={88} y={114} textAnchor="middle" fill="var(--ink)">concept bank</text>
        <text x={88} y={130} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>cited visual features</text>

        {box(8, 168, 160, 52, "var(--surface-raised)")}
        <text x={88} y={190} textAnchor="middle" fill="var(--ink)">
          {led.datasets} MedMNIST datasets
        </text>
        <text x={88} y={206} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>images and labels</text>

        {/* the workflow, and the stages it is made of */}
        {box(246, 92, 196, 212, "var(--surface-sunken)")}
        <text x={344} y={116} textAnchor="middle" fill="var(--ink)"
              style={{ fontWeight: 700 }}>Snakemake</text>
        <text x={344} y={131} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10 }}>one file, every number a rule</text>
        {study.stages.map((s, i) => (
          <g key={s.id}>
            <text x={266} y={155 + i * 21} fill="var(--ink-secondary)"
                  style={{ fontSize: 11 }}>{s.name}</text>
            <text x={422} y={155 + i * 21} textAnchor="end" fill="var(--ink-muted)"
                  style={{ fontFamily: "var(--mono)", fontSize: 10 }}>{s.jobs}</text>
          </g>
        ))}

        {/* the model under study: called, not consulted about the code */}
        {box(246, 344, 196, 44, "var(--surface-raised)", "var(--ink-muted)")}
        <text x={344} y={364} textAnchor="middle" fill="var(--ink)">VLM service</text>
        <text x={344} y={379} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10 }}>the model this study tests</text>
        <text x={452} y={329} fill="var(--ink-muted)"
              style={{ fontSize: 10 }}>the score stage calls it</text>

        {/* generated outputs */}
        {box(500, 92, 200, 56, "var(--surface-raised)")}
        <text x={600} y={113} textAnchor="middle" fill="var(--ink)">response archive</text>
        <text x={600} y={128} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>{led.calls.toLocaleString("en-US")} raw replies</text>
        <text x={600} y={141} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10 }}>never overwritten</text>

        {box(500, 164, 200, 48, "var(--surface-raised)")}
        <text x={600} y={186} textAnchor="middle" fill="var(--ink)">results</text>
        <text x={600} y={201} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>tables, figures, intervals</text>

        {box(500, 228, 200, 48, "var(--surface-raised)")}
        <text x={600} y={250} textAnchor="middle" fill="var(--ink)">report, and this page</text>
        <text x={600} y={265} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>generated, never typed</text>

        {/* data, and the one line that is neither data nor authorship */}
        <g stroke="var(--rule-strong)" strokeWidth={1.4} fill="none" markerEnd="url(#wf-arrow)">
          <path d="M168 26 H240" />
          <path d="M168 118 H240" />
          <path d="M168 194 H240" />
          <path d="M442 120 H494" />
          <path d="M442 188 H494" />
          <path d="M442 252 H494" />
        </g>
        <path d="M344 310 V338" stroke="var(--rule-strong)" strokeWidth={1.4} fill="none"
              markerEnd="url(#wf-arrow)" markerStart="url(#wf-arrow-back)" />

        {/* authorship. Both arrows off the agent's underside land clear of the column headers:
            the bank is entered right of its own, the workflow left of its own. */}
        <g stroke="var(--agent)" strokeWidth={1.4} fill="none" strokeDasharray="5 4"
           markerEnd="url(#wf-arrow-agent)">
          <path d="M268 46 C216 46 176 62 142 86" />
          <path d="M280 46 C274 60 274 72 272 86" />
          <path d="M442 26 H722 Q730 26 730 34 V244 Q730 252 722 252 H706" />
        </g>

        {/* legend */}
        <g style={{ fontSize: 10 }}>
          <path d="M8 336 H44" stroke="var(--rule-strong)" strokeWidth={1.4}
                markerEnd="url(#wf-arrow)" />
          <text x={52} y={340} fill="var(--ink-muted)">data</text>
          <path d="M8 358 H44" stroke="var(--agent)" strokeWidth={1.4} strokeDasharray="5 4"
                markerEnd="url(#wf-arrow-agent)" />
          <text x={52} y={362} fill="var(--ink-muted)">written by the agent</text>
        </g>
      </g>
    </svg>
  );
}

export function StageStrip({ blurbs }: { blurbs: Record<string, string> }) {
  const { study } = useTalk();
  const [open, setOpen] = useState<string | null>(null);
  return (
    <div>
      <div className="controls" role="group" aria-label="Stages">
        {study.stages.map((s, i) => (
          <span key={s.id} style={{ display: "inline-flex", alignItems: "center", gap: "0.4rem" }}>
            <button className="chip" aria-pressed={open === s.id}
                    onClick={() => setOpen(open === s.id ? null : s.id)}>
              {s.name}
              <span className="mono" style={{ color: "var(--ink-muted)" }}>{s.jobs}</span>
            </button>
            {i < study.stages.length - 1 && (
              <span aria-hidden="true" style={{ color: "var(--ink-muted)" }}>→</span>
            )}
          </span>
        ))}
      </div>
      {open && (
        <div className="card" style={{ maxWidth: "40rem", cursor: "default" }}>
          <div className="hid">
            {study.stages.find((s) => s.id === open)!.jobs}{" "}
            {study.stages.find((s) => s.id === open)!.unit}
          </div>
          <div className="claim">{study.stages.find((s) => s.id === open)!.name}</div>
          <p style={{ fontSize: "0.86rem", marginBottom: 0 }}>{blurbs[open]}</p>
        </div>
      )}
    </div>
  );
}
