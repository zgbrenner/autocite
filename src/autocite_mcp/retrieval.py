from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, Sequence


@dataclass(frozen=True)
class RuleChunk:
    chunk_id: str
    text: str
    source_filename: str
    heading: str
    rule_family: str
    mode: str
    source_type: str
    jurisdiction: str
    revision_date: str
    license: str
    redistribution_allowed: bool


@dataclass(frozen=True)
class RetrievalQuery:
    text: str
    mode: str | None = None
    source_type: str | None = None
    rule_family: str | None = None
    jurisdiction: str | None = None
    revision_date: str | None = None


@dataclass(frozen=True)
class RetrievedRuleChunk:
    chunk: RuleChunk
    score: float
    ranker: str
    provenance: str = "retrieved_reference_material"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _stable_chunk_id(filename: str, heading: str, text: str) -> str:
    value = "\x1f".join((filename, heading, text.strip()))
    return "rule:" + hashlib.sha256(value.encode()).hexdigest()[:20]


def _split_markdown(text: str) -> list[tuple[str, str]]:
    matches = list(re.finditer(r"^#{1,6}\s+(.+?)\s*$", text, re.M))
    chunks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        body = text[match.end() : end].strip()
        if body:
            chunks.append((match.group(1).strip(), body))
    return chunks


@dataclass(frozen=True)
class RuleLibrary:
    chunks: tuple[RuleChunk, ...]
    schema_version: str = "1.0"

    @classmethod
    def builtin(cls) -> "RuleLibrary":
        root = Path(__file__).with_name("reference_library")
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        return cls._from_manifest(
            manifest,
            lambda name: (root / name).read_text(encoding="utf-8"),
        )

    @classmethod
    def from_directory(cls, directory: Path) -> "RuleLibrary":
        root = Path(directory)
        manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
        return cls._from_manifest(
            manifest,
            lambda name: (root / name).read_text(encoding="utf-8"),
        )

    @classmethod
    def _from_manifest(cls, manifest: dict[str, Any], reader: Any) -> "RuleLibrary":
        chunks: list[RuleChunk] = []
        for source in manifest.get("sources", []):
            if not source.get("included") or not source.get("redistribution_allowed"):
                continue
            license_name = str(source.get("license") or "").strip()
            if not license_name or license_name.casefold() == "proprietary":
                continue
            filename = str(source["filename"])
            for heading, body in _split_markdown(reader(filename)):
                chunks.append(
                    RuleChunk(
                        _stable_chunk_id(filename, heading, body),
                        body,
                        filename,
                        heading,
                        str(source.get("rule_family") or "unclassified"),
                        str(source.get("mode") or "both"),
                        str(source.get("source_type") or "all"),
                        str(source.get("jurisdiction") or "general"),
                        str(source.get("revision_date") or "unknown"),
                        license_name,
                        True,
                    )
                )
        return cls(tuple(sorted(chunks, key=lambda item: item.chunk_id)), str(manifest.get("schema_version") or "1.0"))

    def save_index(self, path: Path) -> None:
        payload = {
            "schema_version": self.schema_version,
            "chunks": [asdict(item) for item in self.chunks],
        }
        Path(path).write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load_index(cls, path: Path) -> "RuleLibrary":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            tuple(RuleChunk(**item) for item in payload["chunks"]),
            str(payload["schema_version"]),
        )


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.casefold()))


# deterministic_rules.RULE_SPECS labels each rule with a fine-grained
# rule_family_reference (e.g. "short forms: Id.") from a taxonomy the
# reference_library manifest's rule_family field only groups into three
# broad topic buckets. Without this, a caller who took rule_family_
# reference straight from a rule_findings entry (the natural "explain this
# further" workflow) silently got zero results for most of the nine
# possible values, with no error or hint that the vocabulary differed.
# "pincites and quotations" has no reference_library content and is left
# unmapped -- an empty result for it is accurate, not a vocabulary bug.
_RULE_FAMILY_ALIASES = {
    "short forms: id.": "short_forms",
    "short forms: cases": "short_forms",
    "short forms: statutes and regulations": "short_forms",
    "supra and hereinafter": "short_forms",
    "signals": "signals_parentheticals",
    "parentheticals": "signals_parentheticals",
    "citation groups and ordering": "signals_parentheticals",
    "internet sources": "internet_sources",
}


def _normalize_rule_family(rule_family: str | None) -> str | None:
    if rule_family is None:
        return None
    return _RULE_FAMILY_ALIASES.get(rule_family.strip().lower(), rule_family)


def _metadata_match(chunk: RuleChunk, query: RetrievalQuery) -> bool:
    if query.mode and chunk.mode not in {"both", query.mode}:
        return False
    if query.source_type and chunk.source_type not in {"all", query.source_type}:
        return False
    if query.rule_family and chunk.rule_family != _normalize_rule_family(query.rule_family):
        return False
    if query.jurisdiction and chunk.jurisdiction not in {"general", "general_us", query.jurisdiction}:
        return False
    if query.revision_date and chunk.revision_date != query.revision_date:
        return False
    return True


class RuleRetriever(Protocol):
    def retrieve(self, query: RetrievalQuery, *, top_k: int = 3) -> list[RetrievedRuleChunk]: ...


class LexicalRuleRetriever:
    def __init__(self, library: RuleLibrary) -> None:
        self.library = library

    def retrieve(self, query: RetrievalQuery, *, top_k: int = 3) -> list[RetrievedRuleChunk]:
        if top_k <= 0:
            raise ValueError("top_k must be positive")
        query_tokens = _tokens(query.text)
        candidates = [item for item in self.library.chunks if _metadata_match(item, query)]
        ranked: list[RetrievedRuleChunk] = []
        for chunk in candidates:
            chunk_tokens = _tokens(f"{chunk.heading} {chunk.text}")
            overlap = len(query_tokens & chunk_tokens)
            score = overlap / math.sqrt(max(1, len(query_tokens) * len(chunk_tokens)))
            ranked.append(RetrievedRuleChunk(chunk, round(score, 8), "deterministic_lexical"))
        return sorted(ranked, key=lambda item: (-item.score, item.chunk.chunk_id))[:top_k]


class LocalEmbeddingRuleRetriever:
    """Optional local bge-small retriever; loading is lazy and offline by default."""

    def __init__(self, library: RuleLibrary, model_path: str = "BAAI/bge-small-en-v1.5", *, offline_only: bool = True) -> None:
        self.library = library
        self.model_path = model_path
        self.offline_only = offline_only
        self._model: Any = None

    def _load(self) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("local embeddings require the optional 'retrieval' dependencies") from exc
            self._model = SentenceTransformer(
                self.model_path,
                local_files_only=self.offline_only,
            )
        return self._model

    def retrieve(self, query: RetrievalQuery, *, top_k: int = 3) -> list[RetrievedRuleChunk]:
        candidates = [item for item in self.library.chunks if _metadata_match(item, query)]
        if not candidates:
            return []
        model = self._load()
        vectors = model.encode([query.text] + [item.text for item in candidates], normalize_embeddings=True)
        ranked = [
            RetrievedRuleChunk(chunk, float(vectors[0] @ vectors[index]), "local_bge_small")
            for index, chunk in enumerate(candidates, start=1)
        ]
        return sorted(ranked, key=lambda item: (-item.score, item.chunk.chunk_id))[:top_k]


class LocalPassageEmbeddingBackend:
    """Lazy-loaded, offline-only sentence-transformers bi-encoder for candidate-passage scoring.

    Mirrors ``LocalEmbeddingRuleRetriever``'s lazy-load/offline-only pattern and default model.
    Used by ``evidence.HybridPassageScorer``; consumers there catch any error this raises (import
    failure, no cached model under offline-only load, etc.) and fall back to lexical scoring.
    """

    def __init__(self, model_path: str = "BAAI/bge-small-en-v1.5", *, offline_only: bool = True) -> None:
        self.model_path = model_path
        self.offline_only = offline_only
        self._model: Any = None

    def encode(self, texts: Sequence[str]) -> Any:
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise RuntimeError("hybrid passage scoring requires the optional 'retrieval' dependencies") from exc
            self._model = SentenceTransformer(
                self.model_path,
                local_files_only=self.offline_only,
            )
        return self._model.encode(list(texts), normalize_embeddings=True)


class CandidateReranker(Protocol):
    def rerank(self, query: str, candidates: Sequence[RetrievedRuleChunk]) -> list[RetrievedRuleChunk]: ...


class LocalCrossEncoderReranker:
    def __init__(self, model_path: str = "cross-encoder/ms-marco-MiniLM-L6-v2", *, offline_only: bool = True) -> None:
        self.model_path = model_path
        self.offline_only = offline_only
        self._model: Any = None

    def rerank(self, query: str, candidates: Sequence[RetrievedRuleChunk]) -> list[RetrievedRuleChunk]:
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
            except ImportError as exc:
                raise RuntimeError("reranking requires the optional 'retrieval-reranker' dependencies") from exc
            self._model = CrossEncoder(self.model_path, local_files_only=self.offline_only)
        scores = self._model.predict([(query, item.chunk.text) for item in candidates])
        reranked = [
            RetrievedRuleChunk(item.chunk, float(score), "local_cross_encoder")
            for item, score in zip(candidates, scores)
        ]
        return sorted(reranked, key=lambda item: (-item.score, item.chunk.chunk_id))


def should_retrieve(
    *,
    review_required: bool = False,
    ambiguous_antecedent: bool = False,
    multiple_rule_families: bool = False,
    mode_uncertain: bool = False,
    uncommon_source_type: bool = False,
    signal_or_parenthetical_review: bool = False,
    user_requested_explanation: bool = False,
    model_lacks_context: bool = False,
    confidence: float = 1.0,
    threshold: float = 0.7,
) -> bool:
    return any(
        (
            review_required,
            ambiguous_antecedent,
            multiple_rule_families,
            mode_uncertain,
            uncommon_source_type,
            signal_or_parenthetical_review,
            user_requested_explanation,
            model_lacks_context,
            confidence < threshold,
        )
    )


class DisabledEntityExtractor:
    enabled = False

    def extract(self, text: str) -> list[dict[str, Any]]:
        return []


class ExperimentalGLiNEREntityExtractor:
    """Evaluation-only local entity adapter; never selected by default."""

    enabled = True

    def __init__(self, model_path: str = "urchade/gliner_small-v2.1", *, offline_only: bool = True) -> None:
        self.model_path = model_path
        self.offline_only = offline_only
        self._model: Any = None

    def extract(self, text: str) -> list[dict[str, Any]]:
        if self._model is None:
            try:
                from gliner import GLiNER
            except ImportError as exc:
                raise RuntimeError("GLiNER requires the optional experimental-gliner dependencies") from exc
            self._model = GLiNER.from_pretrained(
                self.model_path,
                local_files_only=self.offline_only,
            )
        return list(
            self._model.predict_entities(
                text,
                ["author", "document title", "institution", "source type"],
            )
        )
