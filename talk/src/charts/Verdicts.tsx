import { useState } from "react";
import { scaleLinear } from "d3-scale";
import { useTalk } from "../state";
import { useWidth } from "../hooks";
import { Dots } from "../components/ui";
import { MARGIN, Marker, fmt3, short, useHover } from "./primitives";

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
        as fill, so the row reads without colour. Counts, p-values and verdicts come from
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

  /* Four marks on one row, and three of them used to be the same circle in three hues - two of
     which a deutan reader cannot separate. Each wears its own shape, as the arm diagram and the
     dataset markers already do. */
  const marks = [
    { key: "zero", label: "best zero-label arm", colour: armHue("B"), shape: "circle" },
    { key: "concept", label: "arm C at the largest n", colour: armHue("C"), shape: "square" },
    { key: "pixel", label: "arm P at the largest n", colour: armHue("P"), shape: "triangle" },
    { key: "ceiling", label: "published, fully supervised", colour: armHue("lit"),
      shape: "diamond" },
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
                    y1={y} y2={y} stroke="var(--rule-strong)" strokeWidth={1.5} />
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
                    <Marker kind={m.shape} x={x(v)} y={y} r={5} fill={m.colour}
                            stroke="var(--surface)" />
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
          <span key={m.key} className="chip legend" style={{ cursor: "default" }}>
            <svg width="14" height="14" aria-hidden="true">
              <Marker kind={m.shape} x={7} y={7} r={5} fill={m.colour} />
            </svg>
            {m.label}
          </span>
        ))}
      </div>
    </div>
  );
}
