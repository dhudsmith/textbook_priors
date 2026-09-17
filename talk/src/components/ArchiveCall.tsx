import { useMemo, useState } from "react";
import type { ArchiveSample } from "../types";
import { LAZY, asset, loadPrompt } from "../data";
import { useAsync } from "../hooks";
import { Deep } from "./ui";

/* One real archived call: the image, the rendered prompt, the raw reply, the parsed answer and
   the chunk manifest's fields. The draw is random, so no two people in the room see the same one
   and the speaker can show a call without buying one. Nothing here is live: results/score/ is
   write-protected and this is a copy of four records per dataset. */

export function ArchiveCall({ sample, fixedDataset }: {
  sample: ArchiveSample; fixedDataset?: string;
}) {
  const pool = useMemo(
    () => sample.records.filter((r) => !fixedDataset || r.dataset === fixedDataset),
    [sample.records, fixedDataset]);
  const [i, setI] = useState(() => Math.floor(Math.random() * Math.max(1, pool.length)));
  const rec = pool[i % Math.max(1, pool.length)];
  const manifest = rec ? sample.manifests[rec.manifest_key] : null;
  const redactions = sample.provenance?.redactions ?? [];
  const { data: prompt } = useAsync(
    () => (rec ? loadPrompt(rec.dataset) : Promise.resolve("")), [rec?.dataset]);

  if (!rec || !manifest) return <p className="note">No archived record for this dataset.</p>;

  return (
    <div>
      <div className="controls">
        <button className="plain"
                onClick={() => setI(Math.floor(Math.random() * pool.length))}>
          Draw another archived call
        </button>
        <span className="note" style={{ margin: 0 }}>
          {pool.length} exported records{fixedDataset ? ` for ${fixedDataset}` : ""}
        </span>
      </div>

      <div style={{ display: "grid", gap: "1rem",
                    gridTemplateColumns: "minmax(150px, 210px) minmax(0, 1fr)" }}>
        <div>
          <div className="imgcard">
            <img src={asset(rec.image)} alt={`${rec.dataset} test image ${rec.position}`}
                 width={224} height={224} loading={LAZY} />
          </div>
          <p className="note" style={{ marginTop: "0.4rem" }}>
            {rec.dataset}, test position {rec.position} (release row {rec.index})
          </p>
        </div>
        <div>
          <h4>What came back, verbatim</h4>
          <pre className="file">{rec.text ?? "(nothing readable)"}</pre>
          <h4>What was parsed out of it</h4>
          {rec.answers && Object.keys(rec.answers).length ? (
            <dl className="kv">
              {Object.entries(rec.answers).map(([k, v]) => (
                <div key={k} style={{ display: "contents" }}>
                  <dt>{k}</dt><dd>{String(v)}</dd>
                </div>
              ))}
            </dl>
          ) : <p className="note">No parsed answer recorded.</p>}
        </div>
      </div>

      <h4 style={{ marginTop: "1rem" }}>The manifest, which is what makes it checkable</h4>
      <dl className="kv" style={{ maxWidth: "46rem" }}>
        <dt>served_model</dt><dd>{manifest.served_model}</dd>
        <dt>prompt_sha256</dt><dd>{manifest.prompt_sha256}</dd>
        {manifest.bank_sha256 && (<><dt>bank_sha256</dt><dd>{manifest.bank_sha256}</dd></>)}
        <dt>git_commit</dt><dd>{manifest.git_commit}</dd>
        <dt>slurm_job</dt><dd>{manifest.slurm_job ?? "—"}</dd>
        <dt>host</dt><dd>{manifest.host}</dd>
        <dt>written</dt><dd>{manifest.written}</dd>
        <dt>temperature</dt><dd>{String(manifest.temperature)}</dd>
        <dt>reasoning</dt><dd>{String(manifest.reasoning)}</dd>
        <dt>this call</dt>
        <dd>
          {rec.elapsed_s != null ? `${rec.elapsed_s} s` : "—"}
          {rec.usage ? `, ${rec.usage.prompt_tokens} prompt + ${rec.usage.completion_tokens} ` +
                       "completion tokens" : ""}
          {rec.finish_reason ? `, finish_reason ${rec.finish_reason}` : ""}
          {rec.from_reasoning ? ", answered in the reasoning field" : ""}
        </dd>
        <dt>this chunk</dt>
        <dd>
          {manifest.file} — {manifest.calls} calls, {manifest.complete} complete, median{" "}
          {manifest.seconds_per_call.median} s per call
        </dd>
      </dl>
      {redactions.length > 0 && (
        <p className="note">
          Two fields are not the archive's own, and the export says so: {redactions.join("; ")}.
        </p>
      )}

      <Deep summary={`The rendered ${rec.prompt === "concept" ? "concept" : "zero-shot"} prompt, verbatim`}>
        <pre className="file">{promptSection(prompt, rec.prompt)}</pre>
        <p className="note">
          From <span className="mono">results/prompts_txt/{rec.dataset}.txt</span> — a render of
          the same file the archive was hashed against, not a second copy of the prompt logic.
        </p>
      </Deep>
    </div>
  );
}

/** The txt render holds both prompts under their own headers; show the one this record bought. */
function promptSection(text: string | null, prompt: string): string {
  if (!text) return "loading…";
  const marks = [...text.matchAll(/^--- .*prompt \(sha256 [0-9a-f]+\) ---$/gm)];
  if (marks.length < 2) return text;
  const wanted = marks.find((m) =>
    prompt === "concept" ? m[0].includes("concept prompt") : m[0].includes("zero_shot"));
  if (!wanted) return text;
  const start = wanted.index ?? 0;
  const next = marks.find((m) => (m.index ?? 0) > start);
  return text.slice(start, next ? next.index : undefined).trim();
}
