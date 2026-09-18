import { useEffect, useMemo, useState } from "react";
import { scaleLinear, scaleLog } from "d3-scale";
import { line as d3line, area as d3area, curveMonotoneX } from "d3-shape";
import { useTalk } from "../state";
import { useWidth } from "../hooks";
import { AxisBottom, AxisLeft, Legend, fmt2, fmt3, leftGutter, plotBox, spreadLabels, useHover }
  from "./primitives";

/* H1's learning curve. Arms C, P and C+P move with n; arms A and B are horizontal lines, because
   they use no labels at all; the published ceiling is a fixed reference and deliberately not one
   of the arms - a different colour, a sparser dash, no fill, and its own legend wording.
   The dashed vertical mark is where arm P reaches arm B: how many labelled images it takes to
   match the literature with no labels at all, which is the headline number of H1. */

const LABELLED = ["C", "P", "CP"] as const;

export function LearningCurve({ height = 400, initialHidden = [] }: {
  height?: number; initialHidden?: string[];
}) {
  const { study, dataset, meta, armHue, armDash } = useTalk();
  const per = study.per_dataset[dataset];
  const { ref, width: measured } = useWidth<HTMLDivElement>(820);
  const { width, margin: base } = plotBox(measured);
  const { show, hide, tip } = useHover();
  // The series the speaker adds live start hidden; the legend still lists every one of them.
  const [hidden, setHidden] = useState<Set<string>>(() => new Set(initialHidden));
  // The question picker above the figure changes the preset, so the figure follows it rather
  // than keeping whatever the first question left showing.
  const preset = initialHidden.join(",");
  useEffect(() => setHidden(new Set(preset ? preset.split(",") : [])), [preset]);

  const ns = per.curve_n;
  const primary = study.study.primary;
  const bKey = `B__${primary}`;
  const armB = per.auc[bKey];
  const armA = per.auc["A"];
  const ceiling = per.ceiling.auc;
  const nB = per.n_b?.point ?? null;

  const series = useMemo(() => {
    const rows = LABELLED.map((arm) => ({
      id: arm,
      label: study.style.arms.find((a) => a.id === arm)!.label,
      points: ns.map((n) => ({ n, ...per.curve[`${arm}__n${n}`] })).filter((p) => p.point != null),
    }));
    return rows.filter((r) => r.points.length);
  }, [ns, per.curve, study.style.arms]);

  const flat = [
    armB != null ? { id: "B", value: armB } : null,
    armA != null ? { id: "A", value: armA } : null,
    { id: "lit", value: ceiling },
  ].filter(Boolean) as { id: string; value: number }[];

  const values = [
    ...series.filter((s) => !hidden.has(s.id)).flatMap((s) => s.points.flatMap((p) => [p.lo, p.hi])),
    ...flat.filter((f) => !hidden.has(f.id)).map((f) => f.value),
  ];
  const lo = Math.max(0, Math.min(...values) - 0.03);
  const hi = Math.min(1.001, Math.max(...values) + 0.03);

  // The gutter is worked out from the ticks the axis will actually draw, which needs the tick
  // values but not the scale's range, so the left margin is settled before anything is placed.
  const yTicks = scaleLinear().domain([lo, hi]).ticks(5);
  const MARGIN = { ...base, left: Math.max(base.left, leftGutter(yTicks, fmt2, "test AUC")) };
  const innerW = Math.max(240, width - MARGIN.left - MARGIN.right);
  const innerH = height - MARGIN.top - MARGIN.bottom;
  const x = scaleLog().domain([ns[0], ns[ns.length - 1]]).range([MARGIN.left, MARGIN.left + innerW]);
  const y = scaleLinear().domain([lo, hi]).range([MARGIN.top + innerH, MARGIN.top]);

  const path = d3line<{ n: number; point: number }>()
    .x((p) => x(p.n)).y((p) => y(p.point)).curve(curveMonotoneX);
  const band = d3area<{ n: number; lo: number; hi: number }>()
    .x((p) => x(p.n)).y0((p) => y(p.lo)).y1((p) => y(p.hi)).curve(curveMonotoneX);

  const toggle = (id: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });

  const legend = [
    ...series.map((s) => ({ id: s.id, label: s.label, colour: armHue(s.id), dash: armDash(s.id) })),
    ...flat.map((f) => ({
      id: f.id,
      label: f.id === "lit"
        ? study.style.literature.label
        : study.style.arms.find((a) => a.id === f.id)!.label,
      colour: armHue(f.id), dash: armDash(f.id),
    })),
  ];

  const nBx = nB && /^\d+$/.test(nB) ? x(Number(nB)) : null;

  const endLabels = spreadLabels(
    [
      ...flat.filter((f) => !hidden.has(f.id)).map((f) => ({
        id: f.id, y: y(f.value) + 4, colour: armHue(f.id),
        text: f.id === "lit" ? "ceiling" : `arm ${f.id}`,
      })),
      ...series.filter((s) => !hidden.has(s.id)).map((s) => ({
        id: s.id, y: y(s.points[s.points.length - 1].point) + 4, colour: armHue(s.id),
        text: s.id === "CP" ? "C+P" : `arm ${s.id}`,
      })),
    ],
    17, MARGIN.top + 8, MARGIN.top + innerH,
  );

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={height} role="img"
           aria-label={`${dataset}: test AUC for each arm against the number of labelled ` +
                       "images it was given. Arms given no labels are drawn as flat lines."}>
        <AxisLeft scale={y} x={MARGIN.left} ticks={yTicks} width={innerW} label="test AUC" />
        <AxisBottom scale={x} y={MARGIN.top + innerH} ticks={ns} label="labelled images (n)" />

        {nBx != null && !hidden.has("B") && (
          <g>
            <line x1={nBx} x2={nBx} y1={MARGIN.top} y2={MARGIN.top + innerH}
                  stroke="var(--ink-muted)" strokeWidth={1} strokeDasharray="2 4" />
            <text x={nBx + 4} y={MARGIN.top + 11} className="serieslabel"
                  fill="var(--ink-secondary)">{nB} labels to match arm B</text>
          </g>
        )}

        {flat.filter((f) => !hidden.has(f.id)).map((f) => (
          <line key={f.id} x1={MARGIN.left} x2={MARGIN.left + innerW} y1={y(f.value)}
                y2={y(f.value)} stroke={armHue(f.id)} strokeWidth={2}
                strokeDasharray={armDash(f.id)} />
        ))}

        {series.filter((s) => !hidden.has(s.id)).map((s) => (
          <g key={s.id}>
            <path d={band(s.points as never) ?? undefined} fill={armHue(s.id)} opacity={0.14} />
            <path d={path(s.points as never) ?? undefined} fill="none" stroke={armHue(s.id)}
                  strokeWidth={2} strokeDasharray={armDash(s.id)} />
            {s.points.map((p) => (
              <g key={p.n}
                 onMouseEnter={(e) => show(e, (
                   <>
                     <div className="k">{s.label}</div>
                     <strong>{fmt3(p.point)}</strong>{" "}
                     <span className="k">95% [{fmt3(p.lo)}, {fmt3(p.hi)}]</span>
                     <div className="k mono">n = {p.n} · {dataset}</div>
                   </>
                 ))}
                 onMouseLeave={hide}>
                <circle cx={x(p.n)} cy={y(p.point)} r={12} fill="transparent" />
                <circle cx={x(p.n)} cy={y(p.point)} r={3.6} fill={armHue(s.id)}
                        stroke="var(--surface)" strokeWidth={1.4} />
              </g>
            ))}
          </g>
        ))}

        {/* Direct labels last and pushed apart, so a series that lands on another is still read. */}
        {/* Text wears text ink: at 11 px bold on the light surface the arm B green measured
            3.3:1 and the arm A grey 3.9:1. The line beside the label carries the identity, and
            the legend's swatch carries it again. */}
        {endLabels.map((l) => (
          <text key={l.id} x={MARGIN.left + innerW + 6} y={l.y} className="serieslabel"
                fill="var(--ink-secondary)">{l.text}</text>
        ))}
      </svg>
      {tip}
      <Legend items={legend} onToggle={toggle} hidden={hidden} />
      {!meta.has_arm_b && (
        <p className="note">
          {dataset} is multi-label, so arms A and B are not defined for it and are not drawn.
        </p>
      )}
    </div>
  );
}
