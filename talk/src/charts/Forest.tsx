import { scaleLinear } from "d3-scale";
import { useWidth } from "../hooks";
import { MARGIN, ZeroLine, fmt3, plotBox, rowLeft, short, signed, useHover } from "./primitives";

/* A paired difference and its 95% interval, one row per dataset. Used wherever the claim is "this
   arm minus that arm": rows whose interval clears zero are drawn at full strength and the rest at
   less, which is the report's own convention for the same plots. */

export interface Row { dataset: string; median: number; lo: number; hi: number }

export function Forest({ rows, colour, label, unit = "AUC", height, annotate }: {
  rows: Row[]; colour: string; label: string; unit?: string; height?: number;
  /** The two directions of the axis, named, so a plot whose left half is empty says why. */
  annotate?: [string, string];
}) {
  const { ref, width: measured } = useWidth<HTMLDivElement>(700);
  const { width } = plotBox(measured);
  const { show, hide, tip } = useHover();

  const rowH = 26;
  const extra = annotate ? 18 : 0;
  const h = (height ?? MARGIN.top + MARGIN.bottom + rows.length * rowH) + extra;
  const left = rowLeft(measured);
  const innerW = Math.max(180, width - left - 26);
  const span = Math.max(...rows.flatMap((r) => [Math.abs(r.lo), Math.abs(r.hi)])) * 1.1;
  const x = scaleLinear().domain([-span, span]).range([left, left + innerW]);

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={h} role="img" aria-label={label}>
        <ZeroLine x={x(0)} y1={MARGIN.top - 6} y2={MARGIN.top + rows.length * rowH} />
        <g className="axis">
          {x.ticks(5).map((t) => (
            <text key={t} x={x(t)} y={MARGIN.top + rows.length * rowH + 18} textAnchor="middle">
              {signed(t, 2)}
            </text>
          ))}
          <text x={left + innerW / 2} y={MARGIN.top + rows.length * rowH + 33 + extra}
                textAnchor="middle" style={{ fontWeight: 600 }}>
            {label.toLowerCase().includes(unit.toLowerCase()) ? label : `${label} (${unit})`}
          </text>
        </g>
        {annotate && (
          <g className="axis">
            <text x={x(0) - 8} y={MARGIN.top + rows.length * rowH + 33} textAnchor="end">
              ← {annotate[0]}
            </text>
            <text x={x(0) + 8} y={MARGIN.top + rows.length * rowH + 33} textAnchor="start">
              {annotate[1]} →
            </text>
          </g>
        )}
        {rows.map((r, i) => {
          const y = MARGIN.top + i * rowH + rowH / 2;
          const clear = r.lo > 0 || r.hi < 0;
          return (
            <g key={r.dataset} opacity={clear ? 1 : 0.5}
               onMouseEnter={(e) => show(e, (
                 <>
                   <div className="k">{r.dataset}</div>
                   <strong>{signed(r.median)}</strong>{" "}
                   <span className="k">95% [{fmt3(r.lo)}, {fmt3(r.hi)}]</span>
                   <div className="k">{clear ? "interval clear of zero" : "interval spans zero"}</div>
                 </>
               ))} onMouseLeave={hide}>
              <rect x={0} y={y - rowH / 2} width={width} height={rowH} fill="transparent" />
              <text x={left - 12} y={y + 4} textAnchor="end" className="axis"
                    style={{ fontSize: "var(--chart-row)", fill: "var(--ink-secondary)" }}>
                {short(r.dataset)}
              </text>
              <line x1={x(r.lo)} x2={x(r.hi)} y1={y} y2={y} stroke={colour} strokeWidth={2}
                    strokeLinecap="round" />
              <line x1={x(r.lo)} x2={x(r.lo)} y1={y - 4} y2={y + 4} stroke={colour} strokeWidth={2} />
              <line x1={x(r.hi)} x2={x(r.hi)} y1={y - 4} y2={y + 4} stroke={colour} strokeWidth={2} />
              <circle cx={x(r.median)} cy={y} r={4.5} fill={colour} stroke="var(--surface)"
                      strokeWidth={2} />
            </g>
          );
        })}
      </svg>
      {tip}
    </div>
  );
}
