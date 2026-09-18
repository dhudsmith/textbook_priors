import { useState } from "react";
import { useTalk } from "../state";

/* Two structural diagrams: what each arm is made of, and the seven stages. Both are drawn rather
   than described because the shape is the point - in the arm diagram, that three arms share one
   classifier and differ only in the features that reach it. */

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
  const box = (x: number, y: number, w: number, h: number, fill: string) =>
    <rect x={x} y={y} width={w} height={h} rx={6} fill={fill} stroke="var(--rule-strong)" />;

  return (
    <svg className="plot" viewBox="0 0 720 260" width="100%" role="img" style={{ maxWidth: "46rem" }}
         aria-label={
           "The image goes to the vision-language model, which produces a concept vector feeding " +
           "arm B (nearest class fingerprint, no labels) and arm C (logistic regression on n " +
           "labels); the same image goes to a frozen ImageNet ResNet-18, whose features feed arm " +
           "P under the identical classifier; both feature blocks together feed arm C+P. Arm A " +
           "asks the model for the class directly, from a separate prompt."}>
      <g style={{ fontFamily: "var(--sans)", fontSize: 12 }}>
        {box(8, 100, 82, 42, "var(--surface-sunken)")}
        <text x={49} y={118} textAnchor="middle" fill="var(--ink)">image</text>
        <text x={49} y={133} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>224 px</text>

        {box(116, 28, 148, 40, "var(--surface-raised)")}
        <text x={190} y={53} textAnchor="middle" fill="var(--ink)">VLM, zero-shot prompt</text>
        {box(116, 96, 148, 50, "var(--surface-raised)")}
        <text x={190} y={116} textAnchor="middle" fill="var(--ink)">VLM, concept prompt</text>
        <text x={190} y={132} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>one level per feature</text>
        {box(116, 178, 148, 50, "var(--surface-raised)")}
        <text x={190} y={198} textAnchor="middle" fill="var(--ink)">frozen ImageNet</text>
        <text x={190} y={214} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>ResNet-18 features</text>

        {box(296, 96, 104, 50, "var(--surface-sunken)")}
        <text x={348} y={116} textAnchor="middle" fill="var(--ink)">concept</text>
        <text x={348} y={131} textAnchor="middle" fill="var(--ink)">vector</text>
        {box(296, 178, 104, 50, "var(--surface-sunken)")}
        <text x={348} y={203} textAnchor="middle" fill="var(--ink)">pixel features</text>

        {box(446, 130, 122, 64, "var(--surface-sunken)")}
        <text x={507} y={152} textAnchor="middle" fill="var(--ink)">one identical</text>
        <text x={507} y={167} textAnchor="middle" fill="var(--ink)">classifier</text>
        <text x={507} y={183} textAnchor="middle" fill="var(--ink-muted)"
              style={{ fontSize: 10.5 }}>on n labels</text>

        {[
          ["A", 28, "zero labels"], ["B", 62, "zero labels"],
          ["C", 126, "n labels"], ["P", 166, "n labels"], ["C+P", 206, "n labels"],
        ].map(([id, y, sub]) => {
          const wide = (id as string).length > 1;
          const cy = Number(y) + 14;
          return (
            <g key={id as string}>
              {wide
                ? <rect x={624 - 22} y={cy - 13} width={44} height={26} rx={13}
                        fill={badge(id === "C+P" ? "CP" : (id as string))} />
                : <circle cx={624} cy={cy} r={13} fill={badge(id as string)} />}
              <text x={624} y={cy + 5} textAnchor="middle" fill="var(--surface)"
                    style={{ fontWeight: 700 }}>{id as string}</text>
              <text x={wide ? 652 : 646} y={cy + 4} fill="var(--ink-muted)"
                    style={{ fontSize: 10.5 }}>{sub as string}</text>
            </g>
          );
        })}

        <g stroke="var(--rule-strong)" strokeWidth={1.4} fill="none">
          {/* image to the three encoders */}
          <path d="M90 116 C103 116 103 48 116 48" />
          <path d="M90 121 H116" />
          <path d="M90 126 C103 126 103 203 116 203" />
          {/* encoders to their feature blocks; arm A straight to its circle */}
          <path d="M264 121 H296" />
          <path d="M264 203 H296" />
          <path d="M264 48 C540 48 560 42 611 42" />
          {/* the concept vector leaves by two ports: up to arm B, which needs no classifier,
              and down into the shared classifier; the pixel block enters from below. Neither
              path crosses the other or a box. */}
          <path d="M400 110 C440 110 440 76 611 76" stroke={armHue("B")} />
          <path d="M400 134 C423 134 423 150 446 150" />
          <path d="M400 203 C423 203 423 176 446 176" />
          {/* one classifier, three arms: fan out from three ports on its right edge */}
          <path d="M568 150 C590 150 590 140 611 140" />
          <path d="M568 162 C590 162 590 180 611 180" />
          <path d="M568 174 C590 174 590 220 611 220" />
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
           "A human directs an AI coding agent. The agent wrote three things: the concept bank, " +
           "the Snakemake workflow, and the report and this page. The workflow takes two fixed " +
           "inputs - the concept bank and the twelve MedMNIST datasets - runs seven stages, and " +
           "produces the response archive, which is never overwritten, the tables and figures, " +
           "and the " +
           "report. The vision-language model under study is a service the score stage calls; it " +
           "writes none of the code."}>
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
              style={{ fontSize: 10 }}>the object of study</text>
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
