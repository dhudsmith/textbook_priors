/* The shape of the snapshot `talk/scripts/export_talk_data.py` writes. Only the fields the site
   reads are typed; the deep per-dataset records stay index signatures, because they are copied
   verbatim out of results/evaluate/*.json and the site reads them by key. */

export type Interval = { median: number; lo: number; hi: number; point?: number };
export type CurvePoint = { point: number; median: number; lo: number; hi: number };

export interface DatasetMeta {
  name: string;
  modality: string;
  task: string;
  medmnist_task: string;
  source_dataset: string | null;
  multi_label: boolean;
  has_arm_b: boolean;
  n_classes: number;
  classes: string[];
  n_channels: number;
  split_sizes: { train: number; val: number; test: number };
  test_n: number;
  pool_n: number;
  curve_n: number[];
  n_concepts: number;
  colour: string;
  colour_dark: string;
  marker: string;
  samples: { class: string; position: number; file: string }[];
}

export interface Verdict {
  id: string;
  section: string;
  title: string;
  question: string;
  rule: string;
  wins: number;
  threshold: number;
  n_datasets: number;
  p: number;
  supported: boolean;
  per_dataset: Record<string, boolean>;
  metric: string;
  registered: { commit: string; short: string; date: string };
  rule_precedes_numbers: boolean | null;
  verdict: string;
}

export interface PerDataset {
  auc: Record<string, number>;
  curve: Record<string, CurvePoint>;
  curve_n: number[];
  differences: Record<string, Interval>;
  controls: Record<string, { permuted: number; drop: Interval }>;
  n_b: { point: string; lo: string; hi: string } | null;
  arm_b_by_model: Record<string, number> | null;
  h4: { subsample: number; probe_auc: Record<string, number>;
        steps: Record<string, Interval & { from: string; to: string }> } | null;
  h6: (Interval & { more: string; less: string }) | null;
  h7: { ladder: string[]; probe_auc: Record<string, number>;
        top_minus_bottom: Interval & { from: string; to: string } } | null;
  complete_frac: Record<string, number>;
  feature_columns: Record<string, number> | null;
  ceiling: { method: string; auc: number; acc: number | null;
             methods: Record<string, { auc: number; acc: number }> };
  largest_n: number;
}

export interface ArmStyle {
  id: string; label: string; colour: string; dark: string; dash: string | null;
}

export interface Study {
  provenance: { run_git_commit: string; exported: string; source_files: string[];
                redactions?: string[] };
  run: { git_commit: string; git_dirty: boolean; written: string; host: string;
         versions: Record<string, string> };
  study: {
    datasets: string[]; arm_b_datasets: string[]; primary: string; alpha: number; size: number;
    sample: { test_n: number; pool_n: number; seed: number };
    curve: { n: number[]; seeds: number[] };
    bootstrap: number;
    models: Record<string, { family: string; params_b: number; splits: string[] }>;
    readers: Record<string, { model: string; effort: string; api: string; subsample: number }>;
    zenodo_record: number; medmnist_version: string;
    literature: { citation: string; title: string; url: string; table: string };
  };
  style: { arms: ArmStyle[]; literature: ArmStyle };
  datasets: DatasetMeta[];
  verdicts: Verdict[];
  across: Record<string, any>;
  per_dataset: Record<string, PerDataset>;
  ceiling: {
    rows: { dataset: string; ceiling: number; pixel: number; concept: number; zero?: number;
            largest_n: number }[];
    median_gap: { zero: number; concept: number; pixel: number };
    largest_n: number;
    pixel_within_two_points: number;
    zero_within_five_points: number;
    pixel_at_or_above: number;
  };
  archive: {
    chunks: number; calls: number; first_written: string; last_written: string;
    by_model: Record<string, { calls: number; chunks: number; served: string[] }>;
  };
  stages: { id: string; name: string; jobs: number; unit: string }[];
  ledger: {
    calls: number; chunks: number; datasets: number; tests: number | null; hypotheses: number;
    supported: number; arms: number; readers: number; figures: number;
    session_log_entries: number;
    work_dates: string[];
    catches: { what: string; caught_by: string; source: string }[];
  };
  figures: string[];
}

export interface TimelineEntry {
  date: string; time: string; title: string; kind: string; lead: string;
}
export interface Timeline {
  source: string; days: string[]; entries: TimelineEntry[];
  kinds: { id: string; label: string }[]; kind_note: string;
}

export interface Contention {
  source: string; note: string;
  series: { id: string; label: string; model: string;
            points: { jobs: number; s_per_call: number; calls_per_s: number }[] }[];
  ladder_models: { model: string; cap: number; s_per_call: number }[];
}

export interface Concept {
  id: string; question: string; scale: string[]; sources: string[];
  anchors: Record<string, { text: string; sources: string[] }>;
}
export interface Bank {
  dataset: string; modality: string; task: string; source_dataset: string | null;
  provenance: Record<string, any>;
  concepts: Concept[];
  classes: Record<string, { fingerprint: Record<string, string>; sources: string[] }>;
}

export interface ArchiveRecord {
  id: string; dataset: string; prompt: string; manifest_key: string; position: number;
  index: number; label: number | number[]; image: string;
  answers: Record<string, string> | null; parsed: boolean; complete: boolean;
  invalid: Record<string, unknown>; text: string | null; served_model: string | null;
  finish_reason: string | null; from_reasoning: boolean | null; elapsed_s: number | null;
  usage: { prompt_tokens: number; completion_tokens: number; total_tokens: number } | null;
}
export interface ArchiveManifest {
  file: string; served_model: string; prompt_sha256: string; bank_sha256: string | null;
  git_commit: string; slurm_job: string | null; host: string; written: string;
  temperature: number | null; reasoning: string | null; max_tokens: number | null;
  calls: number; complete: number;
  seconds_per_call: { median: number; min: number; max: number; total: number };
}
export interface ArchiveSample {
  manifests: Record<string, ArchiveManifest>;
  records: ArchiveRecord[];
  provenance: { run_git_commit: string; exported: string; source_files: string[];
                redactions?: string[] };
}
