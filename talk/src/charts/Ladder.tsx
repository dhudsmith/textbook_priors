import { useState } from "react";
import { scalePoint, scaleLinear } from "d3-scale";
import { line as d3line } from "d3-shape";
import { useTalk } from "../state";
import { useWidth } from "../hooks";
import { AxisLeft, MARGIN, Marker, fmt3, plotBox, readerTick, short, spreadLabels, useHover }
  from "./primitives";

/* One line per dataset across an ordered list of models or readers. Used three times - the open
   models by size (H3), the closed models by price (H7) and the nine readers (H4) - because they
   are the same claim shape and a reader comparing them should be comparing one colour language,
   not three. Each dataset keeps the report's own colour AND its own marker, so no two share
   both. */

/** What the lines that are not named are called, once, at the foot of the label column. */
const GREY_LABEL = "other datasets";

export function Ladder({ order, values, yLabel, label, height = 380, divideAfter, note,
                         named = [] }: {
  order: string[];
  values: Record<string, Record<string, number>>;
  yLabel: string;
  label: string;
  height?: number;
  divideAfter?: number;
  note?: string;
  /** The datasets the paragraph beside the chart argues about. Those are drawn in their own
      colour and directly labelled; the rest go to one grey band with a single label, because
      eleven near-neighbour hues plus eleven displaced labels is not a chart a room can read.
      Hovering any line still isolates it, named or not. */
  named?: string[];
}) {
  const { hue, metaOf } = useTalk();
  const { ref, width: measured } = useWidth<HTMLDivElement>(780);
  const { show, hide, tip } = useHover();
  const [isolate, setIsolate] = useState<string | null>(null);

  const datasets = Object.keys(values).filter((d) => order.some((m) => values[d]?.[m] != null));
  const isNamed = (d: string) => named.length === 0 || named.includes(d);
  const anyGrey = datasets.some((d) => !isNamed(d));
  const all = datasets.flatMap((d) => order.map((m) => values[d][m]).filter((v) => v != null));

  // Tick text is the model stem, and the bottom margin is computed from the longest one at the
  // tilt it is drawn at. Nothing here relies on `overflow: visible` for its room.
  const ticks = order.map(readerTick);
  const tilt = order.length > 4;
  const longest = Math.max(...ticks.map((t) => t.length));
  const bottom = tilt
    ? Math.ceil(longest * 6.3 * Math.sin((22 * Math.PI) / 180)) + 30
    : 46;
  /* The right margin holds the direct end labels, so it is measured from the longest one drawn
     rather than fixed: "other datasets" ran off the edge of the plot at 108. */
  const rightLabels = [...datasets.filter(isNamed).map(short), ...(anyGrey ? [GREY_LABEL] : [])];
  const rightNeeded = Math.ceil(Math.max(0, ...rightLabels.map((t) => t.length)) * 7.6) + 16;
  const { width, margin: base } = plotBox(measured,
    { ...MARGIN, right: Math.max(108, rightNeeded) });
  const margin = { ...base, bottom };
  const innerW = Math.max(220, width - margin.left - margin.right);
  const innerH = height - margin.top - margin.bottom;
  const x = scalePoint<string>().domain(order).range([margin.left, margin.left + innerW]).padding(0.5);
  const y = scaleLinear().domain([Math.min(...all) - 0.03, Math.max(...all) + 0.03])
    .range([margin.top + innerH, margin.top]);

  // Twelve lines end in a narrow band of AUC, so the direct labels have to be pushed apart or
  // half of them are unreadable. Order is kept, so a label still sits nearest its own line.
  // Only the named lines are labelled, and each label keeps a leader line back to the end of the
  // line it names - `spreadLabels` moves labels, and a moved label without a leader points at the
  // wrong series.
  const labelled = datasets.filter(isNamed);
  const anchors = new Map(labelled.map((d) => {
    const pts = order.filter((m) => values[d][m] != null);
    return [d, y(values[d][pts[pts.length - 1]])];
  }));
  const endLabels = spreadLabels(
    labelled.map((d) => ({
      id: d, y: anchors.get(d)! + 3.5, colour: hue(d), text: short(d),
    })),
    12, margin.top + 6, margin.top + innerH + 6,
  );

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={height} role="img" aria-label={label}>
        <AxisLeft scale={y} x={margin.left} ticks={y.ticks(5)} width={innerW} label={yLabel} />
        <line x1={margin.left} x2={margin.left + innerW} y1={y(0.5)} y2={y(0.5)}
              stroke="var(--ink-muted)" strokeDasharray="1 4"
              opacity={y(0.5) > margin.top && y(0.5) < margin.top + innerH ? 1 : 0} />
        <g className="axis">
          {order.map((m, i) => {
            const tx = x(m)!;
            const ty = margin.top + innerH + 18;
            return (
              <text key={m} x={tx} y={ty} textAnchor={tilt ? "end" : "middle"}
                    transform={tilt ? `rotate(-22 ${tx} ${ty})` : undefined}
                    style={{ fontFamily: "var(--mono)", fontSize: "var(--chart-tick)" }}>
                {ticks[i]}
              </text>
            );
          })}
        </g>
        {divideAfter != null && divideAfter < order.length - 1 && (
          <line x1={(x(order[divideAfter])! + x(order[divideAfter + 1])!) / 2}
                x2={(x(order[divideAfter])! + x(order[divideAfter + 1])!) / 2}
                y1={margin.top} y2={margin.top + innerH} stroke="var(--rule-strong)"
                strokeDasharray="4 4" />
        )}
        {[...datasets].sort((a, b) => Number(isNamed(a)) - Number(isNamed(b))).map((d) => {
          const meta = metaOf(d);
          const pts = order.filter((m) => values[d][m] != null);
          const grey = !isNamed(d);
          const dim = isolate != null && isolate !== d;
          const stroke = grey && isolate !== d ? "var(--rule-strong)" : hue(d);
          const series = d3line<string>().x((m) => x(m)!).y((m) => y(values[d][m]));
          // The divider is a boundary the caption says not to read across, so the line is drawn
          // as two paths rather than one that steps over it.
          const segments = divideAfter == null
            ? [pts]
            : [pts.filter((m) => order.indexOf(m) <= divideAfter),
               pts.filter((m) => order.indexOf(m) > divideAfter)].filter((s) => s.length);
          return (
            <g key={d} opacity={dim ? 0.13 : 1}
               onMouseEnter={() => setIsolate(d)} onMouseLeave={() => setIsolate(null)}>
              {segments.map((seg, si) => (
                <g key={si}>
                  <path d={series(seg) ?? undefined} fill="none" stroke="transparent"
                        strokeWidth={12} />
                  <path d={series(seg) ?? undefined} fill="none" stroke={stroke}
                        strokeWidth={grey && isolate !== d ? 1 : 1.8} />
                </g>
              ))}
              {pts.map((m) => (
                <g key={m}
                   onMouseEnter={(e) => show(e, (
                     <>
                       <div className="k">{d}</div>
                       <strong>{fmt3(values[d][m])}</strong>
                       <div className="k mono">{m}</div>
                     </>
                   ))} onMouseLeave={hide}>
                  <circle cx={x(m)} cy={y(values[d][m])} r={12} fill="transparent" />
                  {(!grey || isolate === d) && (
                    <Marker kind={meta.marker} x={x(m)!} y={y(values[d][m])} r={4} fill={hue(d)}
                            stroke="var(--surface)" />
                  )}
                </g>
              ))}
            </g>
          );
        })}

        {endLabels.map((l) => (
          <g key={l.id} opacity={isolate == null || isolate === l.id ? 1 : 0.13}>
            <path d={`M${margin.left + innerW + 1} ${anchors.get(l.id)} ` +
                     `L${margin.left + innerW + 5} ${l.y - 3.5}`}
                  stroke={l.colour} strokeWidth={1} fill="none" opacity={0.7} />
            <text x={margin.left + innerW + 8} y={l.y} className="serieslabel" fill={l.colour}>
              {l.text}
            </text>
          </g>
        ))}
        {anyGrey && (
          <text x={margin.left + innerW + 8} y={margin.top + innerH + 4} className="serieslabel"
                fill="var(--ink-muted)">
            {GREY_LABEL}
          </text>
        )}
      </svg>
      {tip}
      {note && <p className="note">{note}</p>}
    </div>
  );
}
