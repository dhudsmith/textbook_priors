import { useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { useTalk } from "../state";
import type { Study } from "../types";

/* The workflow, twice over: as a table of its rules, and as the picture of how they depend on
   each other. Both are drawn from the `workflow` block of the snapshot, which the export reads
   out of the Snakefile and out of three of Snakemake's own dry runs - so a rule renamed, re-wired
   or given a different time limit moves this page, and nothing here is a second copy kept by
   hand. The rule source shown behind a click is sliced out of the Snakefile, not transcribed.

   This is the one place on the page where code is the point: the room is being shown what a
   workflow rule looks like. Everywhere else the prose stays in the words the page has taught. */

export interface RuleFile { path: string; n: number }

export interface WorkflowRule {
  name: string;
  /** Position in the Snakefile: the order a person reading the workflow meets its rules. */
  index: number;
  stage: string | null;
  source: string;
  local: boolean;
  protected: boolean;
  env: string | null;
  modules: string[];
  throttle: string | null;
  layer: number;
  order: number;
  jobs: number;
  needs: string[];
  feeds: string[];
  reads: RuleFile[];
  writes: RuleFile[];
  cpus: number | null;
  mem_mb: number | null;
  runtime: number | null;
  cap: number | null;
}

export interface Workflow {
  rules: WorkflowRule[];
  edges: { from: string; to: string }[];
  jobs: number;
  snakemake: string;
  how: string;
}

/** The snapshot carries the workflow; the shared `Study` type does not name it. */
export function useWorkflow(): Workflow {
  const { study } = useTalk();
  return (study as Study & { workflow: Workflow }).workflow;
}

const mono: CSSProperties = { fontFamily: "var(--mono)", fontSize: "0.76rem" };
/* The page's small-caps field label. It is a style rather than a class because the
   stylesheet only carries it inside a control group. */
const label: CSSProperties = {
  fontSize: "0.72rem", color: "var(--ink-muted)", fontFamily: "var(--mono)",
  textTransform: "uppercase", letterSpacing: "0.08em",
};

function plural(n: number, one: string, many = `${one}s`) {
  return `${n.toLocaleString("en-US")} ${n === 1 ? one : many}`;
}

/* ---- the table ----------------------------------------------------------------------------- */

/** A path that may wrap, breaking at its own separators rather than mid-word. */
function Path({ path }: { path: string }) {
  const parts = path.split(/(?<=\/|__)/);
  return (
    <>{parts.map((part, i) => (
      <span key={i}>{part}{i < parts.length - 1 && <wbr />}</span>
    ))}</>
  );
}

function Files({ files }: { files: RuleFile[] }) {
  if (!files.length) return <span style={{ color: "var(--ink-muted)" }}>nothing</span>;
  return (
    <ul style={{ margin: 0, padding: 0, listStyle: "none" }}>
      {files.map((f) => (
        <li key={f.path} style={{ ...mono, overflowWrap: "break-word", lineHeight: 1.55 }}>
          <Path path={f.path} />
          {f.n > 1 && (
            <span style={{ color: "var(--ink-muted)", fontFamily: "var(--sans)",
                           fontSize: "0.72rem" }}>{" "}× {f.n}</span>
          )}
        </li>
      ))}
    </ul>
  );
}

function Field({ name, children }: { name: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ ...label, marginBottom: "0.25rem" }}>{name}</div>
      <div style={{ fontSize: "0.82rem", color: "var(--ink-secondary)" }}>{children}</div>
    </div>
  );
}

/** What the machine was asked for, said the way a person would say it. */
function asks(rule: WorkflowRule): string {
  if (rule.local) return "runs on the spot, in seconds — nothing is submitted";
  const bits = [];
  if (rule.cpus) bits.push(plural(rule.cpus, "processor"));
  if (rule.mem_mb) bits.push(`${(rule.mem_mb / 1000).toFixed(rule.mem_mb % 1000 ? 1 : 0)} GB`);
  if (rule.runtime) {
    bits.push(rule.runtime >= 60 ? `${rule.runtime / 60} hours at most`
                                 : `${rule.runtime} minutes at most`);
  }
  return bits.length ? bits.join(", ") : "the cluster's defaults";
}

function Row({ rule, blurb, detail, open, onToggle }: {
  rule: WorkflowRule; blurb: string; detail: string;
  open: boolean; onToggle: () => void;
}) {
  const [code, setCode] = useState(false);
  const id = `rule-${rule.name}`;
  return (
    <div id={id} style={{ borderBottom: "1px solid var(--rule)" }}>
      <button
        onClick={onToggle} aria-expanded={open} aria-controls={`${id}-body`}
        style={{
          display: "grid", gap: "0.2rem 0.9rem", width: "100%", textAlign: "left",
          gridTemplateColumns: "minmax(0, 12rem) minmax(0, 1fr) auto",
          alignItems: "baseline", font: "inherit", color: "inherit", cursor: "pointer",
          background: open ? "var(--surface-sunken)" : "none", border: 0,
          padding: "0.4rem 0.55rem", borderRadius: 5,
        }}>
        <span style={{ ...mono, color: "var(--ink)", fontWeight: 600 }}>
          <span aria-hidden="true" style={{ color: "var(--ink-muted)", marginRight: "0.35rem",
                                            display: "inline-block", width: "0.6rem" }}>
            {open ? "⌄" : "›"}
          </span>
          {rule.name}
        </span>
        <span style={{ fontSize: "0.86rem", color: "var(--ink-secondary)" }}>{blurb}</span>
        <span style={{ ...mono, color: "var(--ink-muted)", whiteSpace: "nowrap" }}>
          {rule.jobs.toLocaleString("en-US")}
        </span>
      </button>

      {open && (
        <div id={`${id}-body`}
             style={{ padding: "0.2rem 0.55rem 1rem 1.9rem", background: "var(--surface-sunken)",
                      borderRadius: "0 0 5px 5px" }}>
          <p style={{ fontSize: "0.86rem", maxWidth: "40rem", marginTop: 0 }}>{detail}</p>
          <div style={{ display: "grid", gap: "0.9rem 1.6rem",
                        gridTemplateColumns: "repeat(auto-fit, minmax(19rem, 1fr))",
                        maxWidth: "58rem" }}>
            <Field name="waits for">
              {rule.needs.length
                ? rule.needs.map((n) => <span key={n} style={{ ...mono, display: "block" }}>{n}</span>)
                : "nothing — it can start at once"}
            </Field>
            <Field name="reads"><Files files={rule.reads} /></Field>
            <Field name="writes">
              <Files files={rule.writes} />
              {rule.protected && (
                <p style={{ margin: "0.35rem 0 0", fontSize: "0.78rem" }}>
                  Write-protected: once it exists it cannot be overwritten, so buying those calls
                  again has to be a decision.
                </p>
              )}
            </Field>
            <Field name="how many">
              {plural(rule.jobs, "job")} in a full pass
              {rule.cap != null && (
                <span>, at most {rule.cap} of them talking to the model service at once</span>
              )}
            </Field>
            <Field name="asks for">{asks(rule)}</Field>
            <Field name="rebuilt when these change">
              {rule.modules.length
                ? rule.modules.map((m) => <span key={m} style={{ ...mono, display: "block" }}>{m}</span>)
                : "no code of ours — it runs a tool"}
              {rule.env && (
                <span style={{ ...mono, display: "block", color: "var(--ink-muted)" }}>
                  {rule.env}
                </span>
              )}
            </Field>
          </div>

          <button className="plain" style={{ marginTop: "0.9rem" }}
                  aria-expanded={code} onClick={() => setCode((v) => !v)}>
            {code ? "hide the rule" : "show the rule"}
          </button>
          {/* Code scrolls rather than wraps: a wrapped `rule` block loses the indentation that
              is half of what it is being shown for. */}
          {code && (
            <pre className="file" style={{ marginTop: "0.6rem", maxWidth: "58rem",
                                           whiteSpace: "pre", wordBreak: "normal" }}>
              {rule.source}
            </pre>
          )}
        </div>
      )}
    </div>
  );
}

export function RuleTable({ blurbs, details, open, setOpen }: {
  blurbs: Record<string, string>;
  details: Record<string, string>;
  open: string | null;
  setOpen: (name: string | null) => void;
}) {
  const { study } = useTalk();
  const workflow = useWorkflow();
  const stageName = useMemo(
    () => new Map(study.stages.map((s) => [s.id, s.name])), [study.stages]);

  /* The Snakefile's own order, grouped by its own stage banners: the table reads the way the
     file reads. The one rule that belongs to no stage is `all`, and it goes last because it is
     the thing you ask for rather than a step - which is the point the last row makes. */
  const groups: { key: string; label: string; rules: WorkflowRule[] }[] = [];
  for (const rule of [...workflow.rules].sort((a, b) => a.index - b.index)) {
    const key = rule.stage ?? "target";
    const found = groups.find((g) => g.key === key);
    if (found) found.rules.push(rule);
    else {
      groups.push({ key, rules: [rule],
                    label: rule.stage ? stageName.get(rule.stage) ?? rule.stage
                                      : "What you ask for" });
    }
  }
  groups.sort((a, b) => Number(a.key === "target") - Number(b.key === "target"));

  return (
    <div className="ruletable" style={{ maxWidth: "var(--figure)", margin: "1.4rem 0 0.4rem" }}>
      <div style={{ display: "grid", gap: "0.2rem 0.9rem", padding: "0 0.55rem 0.3rem",
                    gridTemplateColumns: "minmax(0, 12rem) minmax(0, 1fr) auto",
                    borderBottom: "1px solid var(--rule-strong)" }}>
        <span style={label}>rule</span>
        <span style={label}>what it does</span>
        <span style={label}>jobs</span>
      </div>
      {groups.map((g) => (
        <div key={g.key}>
          <div style={{ padding: "0.55rem 0.55rem 0.15rem", fontSize: "0.72rem", fontWeight: 700,
                        letterSpacing: "0.09em", textTransform: "uppercase",
                        color: "var(--ink-muted)" }}>
            {g.label}
          </div>
          {g.rules.map((rule) => (
            <Row key={rule.name} rule={rule}
                 blurb={blurbs[rule.name] ?? ""} detail={details[rule.name] ?? ""}
                 open={open === rule.name}
                 onToggle={() => setOpen(open === rule.name ? null : rule.name)} />
          ))}
        </div>
      ))}
    </div>
  );
}

/* ---- the graph ------------------------------------------------------------------------------ */

/* Drawn from the same rules and edges the table is built from. Layers come out of the export
   (the longest path from a rule with nothing to wait for), so every scoring rule sits on one
   row and the picture is the funnel the workflow actually is.

   Two kinds of line. A dependency between neighbouring rows is drawn straight down. One that
   skips rows is bundled: every such line out of a rule leaves on the same side and runs down its
   own vertical lane, so three rules that each feed four others make three lanes instead of
   twelve crossings. The tests are the exception that would ruin the drawing - eleven of the
   nineteen rules wait on them, and that is a gate rather than a flow of data - so their lines
   are drawn lighter, and the legend says so. Nothing is left out. */

const W = 124, H = 32, GAP_X = 10, GAP_Y = 30, PAD_L = 62, PAD_R = 78, PAD_T = 26, PAD_B = 16;
const LANE = 13;

interface Placed extends WorkflowRule { x: number; y: number }

export function RuleGraph({ open, setOpen }: {
  open: string | null; setOpen: (name: string | null) => void;
}) {
  const workflow = useWorkflow();
  const [hover, setHover] = useState<string | null>(null);
  const focus = hover ?? open;

  const { nodes, at, width, height } = useMemo(() => {
    const rows = new Map<number, WorkflowRule[]>();
    for (const r of workflow.rules) {
      rows.set(r.layer, [...(rows.get(r.layer) ?? []), r]);
    }
    for (const row of rows.values()) row.sort((a, b) => a.order - b.order);
    const widest = Math.max(...[...rows.values()].map((r) => r.length * (W + GAP_X) - GAP_X));
    const placed: Placed[] = [];
    for (const [layer, row] of rows) {
      const span = row.length * (W + GAP_X) - GAP_X;
      row.forEach((r, i) => placed.push({
        ...r,
        x: PAD_L + (widest - span) / 2 + i * (W + GAP_X),
        y: PAD_T + layer * (H + GAP_Y),
      }));
    }
    const byName = new Map(placed.map((p) => [p.name, p]));
    return {
      nodes: placed, at: byName,
      width: PAD_L + widest + PAD_R,
      height: PAD_T + (Math.max(...rows.keys()) + 1) * (H + GAP_Y) - GAP_Y + PAD_B,
    };
  }, [workflow.rules]);

  /* One lane per rule that has a dependency skipping a row: left of the drawing if the rule sits
     left of centre, right of it otherwise, so the lanes spread instead of stacking. */
  const lanes = useMemo(() => {
    const skipping = workflow.rules
      .filter((r) => workflow.edges.some(
        (e) => e.from === r.name && (at.get(e.to)!.layer - r.layer) > 1))
      .sort((a, b) => a.layer - b.layer || a.order - b.order);
    const mid = width / 2;
    const side: Record<string, { x: number; dir: -1 | 1 }> = {};
    let left = 0, right = 0;
    for (const r of skipping) {
      const node = at.get(r.name)!;
      if (node.x + W / 2 < mid) side[r.name] = { x: PAD_L - 14 - left++ * LANE, dir: -1 };
      else side[r.name] = { x: width - PAD_R + 16 + right++ * LANE, dir: 1 };
    }
    return side;
  }, [workflow.rules, workflow.edges, at, width]);

  const paths = workflow.edges.map((e) => {
    const a = at.get(e.from)!, b = at.get(e.to)!;
    const gate = e.from === "smoke";
    const key = `${e.from}->${e.to}`;
    if (b.layer - a.layer === 1) {
      const y0 = a.y + H, y1 = b.y;
      return { key, e, gate,
               d: `M${a.x + W / 2} ${y0} C${a.x + W / 2} ${y0 + 14} ${b.x + W / 2} ${y1 - 16} ` +
                  `${b.x + W / 2} ${y1 - 4}` };
    }
    const lane = lanes[e.from];
    const yMid = b.y + H / 2;
    const enter = lane.dir < 0 ? b.x - 5 : b.x + W + 5;
    const leave = lane.dir < 0 ? a.x : a.x + W;
    const r = 7;
    const ySplit = a.y + H / 2;
    return { key, e, gate,
             d: `M${leave} ${ySplit} H${lane.x + r * lane.dir * -1} ` +
                `Q${lane.x} ${ySplit} ${lane.x} ${ySplit + r} ` +
                `V${yMid - r} Q${lane.x} ${yMid} ${lane.x + r * lane.dir * -1} ${yMid} ` +
                `H${enter}` };
  });

  const lit = (name: string) =>
    !focus || name === focus ||
    workflow.edges.some((e) => (e.from === focus && e.to === name) ||
                               (e.to === focus && e.from === name));

  return (
    <svg className="plot" viewBox={`0 0 ${width} ${height}`} width="100%" role="img"
         style={{ maxWidth: `${width / 16}rem`, minWidth: "38rem" }}
         aria-label={
           `The ${workflow.rules.length} rules of the workflow and what each waits for. The ` +
           "tests come first and everything waits on them. The images are drawn and the two " +
           "questions written, then six scoring rules ask the models and the pixel features are " +
           "computed alongside; the answers are gathered per dataset, every arm is fitted, each " +
           "dataset is evaluated, the twelve are compared, and the tables and figures become the " +
           "report. Asking for the report is asking for all of it."}>
      <defs>
        <marker id="rg-arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="5"
                markerHeight="5" orient="auto">
          <path d="M0 0 L10 5 L0 10 z" fill="var(--rule-strong)" />
        </marker>
      </defs>

      <g fill="none" strokeWidth={1.4} markerEnd="url(#rg-arrow)">
        {paths.map((p) => {
          const on = focus && (p.e.from === focus || p.e.to === focus);
          return (
            <path key={p.key} d={p.d}
                  stroke={on ? "var(--ink)" : "var(--rule-strong)"}
                  opacity={p.gate ? (on ? 0.8 : 0.3) : (focus && !on ? 0.3 : 1)}
                  strokeDasharray={p.gate ? "3 3" : undefined} />
          );
        })}
      </g>

      <g style={{ fontFamily: "var(--mono)", fontSize: 9 }}>
        {nodes.map((n) => {
          const on = n.name === focus;
          return (
            <g key={n.name} style={{ cursor: "pointer" }}
               onMouseEnter={() => setHover(n.name)} onMouseLeave={() => setHover(null)}
               onClick={() => setOpen(open === n.name ? null : n.name)}>
              <title>{`${n.name}: ${n.jobs.toLocaleString("en-US")} ` +
                      `job${n.jobs === 1 ? "" : "s"}`}</title>
              <rect x={n.x} y={n.y} width={W} height={H} rx={5}
                    fill={on ? "var(--surface-sunken)" : "var(--surface-raised)"}
                    stroke={on ? "var(--ink)" : "var(--rule-strong)"}
                    strokeWidth={on ? 1.8 : 1}
                    strokeDasharray={n.stage ? undefined : "4 3"}
                    opacity={lit(n.name) ? 1 : 0.45} />
              <text x={n.x + W / 2} y={n.y + 14} textAnchor="middle"
                    fill={lit(n.name) ? "var(--ink)" : "var(--ink-muted)"}>{n.name}</text>
              <text x={n.x + W / 2} y={n.y + 25} textAnchor="middle" fill="var(--ink-muted)"
                    style={{ fontFamily: "var(--sans)", fontSize: 8.5 }}
                    opacity={lit(n.name) ? 1 : 0.45}>
                {n.jobs.toLocaleString("en-US")} job{n.jobs === 1 ? "" : "s"}
              </text>
            </g>
          );
        })}
      </g>

      <g style={{ fontFamily: "var(--sans)", fontSize: 9 }}>
        <path d={`M8 ${height - 8} h22`} stroke="var(--rule-strong)" strokeWidth={1.3}
              strokeDasharray="3 3" fill="none" />
        <text x={34} y={height - 5} fill="var(--ink-muted)">waits on the tests</text>
      </g>
    </svg>
  );
}
