"""embed: the concept answers and the bank, as prose, in one text-embedding space.

H5 (WORKFLOW.md section 2) asks whether the textbook carries class information that arm B's
readout loses. H2's controls said the answers carry real information; the nearest-fingerprint
distance lost anyway; H4 said no better reader of the concepts changed that. So this module keeps
the answers exactly as the archive holds them and changes only how they are read. An image's
answers and a class's fingerprint are the same kind of object - committed levels over the bank's
concepts - and the bank supplies cited prose for every level. Rendered as prose and embedded, an
image and a class become two unit vectors and the class score is their cosine: a learned semantic
distance over the bank's own words, in place of arithmetic over equally spaced ordinal codes.

Three arms come out of it (WORKFLOW.md section 3):

  * Z, the image's rendered answers against each class *name*;
  * T, the image's rendered answers against each class's rendered *fingerprint* - arm B's
    comparison, same subset of the bank (`any` renders nothing for a class, a missing answer
    renders nothing for an image), different distance;
  * E, the embedding of the rendered answers under arm C's classifier.

Nothing here asks a VLM anything. The archive is read, not re-bought, and the only new traffic is
text through the service's `/v1/embeddings`, which is local, deterministic across calls, and costs
no credits. That endpoint is a second LLM boundary and is treated as principle 7 treats the first:
the exact texts sent, the served model name, the dimension and every vector are recorded, so
everything downstream is a deterministic function of the record. The client reuses `llm.load_key`
and `llm.call_with_backoff` rather than adding to `llm.py`, because that module is a code input to
every protected chunk of the archive and a chunk's provenance should not change because a new
endpoint was added beside it.

Rendering is pure and lives here so the smoke tier can hold the strings to the rules above without
a network. The template is fixed in config and was never tuned: the study reads the bank as
written, not a prompt fitted to the test set.
"""
from __future__ import annotations

import hashlib

import numpy as np


def humanise(name: str) -> str:
    """A class identifier as words: underscores and hyphens become spaces; nothing else changes."""
    return name.replace("_", " ").replace("-", " ").strip()


def render(template: str, modality: str, text: str) -> str:
    return template.format(modality=modality, text=text)


def anchors_of(bank) -> tuple[list[str], dict[str, dict]]:
    """The bank's concept ids in order, and each concept's anchors by level."""
    order = [c["id"] for c in bank.concepts]
    return order, {c["id"]: c["anchors"] for c in bank.concepts}


def describe(bank, levels: dict, template: str) -> str:
    """Committed levels over the bank's concepts, as prose in the bank's own words.

    One renderer for an image's answers and for a class's fingerprint, so that T compares like with
    like. A level that is missing, None or `any` contributes nothing; the rest contribute their
    anchor text, in the bank's concept order, joined as sentences. An image whose every answer is
    missing renders as the modality alone - a real, embeddable string that carries no concept, which
    is the honest representation of an image the model would not describe.
    """
    order, anchors = anchors_of(bank)
    parts = []
    for cid in order:
        level = levels.get(cid)
        if level in (None, "any"):
            continue
        if level not in anchors[cid]:
            raise ValueError(f"{cid}: level {level!r} is not on the scale")
        parts.append(anchors[cid][level]["text"].rstrip(". "))
    return render(template, bank.modality, ". ".join(parts) + ("." if parts else ""))


def name_text(bank, name: str, template: str) -> str:
    """Arm Z's target: the class name under the modality string."""
    return render(template, bank.modality, humanise(name) + ".")


def fingerprint_text(bank, name: str, template: str) -> str:
    """Arm T's target: the class's fingerprint, rendered exactly as an image's answers are."""
    return describe(bank, bank.classes[name]["fingerprint"], template)


def answer_text(bank, row: dict, template: str) -> str:
    """One archived image, rendered exactly as a fingerprint is."""
    return describe(bank, row.get("answers") or {}, template)


def committed_count(bank, levels: dict) -> int:
    order, _ = anchors_of(bank)
    return sum(1 for cid in order if levels.get(cid) not in (None, "any"))


def sha256(texts: list[str]) -> str:
    h = hashlib.sha256()
    for s in texts:
        h.update(s.encode("utf-8")); h.update(b"\x00")
    return h.hexdigest()


def normalise(vectors: np.ndarray) -> np.ndarray:
    """Rows to unit length. A zero row stays zero rather than becoming NaN."""
    array = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(array, axis=-1, keepdims=True)
    safe = np.where(norms > 0, norms, 1.0)
    return np.where(norms > 0, array / safe, 0.0).astype(np.float32)


def cosine_scores(image_vectors: np.ndarray, class_matrix: np.ndarray) -> np.ndarray:
    """(N, K) cosines between unit image vectors and unit class vectors. AUC reads them directly."""
    return normalise(image_vectors) @ normalise(class_matrix).T


def similarity_matrix(class_matrix: np.ndarray) -> np.ndarray:
    """Cosines between the classes' own vectors: a property of the bank, not of any image."""
    unit = normalise(class_matrix)
    return unit @ unit.T


class Embedder:
    """One embedding model on the service, with the settings every call shares.

    Same shape as `llm.Client`, and deliberately not part of it (see the module docstring). The
    served model name and the dimension come back from the first call and are recorded, because
    "qwen3-embedding-4b" is an alias the service could point elsewhere and a vector that does not
    say which model made it cannot be compared with one that does.
    """

    def __init__(self, model: str, base_url: str, key_file: str, batch: int = 256,
                 retries: int = 4, timeout: float = 120.0):
        import openai

        from . import llm

        self.model, self.batch, self.retries = model, int(batch), int(retries)
        self._backoff = llm.call_with_backoff
        self._client = openai.OpenAI(base_url=base_url, api_key=llm.load_key(key_file), timeout=timeout)
        self.served_model: str | None = None
        self.dimension: int | None = None
        self.calls = 0
        self.prompt_tokens = 0

    def embed(self, texts: list[str]) -> np.ndarray:
        """Unit vectors for `texts`, in order, as an (M, D) float32 array."""
        if not texts:
            return np.zeros((0, self.dimension or 1), dtype=np.float32)
        rows: list[list[float]] = []
        for start in range(0, len(texts), self.batch):
            chunk = texts[start:start + self.batch]

            def call():
                return self._client.embeddings.create(model=self.model, input=chunk)

            response, _ = self._backoff(call, attempts=self.retries)
            self.calls += 1
            if response.usage is not None:
                self.prompt_tokens += int(getattr(response.usage, "prompt_tokens", 0) or 0)
            served = getattr(response, "model", None) or self.model
            if self.served_model is None:
                self.served_model = served
            elif served != self.served_model:
                raise RuntimeError(f"the served model changed mid-run: {self.served_model} -> {served}")
            ordered = sorted(response.data, key=lambda d: d.index)
            rows.extend(d.embedding for d in ordered)
        vectors = np.asarray(rows, dtype=np.float32)
        if self.dimension is None:
            self.dimension = int(vectors.shape[1])
        elif vectors.shape[1] != self.dimension:
            raise RuntimeError(f"embedding dimension changed mid-run: {self.dimension} -> {vectors.shape[1]}")
        return normalise(vectors)
