import argparse
import hashlib
import re
import sqlite3
from pathlib import Path

try:
    from .vector_utils import text_to_vector, vector_to_blob
except ImportError:
    from vector_utils import text_to_vector, vector_to_blob


def normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return []

    chunks: list[str] = []
    current = ""
    for p in paragraphs:
        if len(p) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            start = 0
            while start < len(p):
                end = min(start + chunk_size, len(p))
                piece = p[start:end].strip()
                if piece:
                    chunks.append(piece)
                if end == len(p):
                    break
                start = max(end - overlap, start + 1)
            continue

        if not current:
            current = p
            continue

        if len(current) + 2 + len(p) <= chunk_size:
            current += "\n\n" + p
        else:
            chunks.append(current.strip())
            tail = current[-overlap:] if overlap > 0 and len(current) > overlap else ""
            current = (tail + "\n\n" + p).strip() if tail else p

    if current:
        chunks.append(current.strip())

    return [c for c in chunks if c]


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(1024 * 1024)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;
        PRAGMA temp_store = MEMORY;

        CREATE TABLE IF NOT EXISTS documents (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            filename TEXT NOT NULL UNIQUE,
            source_path TEXT NOT NULL,
            file_hash TEXT NOT NULL,
            char_count INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS chunks (
            id INTEGER PRIMARY KEY,
            document_id INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            chunk_text TEXT NOT NULL,
            char_count INTEGER NOT NULL,
            FOREIGN KEY(document_id) REFERENCES documents(id)
        );

        CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);

        CREATE TABLE IF NOT EXISTS chunk_vectors (
            chunk_id INTEGER PRIMARY KEY,
            dim INTEGER NOT NULL,
            vector_dtype TEXT NOT NULL,
            embedding BLOB NOT NULL,
            FOREIGN KEY(chunk_id) REFERENCES chunks(id)
        );

        CREATE INDEX IF NOT EXISTS idx_chunk_vectors_dim ON chunk_vectors(dim);

        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_text,
            title UNINDEXED,
            filename UNINDEXED,
            source_path UNINDEXED,
            chunk_id UNINDEXED,
            content='',
            tokenize='trigram'
        );
        """
    )


def reset_all(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        DROP TABLE IF EXISTS chunks_fts;
        DROP TABLE IF EXISTS chunk_vectors;
        DROP TABLE IF EXISTS chunks;
        DROP TABLE IF EXISTS documents;
        """
    )
    create_schema(conn)


def requires_full_rebuild(conn: sqlite3.Connection) -> bool:
    cols = {row[1] for row in conn.execute("PRAGMA table_info(chunk_vectors)").fetchall()}
    return "vector_dtype" not in cols


def delete_document_content(conn: sqlite3.Connection, document_id: int) -> None:
    chunk_ids = [r[0] for r in conn.execute("SELECT id FROM chunks WHERE document_id = ?", (document_id,)).fetchall()]
    if chunk_ids:
        conn.executemany("DELETE FROM chunk_vectors WHERE chunk_id = ?", [(cid,) for cid in chunk_ids])
        conn.executemany("DELETE FROM chunks_fts WHERE rowid = ?", [(cid,) for cid in chunk_ids])
        conn.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))


def upsert_document(
    conn: sqlite3.Connection,
    filename: str,
    source_path: str,
    title: str,
    file_hash_value: str,
    char_count: int,
) -> int:
    row = conn.execute("SELECT id FROM documents WHERE filename = ?", (filename,)).fetchone()
    if row:
        doc_id = row[0]
        conn.execute(
            """
            UPDATE documents
            SET title = ?, source_path = ?, file_hash = ?, char_count = ?
            WHERE id = ?
            """,
            (title, source_path, file_hash_value, char_count, doc_id),
        )
        return doc_id

    cur = conn.execute(
        """
        INSERT INTO documents(title, filename, source_path, file_hash, char_count)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, filename, source_path, file_hash_value, char_count),
    )
    return cur.lastrowid


def insert_chunks(
    conn: sqlite3.Connection,
    doc_id: int,
    title: str,
    filename: str,
    source_path: str,
    chunks: list[str],
    embed_dim: int,
    vector_dtype: str,
) -> int:
    inserted = 0
    for idx, c in enumerate(chunks):
        cur = conn.execute(
            """
            INSERT INTO chunks(document_id, chunk_index, chunk_text, char_count)
            VALUES (?, ?, ?, ?)
            """,
            (doc_id, idx, c, len(c)),
        )
        chunk_id = cur.lastrowid
        conn.execute(
            """
            INSERT INTO chunks_fts(rowid, chunk_text, title, filename, source_path, chunk_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (chunk_id, c, title, filename, source_path, chunk_id),
        )
        emb = text_to_vector(c, dim=embed_dim)
        conn.execute(
            """
            INSERT INTO chunk_vectors(chunk_id, dim, vector_dtype, embedding)
            VALUES (?, ?, ?, ?)
            """,
            (chunk_id, embed_dim, vector_dtype, sqlite3.Binary(vector_to_blob(emb, dtype=vector_dtype))),
        )
        inserted += 1
    return inserted


def build(
    input_dir: Path,
    db_path: Path,
    chunk_size: int,
    overlap: int,
    embed_dim: int,
    vector_dtype: str,
    full_rebuild: bool,
) -> dict[str, int]:
    txt_files = sorted(input_dir.glob("*.txt"))
    if not txt_files:
        raise RuntimeError(f"no .txt files found in {input_dir}")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    try:
        create_schema(conn)
        if full_rebuild or requires_full_rebuild(conn):
            reset_all(conn)

        existing = {
            row["filename"]: (row["id"], row["file_hash"])
            for row in conn.execute("SELECT id, filename, file_hash FROM documents").fetchall()
        }
        incoming_names = {p.name for p in txt_files}

        stats = {
            "documents_total": 0,
            "documents_updated": 0,
            "documents_skipped": 0,
            "documents_deleted": 0,
            "chunks_total": 0,
        }

        for old_name in set(existing.keys()) - incoming_names:
            old_id = existing[old_name][0]
            delete_document_content(conn, old_id)
            conn.execute("DELETE FROM documents WHERE id = ?", (old_id,))
            stats["documents_deleted"] += 1

        for path in txt_files:
            stats["documents_total"] += 1
            raw = path.read_text(encoding="utf-8", errors="strict")
            text = normalize_text(raw)
            title = path.stem
            doc_hash = file_hash(path)

            old = existing.get(path.name)
            if old and old[1] == doc_hash:
                stats["documents_skipped"] += 1
                continue

            doc_id = upsert_document(
                conn=conn,
                filename=path.name,
                source_path=str(path),
                title=title,
                file_hash_value=doc_hash,
                char_count=len(text),
            )
            delete_document_content(conn, doc_id)

            chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
            if not chunks and text:
                chunks = [text]

            stats["chunks_total"] += insert_chunks(
                conn=conn,
                doc_id=doc_id,
                title=title,
                filename=path.name,
                source_path=str(path),
                chunks=chunks,
                embed_dim=embed_dim,
                vector_dtype=vector_dtype,
            )
            stats["documents_updated"] += 1

        conn.commit()
        return stats
    finally:
        conn.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Build SQLite RAG database from txt files.")
    parser.add_argument("--input-dir", required=True, type=Path, help="Folder containing txt files.")
    parser.add_argument("--db-path", default=Path("rag/rag.db"), type=Path, help="Output sqlite db path.")
    parser.add_argument("--chunk-size", default=800, type=int, help="Chunk size in characters.")
    parser.add_argument("--overlap", default=120, type=int, help="Chunk overlap in characters.")
    parser.add_argument("--embed-dim", default=2048, type=int, help="Vector dimension for each chunk.")
    parser.add_argument(
        "--vector-dtype",
        default="float16",
        choices=["float16", "float32"],
        help="Vector storage dtype. float16 is smaller and cheaper.",
    )
    parser.add_argument("--full-rebuild", action="store_true", help="Force rebuild all documents.")
    args = parser.parse_args()

    if args.overlap >= args.chunk_size:
        raise ValueError("overlap must be smaller than chunk-size")

    stats = build(
        input_dir=args.input_dir,
        db_path=args.db_path,
        chunk_size=args.chunk_size,
        overlap=args.overlap,
        embed_dim=args.embed_dim,
        vector_dtype=args.vector_dtype,
        full_rebuild=args.full_rebuild,
    )
    print(f"db={args.db_path}")
    print(f"documents_total={stats['documents_total']}")
    print(f"documents_updated={stats['documents_updated']}")
    print(f"documents_skipped={stats['documents_skipped']}")
    print(f"documents_deleted={stats['documents_deleted']}")
    print(f"chunks_total={stats['chunks_total']}")
    print(f"vector_dim={args.embed_dim}")
    print(f"vector_dtype={args.vector_dtype}")


if __name__ == "__main__":
    main()
