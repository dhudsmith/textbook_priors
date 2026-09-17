import { scaleLinear } from "d3-scale";
import { line as d3line } from "d3-shape";
import type { Contention as ContentionData } from "../types";
import { useWidth } from "../hooks";
import { AxisBottom, AxisLeft, Legend, MARGIN, useHover } from "./primitives";

/* Seconds per call against jobs in flight. Two points per series rather than a curve, because
   that is what was measured; the caption and the changelog both say so. Not a dual axis: the
   aggregate-throughput reading sits in the tooltip and the table, on its own terms. */

const HUES = ["var(--principle)", "var(--nearmiss)", "var(--agent)"];

export function Contention({ data, height = 300 }: { data: ContentionData; height?: number }) {
  const { ref, width } = useWidth<HTMLDivElement>(700);
  const { show, hide, tip } = useHover();

  const all = data.series.flatMap((s) => s.points);
  const innerW = Math.max(220, width - MARGIN.left - MARGIN.right);
  const innerH = height - MARGIN.top - MARGIN.bottom;
  const x = scaleLinear().domain([0, Math.max(...all.map((p) => p.jobs)) * 1.08])
    .range([MARGIN.left, MARGIN.left + innerW]);
  const y = scaleLinear().domain([0, Math.max(...all.map((p) => p.s_per_call)) * 1.1])
    .range([MARGIN.top + innerH, MARGIN.top]);
  const path = d3line<{ jobs: number; s_per_call: number }>()
    .x((p) => x(p.jobs)).y((p) => y(p.s_per_call));

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={height} role="img"
           aria-label="Seconds per call against our own jobs in flight, three measured series">
        <AxisLeft scale={y} x={MARGIN.left} ticks={y.ticks(5)} width={innerW}
                  label="seconds per call" format={(v) => String(v)} />
        <AxisBottom scale={x} y={MARGIN.top + innerH} ticks={x.ticks(6)}
                    label="our own jobs in flight" />
        {data.series.map((s, i) => (
          <g key={s.id}>
            <path d={path(s.points) ?? undefined} fill="none" stroke={HUES[i % HUES.length]}
                  strokeWidth={2} />
            {s.points.map((p) => (
              <g key={p.jobs}
                 onMouseEnter={(e) => show(e, (
                   <>
                     <div className="k">{s.label}</div>
                     <strong>{p.s_per_call} s</strong> per call at {p.jobs} job
                     {p.jobs === 1 ? "" : "s"}
                     <div className="k mono">{p.calls_per_s} calls/s aggregate · {s.model}</div>
                   </>
                 ))} onMouseLeave={hide}>
                <circle cx={x(p.jobs)} cy={y(p.s_per_call)} r={12} fill="transparent" />
                <circle cx={x(p.jobs)} cy={y(p.s_per_call)} r={4.5} fill={HUES[i % HUES.length]}
                        stroke="var(--surface)" strokeWidth={2} />
              </g>
            ))}
            <text x={x(s.points[s.points.length - 1].jobs) - 6}
                  y={y(s.points[s.points.length - 1].s_per_call) - 10}
                  textAnchor="end" className="serieslabel" fill={HUES[i % HUES.length]}>
              {s.points[s.points.length - 1].s_per_call} s
            </text>
          </g>
        ))}
      </svg>
      {tip}
      <Legend items={data.series.map((s, i) => ({
        id: s.id, label: s.label, colour: HUES[i % HUES.length],
      }))} />
    </div>
  );
}
