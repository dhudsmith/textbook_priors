import { scaleLinear } from "d3-scale";
import { useTalk } from "../state";
import { useWidth } from "../hooks";
import { AxisBottom, AxisLeft, MARGIN, Marker, ZeroLine, fmt3, short, signed, useHover } from "./primitives";

/* Thinking's effect against how well the model read the concepts without it. The slope is the
   claim: thinking rescues the tasks the model read badly and costs the ones it read well. One
   point per dataset, in the dataset's own colour and marker. */

export function ThinkingScatter({ height = 360 }: { height?: number }) {
  const { study, hue, metaOf } = useTalk();
  const { ref, width } = useWidth<HTMLDivElement>(700);
  const { show, hide, tip } = useHover();

  const h4a = study.across.h4.h4a;
  const baseline = h4a.from as string;
  const rows = Object.keys(h4a.differences).map((d) => ({
    dataset: d,
    base: study.per_dataset[d].h4!.probe_auc[baseline],
    diff: h4a.differences[d] as { median: number; lo: number; hi: number },
  }));

  const innerW = Math.max(220, width - MARGIN.left - MARGIN.right);
  const innerH = height - MARGIN.top - MARGIN.bottom;
  const x = scaleLinear().domain([Math.min(...rows.map((r) => r.base)) - 0.05,
                                  Math.max(...rows.map((r) => r.base)) + 0.05])
    .range([MARGIN.left, MARGIN.left + innerW]);
  const y = scaleLinear().domain([Math.min(...rows.map((r) => r.diff.lo)) - 0.02,
                                  Math.max(...rows.map((r) => r.diff.hi)) + 0.02])
    .range([MARGIN.top + innerH, MARGIN.top]);

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={height} role="img"
           aria-label="Thinking's effect on the probe against the same model's probe AUC without thinking">
        <AxisLeft scale={y} x={MARGIN.left} ticks={y.ticks(5)} width={innerW}
                  label="thinking − no thinking (AUC)" format={(v) => signed(v, 2)} />
        <AxisBottom scale={x} y={MARGIN.top + innerH} ticks={x.ticks(5)}
                    label="probe AUC with thinking off" format={(v) => v.toFixed(2)} />
        <line x1={MARGIN.left} x2={MARGIN.left + innerW} y1={y(0)} y2={y(0)}
              stroke="var(--ink-muted)" strokeWidth={1} strokeDasharray="1 3" />
        <ZeroLine x={MARGIN.left} y1={MARGIN.top} y2={MARGIN.top} />
        {rows.map((r) => {
          const meta = metaOf(r.dataset);
          const clear = r.diff.lo > 0 || r.diff.hi < 0;
          return (
            <g key={r.dataset} opacity={clear ? 1 : 0.55}
               onMouseEnter={(e) => show(e, (
                 <>
                   <div className="k">{r.dataset}</div>
                   <strong>{signed(r.diff.median)}</strong>{" "}
                   <span className="k">95% [{fmt3(r.diff.lo)}, {fmt3(r.diff.hi)}]</span>
                   <div className="k">probe with thinking off {fmt3(r.base)}</div>
                 </>
               ))} onMouseLeave={hide}>
              <circle cx={x(r.base)} cy={y(r.diff.median)} r={13} fill="transparent" />
              <line x1={x(r.base)} x2={x(r.base)} y1={y(r.diff.lo)} y2={y(r.diff.hi)}
                    stroke={hue(r.dataset)} strokeWidth={1.4} opacity={0.6} />
              <Marker kind={meta.marker} x={x(r.base)} y={y(r.diff.median)} r={5}
                      fill={hue(r.dataset)} stroke="var(--surface)" />
              <text x={x(r.base) + 9} y={y(r.diff.median) + 4} className="serieslabel"
                    fill="var(--ink-secondary)">{short(r.dataset)}</text>
            </g>
          );
        })}
      </svg>
      {tip}
    </div>
  );
}
