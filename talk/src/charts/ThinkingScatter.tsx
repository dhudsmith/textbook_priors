import { scaleLinear } from "d3-scale";
import { useTalk } from "../state";
import { useWidth } from "../hooks";
import { AxisBottom, AxisLeft, Marker, fmt3, leftGutter, plotBox, short, signed, spreadLabels,
  useHover } from "./primitives";

/* Thinking's effect against how well the model scored the visual features without it. The slope
   is the claim: thinking helps on the tasks the model read badly and hurts on the ones it read
   well. One point per dataset, in the dataset's own colour and marker. */

const Y_LABEL = "thinking − no thinking (AUC)";

export function ThinkingScatter({ height = 360 }: { height?: number }) {
  const { study, hue, metaOf } = useTalk();
  const { ref, width: measured } = useWidth<HTMLDivElement>(700);
  const { width, margin: base } = plotBox(measured);
  const { show, hide, tip } = useHover();

  const h4a = study.across.h4.h4a;
  const baseline = h4a.from as string;
  const rows = Object.keys(h4a.differences).map((d) => ({
    dataset: d,
    base: study.per_dataset[d].h4!.probe_auc[baseline],
    diff: h4a.differences[d] as { median: number; lo: number; hi: number },
  }));

  // Signed ticks are the widest on the page, so the gutter is measured from them before the
  // scales are built rather than assumed.
  const yDomain: [number, number] = [Math.min(...rows.map((r) => r.diff.lo)) - 0.02,
                                     Math.max(...rows.map((r) => r.diff.hi)) + 0.02];
  const yFormat = (v: number) => signed(v, 2);
  const yTicks = scaleLinear().domain(yDomain).ticks(5);
  const MARGIN = {
    ...base, left: Math.max(base.left, leftGutter(yTicks, yFormat, Y_LABEL)),
  };
  const innerW = Math.max(220, width - MARGIN.left - MARGIN.right);
  const innerH = height - MARGIN.top - MARGIN.bottom;
  const x = scaleLinear().domain([Math.min(...rows.map((r) => r.base)) - 0.05,
                                  Math.max(...rows.map((r) => r.base)) + 0.05])
    .range([MARGIN.left, MARGIN.left + innerW]);
  const y = scaleLinear().domain(yDomain).range([MARGIN.top + innerH, MARGIN.top]);

  const labels = spreadLabels(
    rows.map((r) => ({
      id: r.dataset, text: short(r.dataset), x: x(r.base) + 11,
      ax: x(r.base), ay: y(r.diff.median), y: y(r.diff.median) + 4,
    })),
    17, MARGIN.top + 8, MARGIN.top + innerH,
  );

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={height} role="img"
           aria-label={"One point per dataset: how much the thinking step changed the probe's " +
                       "AUC, against how well the same model scored the visual features with " +
                       "thinking off. The points slope downwards."}>
        <AxisLeft scale={y} x={MARGIN.left} ticks={yTicks} width={innerW}
                  label={Y_LABEL} format={yFormat} />
        <AxisBottom scale={x} y={MARGIN.top + innerH} ticks={x.ticks(5)}
                    label="probe AUC with thinking off" format={(v) => v.toFixed(2)} />
        <line x1={MARGIN.left} x2={MARGIN.left + innerW} y1={y(0)} y2={y(0)}
              stroke="var(--ink-muted)" strokeWidth={1} strokeDasharray="1 3" />
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
            </g>
          );
        })}
        {/* The labels are placed last and pushed apart: at 1366 px three of them already sat
            within twelve pixels of each other and at 390 px they ran together outright. */}
        {labels.map((l) => (
          <g key={l.id}>
            <line x1={l.ax + 7} y1={l.ay} x2={l.x - 2} y2={l.y - 4} stroke="var(--rule-strong)"
                  strokeWidth={1} />
            <text x={l.x} y={l.y} className="serieslabel" fill="var(--ink-secondary)">
              {l.text}
            </text>
          </g>
        ))}
      </svg>
      {tip}
    </div>
  );
}
