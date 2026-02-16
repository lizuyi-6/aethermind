"""
SQLite RAG adapter for integrating external SQLite vector databases.
Compatible with the Chinese law RAG project schema.
"""

from __future__ import annotations

import hashlib
import math
import sqlite3
import struct
from array import array
from pathlib import Path
from typing import Any, Optional

try:
    import numpy as np
except Exception:  # pragma: no cover
    np = None


def _iter_char_ngrams(text: str, n: int = 3):
    compact = "".join(ch for ch in text if not ch.isspace())
    if not compact:
        return
    if len(compact) < n:
        yield compact
        return
    for i in range(0, len(compact) - n + 1):
        yield compact[i : i + n]


def text_to_vector(text: str, dim: int = 2048) -> list[float]:
    vec = [0.0] * dim
    for gram in _iter_char_ngrams(text, n=3):
        digest = hashlib.sha256(gram.encode("utf-8")).digest()
        idx = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if (digest[4] & 1) == 0 else -1.0
        weight = 1.0 + (digest[5] / 255.0) * 0.25
        vec[idx] += sign * weight
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        inv = 1.0 / norm
        vec = [v * inv for v in vec]
    return vec


def blob_to_vector(blob: bytes, dtype: str = "float16") -> list[float]:
    if dtype == "float32":
        arr = array("f")
        arr.frombytes(blob)
        return arr.tolist()
    if dtype == "float16":
        count = len(blob) // 2
        return list(struct.unpack("<" + ("e" * count), blob))
    raise ValueError(f"unsupported vector dtype: {dtype}")


def dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


class SQLiteRAGRetriever:
    def __init__(
        self,
        db_path: str,
        embed_dim: int = 2048,
        top_k: int = 5,
        vector_candidate_limit: int = 300,
    ):
        self.db_path = db_path
        self.embed_dim = embed_dim
        self.top_k = top_k
        self.vector_candidate_limit = vector_candidate_limit

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    def _keyword_search(self, query: str, top_k: int) -> list[sqlite3.Row]:
        conn = self._connect()
        try:
            fts_rows: list[sqlite3.Row] = []
            if len(query.strip()) >= 2:
                q_escaped = query.replace('"', '""')
                fts_query = f'"{q_escaped}"'
                try:
                    fts_rows = conn.execute(
                        """
                        SELECT
                            c.id AS chunk_id,
                            d.title,
                            d.filename,
                            c.chunk_index,
                            c.chunk_text,
                            bm25(chunks_fts) AS score
                        FROM chunks_fts
                        JOIN chunks c ON c.id = chunks_fts.rowid
                        JOIN documents d ON d.id = c.document_id
                        WHERE chunks_fts MATCH ?
                        ORDER BY score
                        LIMIT ?
                        """,
                        (fts_query, top_k),
                    ).fetchall()
                except sqlite3.OperationalError:
                    fts_rows = []

            if fts_rows:
                return fts_rows

            like_q = f"%{query}%"
            return conn.execute(
                """
                SELECT
                    c.id AS chunk_id,
                    d.title,
                    d.filename,
                    c.chunk_index,
                    c.chunk_text,
                    0.0 AS score
                FROM chunks c
                JOIN documents d ON d.id = c.document_id
                WHERE c.chunk_text LIKE ?
                LIMIT ?
                """,
                (like_q, top_k),
            ).fetchall()
        finally:
            conn.close()

    def _keyword_candidate_ids(self, query: str, limit: int = 300) -> list[int]:
        conn = self._connect()
        try:
            ids: list[int] = []
            if len(query.strip()) >= 2:
                q_escaped = query.replace('"', '""')
                fts_query = f'"{q_escaped}"'
                try:
                    rows = conn.execute(
                        """
                        SELECT rowid
                        FROM chunks_fts
                        WHERE chunks_fts MATCH ?
                        LIMIT ?
                        """,
                        (fts_query, limit),
                    ).fetchall()
                    ids.extend([r[0] for r in rows])
                except sqlite3.OperationalError:
                    pass

            if len(ids) < limit:
                like_q = f"%{query}%"
                rows = conn.execute(
                    """
                    SELECT c.id
                    FROM chunks c
                    WHERE c.chunk_text LIKE ?
                    LIMIT ?
                    """,
                    (like_q, limit - len(ids)),
                ).fetchall()
                ids.extend([r[0] for r in rows])
            return list(dict.fromkeys(ids))
        finally:
            conn.close()

    def _vector_search(
        self, query: str, top_k: int, candidate_chunk_ids: Optional[list[int]] = None
    ) -> list[dict[str, Any]]:
        qv = text_to_vector(query, dim=self.embed_dim)
        conn = self._connect()
        try:
            if candidate_chunk_ids:
                placeholders = ",".join("?" for _ in candidate_chunk_ids)
                sql = f"""
                    SELECT
                        c.id AS chunk_id,
                        d.title,
                        d.filename,
                        c.chunk_index,
                        c.chunk_text,
                        v.vector_dtype,
                        v.embedding
                    FROM chunk_vectors v
                    JOIN chunks c ON c.id = v.chunk_id
                    JOIN documents d ON d.id = c.document_id
                    WHERE v.dim = ? AND c.id IN ({placeholders})
                """
                params = [self.embed_dim, *candidate_chunk_ids]
                rows = conn.execute(sql, params).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT
                        c.id AS chunk_id,
                        d.title,
                        d.filename,
                        c.chunk_index,
                        c.chunk_text,
                        v.vector_dtype,
                        v.embedding
                    FROM chunk_vectors v
                    JOIN chunks c ON c.id = v.chunk_id
                    JOIN documents d ON d.id = c.document_id
                    WHERE v.dim = ?
                    """,
                    (self.embed_dim,),
                ).fetchall()
        finally:
            conn.close()

        scored: list[dict[str, Any]] = []
        if np is not None and rows:
            q_np = np.asarray(qv, dtype=np.float32)
            groups: dict[str, list[sqlite3.Row]] = {"float16": [], "float32": []}
            for r in rows:
                dtype = r["vector_dtype"] if "vector_dtype" in r.keys() else "float32"
                groups["float16" if dtype == "float16" else "float32"].append(r)
            for dtype, grows in groups.items():
                if not grows:
                    continue
                src_dtype = np.float16 if dtype == "float16" else np.float32
                vecs = []
                for r in grows:
                    v = np.frombuffer(
                        r["embedding"], dtype=src_dtype, count=self.embed_dim
                    ).astype(np.float32, copy=False)
                    vecs.append(v)
                mat = np.vstack(vecs)
                scores = mat @ q_np
                for r, s in zip(grows, scores):
                    scored.append(
                        {
                            "chunk_id": r["chunk_id"],
                            "title": r["title"],
                            "filename": r["filename"],
                            "chunk_index": r["chunk_index"],
                            "chunk_text": r["chunk_text"],
                            "score": float(s),
                        }
                    )
        else:
            for r in rows:
                dtype = r["vector_dtype"] if "vector_dtype" in r.keys() else "float32"
                cv = blob_to_vector(r["embedding"], dtype=dtype)
                score = dot(qv, cv)
                scored.append(
                    {
                        "chunk_id": r["chunk_id"],
                        "title": r["title"],
                        "filename": r["filename"],
                        "chunk_index": r["chunk_index"],
                        "chunk_text": r["chunk_text"],
                        "score": score,
                    }
                )
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    def retrieve(
        self,
        query: str,
        strategy: str = "hybrid",
        category: Optional[str] = None,
        top_k: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        _ = category
        top_k = top_k or self.top_k
        raw_results: list[Any] = []
        used_keyword_results = False
        if strategy in ("keyword", "hybrid"):
            raw_results = self._keyword_search(query, top_k=top_k)
            used_keyword_results = bool(raw_results)
        if (not raw_results) and strategy in ("vector", "hybrid"):
            candidates = None
            if self.vector_candidate_limit > 0:
                candidates = self._keyword_candidate_ids(
                    query, limit=self.vector_candidate_limit
                )
            raw_results = self._vector_search(
                query, top_k=top_k, candidate_chunk_ids=candidates
            )
            used_keyword_results = False

        # Normalize relevance scores to 0..1 for UI consistency.
        # Keyword branch uses bm25-like ranking where smaller is better (often negative),
        # while vector branch already treats larger as better.
        raw_scores = []
        for r in raw_results:
            row = dict(r) if not isinstance(r, dict) else r
            raw_scores.append(float(row.get("score", 0.0)))
        min_score = min(raw_scores) if raw_scores else 0.0
        max_score = max(raw_scores) if raw_scores else 0.0
        use_keyword_norm = used_keyword_results and len(raw_results) > 0

        normalized = []
        for idx, r in enumerate(raw_results):
            row = dict(r) if not isinstance(r, dict) else r
            score = float(row.get("score", 0.0))
            if use_keyword_norm:
                # bm25: smaller is better. Map to [0,1], higher is better.
                span = max_score - min_score
                if span > 1e-12:
                    score = (max_score - score) / span
                else:
                    # Degenerate case: identical scores; keep rank signal.
                    score = 1.0 - (idx / max(1, len(raw_results)))
            else:
                # Vector similarity might be in [-1,1] or other small ranges.
                # Clamp to [0,1] for stable frontend display.
                score = max(0.0, min(1.0, score))
            normalized.append(
                {
                    "score": float(score),
                    "payload": {
                        "title": row.get("title", ""),
                        "source": row.get("filename", ""),
                        "content": row.get("chunk_text", ""),
                        "category": row.get("category", "general") or "general",
                        "chunk_index": row.get("chunk_index", 0),
                    },
                }
            )
        requested_category = (category or "").strip()
        if requested_category and requested_category.lower() not in ("all", "全部"):
            normalized = [
                item
                for item in normalized
                if str(item.get("payload", {}).get("category", "")).strip() == requested_category
            ]
        return normalized

    def format_context(self, results: list[dict[str, Any]], max_length: int = 4500) -> str:
        context_parts = []
        current_length = 0
        for i, result in enumerate(results, start=1):
            title = result["payload"].get("title", "Untitled")
            content = result["payload"].get("content", "")
            score = result["score"]
            source = result["payload"].get("source", "")
            if len(content) > 500:
                content = content[:500] + "..."
            part = f"""
【参考文档{i}】
标题: {title}
相似度: {score:.3f}
来源: {source}
内容: {content}
"""
            if current_length + len(part) > max_length:
                break
            context_parts.append(part)
            current_length += len(part)
        return "\n".join(context_parts)


class SQLiteRAGAugmenter:
    def __init__(self, retriever: SQLiteRAGRetriever):
        self.retriever = retriever

    def augment_with_sources(
        self, query: str, strategy: str = "hybrid", category: Optional[str] = None
    ) -> dict[str, Any]:
        results = self.retriever.retrieve(query, strategy=strategy, category=category)
        context = self.retriever.format_context(results)

        sources = []
        seen_sources = set()
        for result in results:
            source = result["payload"].get("source", "Unknown")
            title = result["payload"].get("title", "Untitled")
            content = result["payload"].get("content", "") or ""
            category = result["payload"].get("category", "general") or "general"
            source_key = f"{source} - {title}"
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            compact_preview = " ".join(str(content).split())
            sources.append(
                {
                    "title": title,
                    "source": source,
                    "score": result["score"],
                    "similarity": result["score"],
                    "category": category,
                    "content_preview": compact_preview[:220],
                    "preview": compact_preview[:220],
                }
            )

        augmented_prompt = f"""
参考以下文档内容回答用户问题：

{context}

用户问题: {query}

请基于上述参考文档内容回答问题。如果参考文档中没有相关信息，请明确说明。
"""
        return {
            "augmented_prompt": augmented_prompt,
            "sources": sources,
            "retrieval_metadata": {
                "num_results": len(results),
                "strategy": strategy,
                "category": category,
                "db_path": str(self.retriever.db_path),
            },
        }
