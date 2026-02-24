import argparse
import sqlite3
from pathlib import Path
from typing import Any

try:
    from .vector_utils import blob_to_vector, dot, text_to_vector
except ImportError:
    from vector_utils import blob_to_vector, dot, text_to_vector
try:
    import numpy as np
except Exception:
    np = None


def _connect(db_path: Path | str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA query_only = ON")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def query(db_path: Path | str, q: str, top_k: int) -> list[sqlite3.Row]:
    conn = _connect(db_path)
    try:
        fts_rows: list[sqlite3.Row] = []
        if len(q.strip()) >= 3:
            q_escaped = q.replace('"', '""')
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

        like_q = f"%{q}%"
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


def keyword_candidate_ids(db_path: Path | str, q: str, limit: int = 300) -> list[int]:
    conn = _connect(db_path)
    try:
        ids: list[int] = []
        if len(q.strip()) >= 3:
            q_escaped = q.replace('"', '""')
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
            like_q = f"%{q}%"
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

        # Deduplicate while keeping order.
        return list(dict.fromkeys(ids))
    finally:
        conn.close()


def query_vector(
    db_path: Path | str,
    q: str,
    top_k: int,
    dim: int = 2048,
    candidate_chunk_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    qv = text_to_vector(q, dim=dim)
    conn = _connect(db_path)
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
            params = [dim, *candidate_chunk_ids]
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
                (dim,),
            ).fetchall()
    finally:
        conn.close()

    scored = []
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
                v = np.frombuffer(r["embedding"], dtype=src_dtype, count=dim).astype(np.float32, copy=False)
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Query SQLite RAG db.")
    parser.add_argument("--db-path", default=Path("rag/rag.db"), type=Path)
    parser.add_argument("--query", required=True, type=str)
    parser.add_argument("--top-k", default=5, type=int)
    parser.add_argument(
        "--mode",
        default="hybrid",
        choices=["hybrid", "keyword", "vector"],
        help="keyword=FTS/LIKE, vector=similarity, hybrid=keyword first then vector fallback",
    )
    parser.add_argument("--embed-dim", default=2048, type=int)
    parser.add_argument(
        "--vector-candidate-limit",
        default=300,
        type=int,
        help="Use keyword candidates to shrink vector search scope in vector mode.",
    )
    args = parser.parse_args()

    rows: list[Any] = []
    if args.mode in ("keyword", "hybrid"):
        rows = query(args.db_path, args.query, args.top_k)
    if (not rows) and args.mode in ("vector", "hybrid"):
        candidates = None
        if args.vector_candidate_limit > 0:
            candidates = keyword_candidate_ids(args.db_path, args.query, limit=args.vector_candidate_limit)
        rows = query_vector(
            args.db_path,
            args.query,
            args.top_k,
            dim=args.embed_dim,
            candidate_chunk_ids=candidates,
        )

    if not rows:
        print("no results")
        return

    for i, row in enumerate(rows, start=1):
        preview = row["chunk_text"].replace("\n", " ")
        if len(preview) > 200:
            preview = preview[:200] + "..."
        print(f"[{i}] score={row['score']:.4f} file={row['filename']} chunk={row['chunk_index']}")
        print(preview)
        print()


if __name__ == "__main__":
    main()
