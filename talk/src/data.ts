import type { ArchiveSample, Bank, Contention, Study, Timeline } from "./types";

/* Everything the page shows comes from here: the snapshot the `talk_data` rule wrote into
   `public/data/`. No number is typed into the site source. `import.meta.env.BASE_URL` keeps the
   paths right under the `/textbook_priors/` base the site is deployed at, and the cache means a
   section that scrolls into view twice fetches once - a conference network is not to be trusted. */

/* `?static=1` freezes the page in its final state - sections already entered, stat tiles on their
   final value, the deferred panels mounted - so a headless screenshot and a print show what a
   reader would see after the animations finish. `prefers-reduced-motion` means the same thing and
   is honoured the same way. */
export const STATIC = (() => {
  if (typeof window === "undefined") return false;
  const q = new URLSearchParams(window.location.search).get("static");
  if (q !== null && q !== "0") return true;
  return !!window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;
})();

export const BASE = import.meta.env.BASE_URL;
export const asset = (rel: string) => `${BASE}${rel.replace(/^\//, "")}`;

const cache = new Map<string, Promise<unknown>>();

/* What a promise from here has already resolved to, so a component can render its data in the
   same pass rather than one effect later. It matters only in static mode, where the files are
   read synchronously and a screenshot has to catch the finished page. */
const settled = new Map<Promise<unknown>, unknown>();

export function settledValue<T>(p: Promise<T>): T | undefined {
  return settled.has(p as Promise<unknown>) ? (settled.get(p as Promise<unknown>) as T) : undefined;
}

async function fetchOk(rel: string): Promise<Response> {
  const res = await fetch(asset(rel));
  if (!res.ok) throw new Error(`could not load ${rel} (${res.status})`);
  return res;
}

/** Static mode only: read the file on the spot, so the first render already has it. */
function readNow(rel: string): string {
  const xhr = new XMLHttpRequest();
  xhr.open("GET", asset(rel), false);
  xhr.send();
  if (xhr.status && (xhr.status < 200 || xhr.status >= 300)) {
    throw new Error(`could not load ${rel} (${xhr.status})`);
  }
  return xhr.responseText;
}

function once<T>(rel: string, load: () => Promise<T>, parse: (raw: string) => T): Promise<T> {
  let pending = cache.get(rel) as Promise<T> | undefined;
  if (!pending) {
    if (STATIC && typeof XMLHttpRequest !== "undefined") {
      const value = parse(readNow(rel));
      pending = Promise.resolve(value);
      settled.set(pending as Promise<unknown>, value);
    } else {
      pending = load();
      pending.then((value) => settled.set(pending as Promise<unknown>, value), () => undefined);
    }
    cache.set(rel, pending as Promise<unknown>);
  }
  return pending;
}

const json = <T,>(rel: string) =>
  once(rel, async () => (await fetchOk(rel)).json() as Promise<T>, (raw) => JSON.parse(raw) as T);
const text = (rel: string) => once(rel, async () => (await fetchOk(rel)).text(), (raw) => raw);

export const loadStudy = () => json<Study>("data/study.json");
export const loadTimeline = () => json<Timeline>("data/timeline.json");
export const loadContention = () => json<Contention>("data/contention.json");
export const loadArchive = () => json<ArchiveSample>("data/archive_sample.json");
export const loadBank = (dataset: string) => json<Bank>(`data/bank/${dataset}.json`);
export const loadPrompt = (dataset: string) => text(`data/prompts/${dataset}.txt`);

/** A promise read by Suspense-free components: `use`-style hook lives in hooks.ts. */
export type Loader<T> = () => Promise<T>;

/** `loading` for every image on the page: lazy normally, eager in static mode so that a
    screenshot or a print carries the pictures rather than their alt text. */
export const LAZY: "lazy" | "eager" = STATIC ? "eager" : "lazy";
