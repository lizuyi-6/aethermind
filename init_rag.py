#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SQLite-RAG 初始化与自检脚本。
当前项目仅使用迁移后的 SQLite 向量库。
"""

import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


def test_sqlite_db(db_path: Path) -> bool:
    print("=" * 60)
    print("检查 SQLite RAG 数据库...")
    print("=" * 60)
    if not db_path.exists():
        print(f"✗ 数据库不存在: {db_path}")
        return False
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        required_tables = ["documents", "chunks", "chunk_vectors", "chunks_fts"]
        for t in required_tables:
            cur.execute(f"SELECT count(*) FROM {t}")
            cnt = cur.fetchone()[0]
            print(f"[OK] {t}: {cnt}")
        conn.close()
        return True
    except Exception as e:
        print(f"[FAIL] 数据库结构检查失败: {e}")
        return False


def test_retrieval(db_path: Path, embed_dim: int) -> bool:
    print("\n" + "=" * 60)
    print("检查检索能力...")
    print("=" * 60)
    try:
        from sqlite_rag_adapter import SQLiteRAGRetriever

        retriever = SQLiteRAGRetriever(
            db_path=str(db_path),
            embed_dim=embed_dim,
            top_k=3,
            vector_candidate_limit=200,
        )
        query = "行政诉讼法 受理 条件"
        results = retriever.retrieve(query, strategy="hybrid")
        print(f"[OK] 查询: {query}")
        print(f"[OK] 命中数量: {len(results)}")
        if results:
            top = results[0]
            print(f"[OK] Top1 来源: {top['payload'].get('source', '')}")
            return True
        print("[FAIL] 检索结果为空")
        return False
    except Exception as e:
        print(f"[FAIL] 检索测试失败: {e}")
        return False


def test_agent_init() -> bool:
    print("\n" + "=" * 60)
    print("检查 Agent RAG 初始化...")
    print("=" * 60)
    try:
        from config import Config
        from agent import IntelligentAgent
        from sqlite_rag_adapter import SQLiteRAGAugmenter

        cfg = Config()
        agent = IntelligentAgent(cfg, enable_rag=True)
        agent._init_rag()
        if agent.rag_augmenter and isinstance(agent.rag_augmenter, SQLiteRAGAugmenter):
            print("[OK] Agent 已接入 SQLiteRAGAugmenter")
            return True
        print("[FAIL] Agent 未接入 SQLiteRAGAugmenter")
        return False
    except Exception as e:
        print(f"[FAIL] Agent 初始化测试失败: {e}")
        return False


def main() -> int:
    db_path = Path(os.getenv("SQLITE_RAG_DB_PATH", "knowledge_base/sqlite_rag.db"))
    embed_dim = int(os.getenv("SQLITE_RAG_EMBED_DIM", "2048"))

    checks = {
        "SQLite 数据库": test_sqlite_db(db_path),
        "检索功能": test_retrieval(db_path, embed_dim),
        "Agent 接入": test_agent_init(),
    }

    print("\n" + "=" * 60)
    print("测试总结")
    print("=" * 60)
    for k, ok in checks.items():
        print(f"{k}: {'[PASS]' if ok else '[FAIL]'}")
    all_ok = all(checks.values())
    if all_ok:
        print("\n[DONE] SQLite-RAG 已就绪。")
    else:
        print("\n[WARN] SQLite-RAG 检查未全部通过。")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
