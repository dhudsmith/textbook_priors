import { scaleLinear } from "d3-scale";
import type { Contention as ContentionData } from "../types";
import { useWidth } from "../hooks";
import { AxisBottom, plotBox, useHover } from "./primitives";

/* What our own load did to a call. Each prompt was measured at exactly two points - one job in
   flight, and a wave of them - so the chart is a pair of bars per prompt, not a line: two points
   joined by a straight segment assert a continuum across the interval that nobody measured, and a
   caption disclaiming it ("two points per series, not a curve") is the form admitting it is wrong.
   Each bar carries its own value, so the comparison is read without a scale, and the pair is told
   apart by its fill as well as its hue. */

const HUES = ["var(--principle)", "var(--nearmiss)", "var(--agent)"];

export function Contention({ data }: { data: ContentionData }) {
  const { ref, width: measured } = useWidth<HTMLDivElement>(700);
  const { show, hide, tip } = useHover();
  const { width, margin } = plotBox(measured, { top: 24, right: 20, bottom: 44, left: 150 });

  const rows = data.series.flatMap((s, i) =>
    s.points.map((p, k) => ({
      series: s, hue: HUES[i % HUES.length], point: p, first: k === 0, band: i,
    })));
  const innerW = Math.max(180, width - margin.left - margin.right);
  const height = margin.top + margin.bottom + rows.length * 26 + data.series.length * 14;
  const max = Math.max(...rows.map((r) => r.point.s_per_call));
  const x = scaleLinear().domain([0, max * 1.12]).range([margin.left, margin.left + innerW]);

  let y = margin.top;
  const placed = rows.map((r, i) => {
    if (i > 0 && rows[i - 1].band !== r.band) y += 14;
    const at = y;
    y += 26;
    return { ...r, y: at };
  });

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={height} role="img"
           aria-label={"Seconds per call with one job running, against many running at once, " +
                       "for each prompt"}>
        <g className="grid">
          {x.ticks(5).map((t) => (
            <line key={t} x1={x(t)} x2={x(t)} y1={margin.top - 6} y2={height - margin.bottom} />
          ))}
        </g>
        <AxisBottom scale={x} y={height - margin.bottom} ticks={x.ticks(5)}
                    label="seconds per call" format={(v) => String(v)} />
        {placed.map((r) => (
          <g key={`${r.series.id}-${r.point.jobs}`}
             onMouseEnter={(e) => show(e, (
               <>
                 <div className="k">{r.series.label}</div>
                 <strong>{r.point.s_per_call} s</strong> per call at {r.point.jobs} job
                 {r.point.jobs === 1 ? "" : "s"}
                 <div className="k mono">
                   {r.point.calls_per_s} calls/s aggregate · {r.series.model}
                 </div>
               </>
             ))} onMouseLeave={hide}>
            <rect x={0} y={r.y - 4} width={width} height={26} fill="transparent" />
            <text x={margin.left - 10} y={r.y + 13} textAnchor="end" className="axis"
                  style={{ fontSize: "var(--chart-row)", fill: "var(--ink-secondary)" }}>
              {r.point.jobs} job{r.point.jobs === 1 ? "" : "s"}
            </text>
            {/* One job is the hollow bar, the wave is the filled one: the pair is told apart by
                more than its hue. */}
            <rect x={margin.left} y={r.y} width={Math.max(2, x(r.point.s_per_call) - margin.left)}
                  height={18} rx={3.5}
                  fill={r.first ? "var(--surface)" : r.hue}
                  stroke={r.hue} strokeWidth={r.first ? 2 : 0} />
            <text x={x(r.point.s_per_call) + 8} y={r.y + 13} className="serieslabel"
                  fill="var(--ink-secondary)">
              {r.point.s_per_call} s
            </text>
          </g>
        ))}
        {data.series.map((s, i) => {
          const top = placed.find((r) => r.band === i)!;
          return (
            <text key={s.id} x={2} y={top.y - 8} textAnchor="start"
                  className="serieslabel" fill={HUES[i % HUES.length]}>
              {s.label}
            </text>
          );
        })}
      </svg>
      {tip}
      <p className="note">
        A hollow bar is one job on its own; a filled bar is many at once.
      </p>
    </div>
  );
}
