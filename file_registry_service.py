import hashlib
import json
import mimetypes
import os
import secrets
import sqlite3
import threading
import time
from datetime import datetime
from typing import Any, Dict, Optional


_CROCKFORD32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"


def _encode_base32(value: int, length: int) -> str:
    chars = ["0"] * length
    for i in range(length - 1, -1, -1):
        chars[i] = _CROCKFORD32[value & 31]
        value >>= 5
    return "".join(chars)


def generate_ulid() -> str:
    ts_ms = int(time.time() * 1000)
    rand_80 = secrets.randbits(80)
    return f"{_encode_base32(ts_ms, 10)}{_encode_base32(rand_80, 16)}"


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class FileRegistry:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._lock = threading.RLock()
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS file_registry (
                    file_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL,
                    origin_name TEXT NOT NULL,
                    stored_name TEXT NOT NULL,
                    stored_path TEXT NOT NULL UNIQUE,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL,
                    sha256 TEXT NOT NULL,
                    source_ref TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    extra_json TEXT NOT NULL DEFAULT '{}'
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_file_registry_kind_created ON file_registry(kind, created_at DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_file_registry_sha256 ON file_registry(sha256)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_file_registry_source_ref ON file_registry(source_ref)"
            )
            conn.commit()

    def register_file(
        self,
        stored_path: str,
        kind: str,
        origin_name: Optional[str] = None,
        source_ref: str = "",
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        if not os.path.isfile(stored_path):
            raise FileNotFoundError(stored_path)
        abs_path = os.path.abspath(stored_path)
        stored_name = os.path.basename(abs_path)
        origin_name = (origin_name or stored_name).strip() or stored_name
        mime = mimetypes.guess_type(abs_path)[0] or "application/octet-stream"
        size = int(os.path.getsize(abs_path))
        checksum = sha256_file(abs_path)
        now = datetime.now().isoformat()
        extra_json = json.dumps(extra or {}, ensure_ascii=False)

        with self._lock:
            with self._connect() as conn:
                row = conn.execute(
                    "SELECT * FROM file_registry WHERE stored_path = ?",
                    (abs_path,),
                ).fetchone()
                if row:
                    conn.execute(
                        """
                        UPDATE file_registry
                        SET kind=?, origin_name=?, mime_type=?, size_bytes=?, sha256=?, source_ref=?, status='active', updated_at=?, extra_json=?
                        WHERE file_id=?
                        """,
                        (
                            kind,
                            origin_name,
                            mime,
                            size,
                            checksum,
                            source_ref or "",
                            now,
                            extra_json,
                            row["file_id"],
                        ),
                    )
                    conn.commit()
                    updated = dict(row)
                    updated.update(
                        {
                            "kind": kind,
                            "origin_name": origin_name,
                            "mime_type": mime,
                            "size_bytes": size,
                            "sha256": checksum,
                            "source_ref": source_ref or "",
                            "status": "active",
                            "updated_at": now,
                            "extra_json": extra_json,
                        }
                    )
                    return updated

                file_id = generate_ulid()
                conn.execute(
                    """
                    INSERT INTO file_registry(
                        file_id, kind, origin_name, stored_name, stored_path, mime_type, size_bytes, sha256, source_ref, status, created_at, updated_at, extra_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
                    """,
                    (
                        file_id,
                        kind,
                        origin_name,
                        stored_name,
                        abs_path,
                        mime,
                        size,
                        checksum,
                        source_ref or "",
                        now,
                        now,
                        extra_json,
                    ),
                )
                conn.commit()
                return {
                    "file_id": file_id,
                    "kind": kind,
                    "origin_name": origin_name,
                    "stored_name": stored_name,
                    "stored_path": abs_path,
                    "mime_type": mime,
                    "size_bytes": size,
                    "sha256": checksum,
                    "source_ref": source_ref or "",
                    "status": "active",
                    "created_at": now,
                    "updated_at": now,
                    "extra_json": extra_json,
                }

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM file_registry WHERE file_id = ?",
                (file_id,),
            ).fetchone()
            return dict(row) if row else None

    def mark_deleted(self, file_id: str) -> None:
        now = datetime.now().isoformat()
        with self._lock:
            with self._connect() as conn:
                conn.execute(
                    "UPDATE file_registry SET status='deleted', updated_at=? WHERE file_id=?",
                    (now, file_id),
                )
                conn.commit()

