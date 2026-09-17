import { useState } from "react";
import { scaleLinear } from "d3-scale";
import { useTalk } from "../state";
import { useWidth } from "../hooks";
import { Dots } from "../components/ui";
import { MARGIN, fmt3, short, useHover } from "./primitives";

/* The verdict board: seven rows, each with its rule, its count against the count the rule asks
   for, a dot per dataset, and the verdict. Nothing here decides anything - every field is copied
   from results/evaluation.json. A row links back to the section that argued it. */

export function VerdictBoard() {
  const { study } = useTalk();
  const [open, setOpen] = useState<string | null>(null);
  const order = study.study.datasets;

  return (
    <div>
      <table className="data">
        <thead>
          <tr>
            <th>hypothesis</th>
            <th>what it counted</th>
            <th>count</th>
            <th>needed</th>
            <th>p</th>
            <th style={{ textAlign: "left" }}>per dataset</th>
            <th style={{ textAlign: "left" }}>verdict</th>
          </tr>
        </thead>
        <tbody>
          {study.verdicts.map((v) => (
            <tr key={v.id}>
              <td>
                <a href={`#${v.section}`} onClick={() => setOpen(open === v.id ? null : v.id)}>
                  <strong>{v.id.toUpperCase()}</strong> {v.title}
                </a>
              </td>
              <td style={{ textAlign: "left", fontSize: "0.78rem", color: "var(--ink-secondary)" }}>
                {v.metric}
              </td>
              <td>{v.wins}</td>
              <td>{v.threshold} of {v.n_datasets}</td>
              <td>{v.p.toFixed(4)}</td>
              <td style={{ textAlign: "left" }}>
                <Dots per={v.per_dataset} order={order} label={`${v.id} per dataset`} />
              </td>
              <td style={{ textAlign: "left",
                           color: v.supported ? "var(--good)" : "var(--ink-muted)",
                           fontWeight: 700 }}>
                {v.supported ? "✓ supported" : "✕ not supported"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="note">
        A filled dot is a dataset the comparison won on; a cross is one it did not. Shape as well
        as fill, so the row reads without colour. Counts, p-values and verdicts are
        results/evaluation.json.
      </p>
    </div>
  );
}

/* The published ceiling against the arms, as a compact dot plot: the ceiling is a reference and
   not an arm, so it wears its own colour and its own marker and sits on its own row end. */
export function CeilingDots({ height }: { height?: number }) {
  const { study, armHue } = useTalk();
  const { ref, width } = useWidth<HTMLDivElement>(720);
  const { show, hide, tip } = useHover();
  const rows = study.ceiling.rows;
  const rowH = 24;
  const left = 118;
  const innerW = Math.max(180, width - left - 26);
  const h = height ?? MARGIN.top + MARGIN.bottom + rows.length * rowH;
  const lo = Math.min(...rows.flatMap((r) => [r.pixel, r.concept, r.zero ?? 1])) - 0.03;
  const x = scaleLinear().domain([Math.max(0, lo), 1.0]).range([left, left + innerW]);

  const marks = [
    { key: "zero", label: "best zero-label arm", colour: armHue("B") },
    { key: "concept", label: "arm C at the largest n", colour: armHue("C") },
    { key: "pixel", label: "arm P at the largest n", colour: armHue("P") },
    { key: "ceiling", label: "published, fully supervised", colour: armHue("lit") },
  ] as const;

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={h} role="img"
           aria-label="Each arm against the published fully supervised ceiling, per dataset">
        <g className="grid">
          {x.ticks(5).map((t) => (
            <line key={t} x1={x(t)} x2={x(t)} y1={MARGIN.top - 6}
                  y2={MARGIN.top + rows.length * rowH} />
          ))}
        </g>
        <g className="axis">
          {x.ticks(5).map((t) => (
            <text key={t} x={x(t)} y={MARGIN.top + rows.length * rowH + 18} textAnchor="middle">
              {t.toFixed(2)}
            </text>
          ))}
          <text x={left + innerW} y={MARGIN.top + rows.length * rowH + 33} textAnchor="end"
                style={{ fontWeight: 600 }}>test AUC</text>
        </g>
        {rows.map((r, i) => {
          const y = MARGIN.top + i * rowH + rowH / 2;
          return (
            <g key={r.dataset}>
              <text x={left - 12} y={y + 4} textAnchor="end" className="axis"
                    style={{ fontSize: 11.5, fill: "var(--ink-secondary)" }}>{short(r.dataset)}</text>
              <line x1={x(Math.min(r.pixel, r.concept, r.zero ?? r.pixel))} x2={x(r.ceiling)}
                    y1={y} y2={y} stroke="var(--rule)" strokeWidth={1.5} />
              {marks.map((m) => {
                const v = (r as unknown as Record<string, number | undefined>)[m.key];
                if (v == null) return null;
                return (
                  <g key={m.key}
                     onMouseEnter={(e) => show(e, (
                       <>
                         <div className="k">{r.dataset}</div>
                         {m.label} <strong>{fmt3(v)}</strong>
                         <div className="k">gap to ceiling {fmt3(r.ceiling - v)}</div>
                       </>
                     ))} onMouseLeave={hide}>
                    <circle cx={x(v)} cy={y} r={11} fill="transparent" />
                    {m.key === "ceiling"
                      ? <path d={`M${x(v)} ${y - 5} L${x(v) + 5} ${y} L${x(v)} ${y + 5} L${x(v) - 5} ${y} Z`}
                              fill={m.colour} stroke="var(--surface)" strokeWidth={1.6} />
                      : <circle cx={x(v)} cy={y} r={4} fill={m.colour} stroke="var(--surface)"
                                strokeWidth={1.6} />}
                  </g>
                );
              })}
            </g>
          );
        })}
      </svg>
      {tip}
      <div className="controls" aria-label="Series">
        {marks.map((m) => (
          <span key={m.key} className="chip" style={{ cursor: "default" }}>
            <span className="swatch" style={{ background: m.colour,
                     borderRadius: m.key === "ceiling" ? 0 : 9,
                     transform: m.key === "ceiling" ? "rotate(45deg)" : undefined }} />
            {m.label}
          </span>
        ))}
      </div>
    </div>
  );
}

/* The close's tally: what actually caught each mistake. A bar per catcher, and the DAG's bar is
   the point - it is empty. */
export function CaughtBy() {
  const { study } = useTalk();
  const counts = new Map<string, string[]>();
  for (const c of study.ledger.catches) {
    counts.set(c.caught_by, [...(counts.get(c.caught_by) ?? []), c.what]);
  }
  const rows = [...counts.entries()].sort((a, b) => b[1].length - a[1].length);
  rows.push(["the dependency graph", []]);
  const max = Math.max(...rows.map((r) => r[1].length), 1);

  return (
    <div>
      <table className="data">
        <thead>
          <tr>
            <th>what caught it</th>
            <th style={{ textAlign: "left" }}>count</th>
          </tr>
        </thead>
        <tbody>
          {rows.map(([who, what]) => (
            <tr key={who}>
              <td>{who}</td>
              <td style={{ textAlign: "left" }}>
                <svg width={Math.max(6, (what.length / max) * 160) + 26} height="14"
                     role="img" aria-label={`${what.length}`}>
                  <rect x="0" y="3" width={Math.max(2, (what.length / max) * 160)} height="8"
                        rx="2" fill={what.length ? "var(--nearmiss)" : "var(--rule-strong)"} />
                  <text x={Math.max(2, (what.length / max) * 160) + 6} y="11"
                        style={{ fontSize: 11, fill: "var(--ink-muted)" }}>{what.length}</text>
                </svg>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <ul style={{ fontSize: "0.85rem", color: "var(--ink-secondary)", maxWidth: "42rem" }}>
        {study.ledger.catches.map((c, i) => (
          <li key={i}>
            {c.what} — <em>{c.caught_by}</em>{" "}
            <span className="mono" style={{ color: "var(--ink-muted)" }}>({c.source})</span>
          </li>
        ))}
      </ul>
    </div>
  );
}
