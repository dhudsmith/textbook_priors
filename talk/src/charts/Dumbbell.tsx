import { scaleLinear } from "d3-scale";
import { useTalk } from "../state";
import { useWidth } from "../hooks";
import { MARGIN, fmt3, short, signed, useHover } from "./primitives";

/* H2: AUC(A) against AUC(B), one dumbbell per dataset, in the arms' own colours. A dumbbell
   rather than two bars, because the claim is about two readings of the same images and a reader
   should see where the pair sits, not only the gap. */

export function Dumbbell() {
  const { study, armHue } = useTalk();
  const { ref, width } = useWidth<HTMLDivElement>(720);
  const { show, hide, tip } = useHover();
  const primary = study.study.primary;
  const order = study.study.arm_b_datasets;

  const rows = order.map((d) => {
    const per = study.per_dataset[d];
    return {
      dataset: d, a: per.auc["A"], b: per.auc[`B__${primary}`],
      diff: per.differences["B_minus_A"],
    };
  });

  const rowH = 26;
  const left = 118;
  const innerW = Math.max(180, width - left - 60);
  const h = MARGIN.top + MARGIN.bottom + rows.length * rowH;
  const lo = Math.min(...rows.flatMap((r) => [r.a, r.b])) - 0.03;
  const hi = Math.max(...rows.flatMap((r) => [r.a, r.b])) + 0.03;
  const x = scaleLinear().domain([lo, hi]).range([left, left + innerW]);

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={h} role="img"
           aria-label="Arm A against arm B, test AUC, one row per dataset">
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
          const bWins = r.b > r.a;
          return (
            <g key={r.dataset}
               onMouseEnter={(e) => show(e, (
                 <>
                   <div className="k">{r.dataset}</div>
                   arm A (zero-shot) <strong>{fmt3(r.a)}</strong><br />
                   arm B (textbook) <strong>{fmt3(r.b)}</strong>
                   <div className="k">B − A {signed(r.diff.median)} 95% [{fmt3(r.diff.lo)},
                     {" "}{fmt3(r.diff.hi)}]</div>
                 </>
               ))} onMouseLeave={hide}>
              <rect x={0} y={y - rowH / 2} width={width} height={rowH} fill="transparent" />
              <text x={left - 12} y={y + 4} textAnchor="end" className="axis"
                    style={{ fontSize: 11.5, fill: "var(--ink-secondary)" }}>
                {short(r.dataset)}
              </text>
              <line x1={x(Math.min(r.a, r.b))} x2={x(Math.max(r.a, r.b))} y1={y} y2={y}
                    stroke="var(--rule-strong)" strokeWidth={1.8} />
              <circle cx={x(r.a)} cy={y} r={4.5} fill={armHue("A")} stroke="var(--surface)"
                      strokeWidth={2} />
              <rect x={x(r.b) - 4.2} y={y - 4.2} width={8.4} height={8.4} rx={1}
                    fill={armHue("B")} stroke="var(--surface)" strokeWidth={2} />
              <text x={left + innerW + 8} y={y + 4} className="serieslabel"
                    fill={bWins ? "var(--good)" : "var(--ink-muted)"}>
                {bWins ? "B" : "A"}
              </text>
            </g>
          );
        })}
      </svg>
      {tip}
      <div className="controls" aria-label="Series">
        <span className="chip" style={{ cursor: "default" }}>
          <svg width="12" height="12" aria-hidden="true">
            <circle cx="6" cy="6" r="4.5" fill={armHue("A")} />
          </svg>
          arm A: zero-shot, the model's own guess
        </span>
        <span className="chip" style={{ cursor: "default" }}>
          <svg width="12" height="12" aria-hidden="true">
            <rect x="1.8" y="1.8" width="8.4" height="8.4" rx="1" fill={armHue("B")} />
          </svg>
          arm B: the textbook readout
        </span>
      </div>
    </div>
  );
}

/* The permutation controls, as bars: how much AUC each arm loses when the fingerprints are
   permuted across classes, or the concept columns across images. Free re-analyses of the archive,
   and the reason the concept answers are known to carry real class information. */
export function PermutationDrops() {
  const { study, armHue } = useTalk();
  const { ref, width } = useWidth<HTMLDivElement>(720);
  const { show, hide, tip } = useHover();
  const primary = study.study.primary;

  const rows = study.study.datasets.map((d) => {
    const per = study.per_dataset[d];
    return {
      dataset: d,
      b: per.controls[`B__${primary}`]?.drop ?? null,
      c: per.controls["C__n50"]?.drop ?? null,
    };
  });

  const rowH = 24;
  const left = 118;
  const innerW = Math.max(180, width - left - 26);
  const h = MARGIN.top + MARGIN.bottom + rows.length * rowH;
  const hi = Math.max(...rows.flatMap((r) => [r.b?.hi ?? 0, r.c?.hi ?? 0])) * 1.05;
  const x = scaleLinear().domain([0, hi]).range([left, left + innerW]);

  return (
    <div ref={ref}>
      <svg className="plot" width={width} height={h} role="img"
           aria-label="AUC lost under the permutation controls, per dataset and arm">
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
                style={{ fontWeight: 600 }}>AUC lost when the structure is permuted</text>
        </g>
        {rows.map((r, i) => {
          const y = MARGIN.top + i * rowH;
          return (
            <g key={r.dataset}>
              <text x={left - 12} y={y + rowH / 2 + 4} textAnchor="end" className="axis"
                    style={{ fontSize: 11.5, fill: "var(--ink-secondary)" }}>
                {short(r.dataset)}
              </text>
              {([["B", r.b], ["C", r.c]] as const).map(([arm, drop], k) =>
                drop ? (
                  <g key={arm}
                     onMouseEnter={(e) => show(e, (
                       <>
                         <div className="k">{r.dataset} · arm {arm}</div>
                         <strong>−{fmt3(drop.median)}</strong>{" "}
                         <span className="k">95% [{fmt3(drop.lo)}, {fmt3(drop.hi)}]</span>
                       </>
                     ))} onMouseLeave={hide}>
                    <rect x={left} y={y + 3 + k * 9} width={Math.max(1, x(drop.median) - left)}
                          height={7} rx={2} fill={armHue(arm)} />
                    <rect x={left} y={y + 3 + k * 9} width={innerW} height={7} fill="transparent" />
                  </g>
                ) : null)}
            </g>
          );
        })}
      </svg>
      {tip}
      <div className="controls" aria-label="Series">
        <span className="chip" style={{ cursor: "default" }}>
          <span className="swatch" style={{ background: armHue("B") }} /> arm B, fingerprints
          permuted across classes
        </span>
        <span className="chip" style={{ cursor: "default" }}>
          <span className="swatch" style={{ background: armHue("C") }} /> arm C at n = 50,
          concept columns permuted across images
        </span>
      </div>
    </div>
  );
}
