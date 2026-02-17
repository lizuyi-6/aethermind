import os
import shutil
import tempfile

from file_registry_service import FileRegistry


def test_register_and_get_file_record():
    tmp = tempfile.mkdtemp()
    try:
        db_path = os.path.join(tmp, "meta.db")
        file_path = os.path.join(tmp, "sample.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("hello")

        reg = FileRegistry(db_path)
        rec = reg.register_file(
            stored_path=file_path,
            kind="upload",
            origin_name="origin.txt",
            source_ref="s1",
            extra={"k": "v"},
        )
        assert rec["file_id"]
        got = reg.get_file(rec["file_id"])
        assert got is not None
        assert got["kind"] == "upload"
        assert got["origin_name"] == "origin.txt"
        assert got["source_ref"] == "s1"
        del reg
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_register_same_path_updates_record():
    tmp = tempfile.mkdtemp()
    try:
        db_path = os.path.join(tmp, "meta.db")
        file_path = os.path.join(tmp, "sample.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("v1")

        reg = FileRegistry(db_path)
        rec1 = reg.register_file(file_path, kind="upload", origin_name="a.txt")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write("v2")
        rec2 = reg.register_file(file_path, kind="report_md", origin_name="b.md")
        assert rec1["file_id"] == rec2["file_id"]
        got = reg.get_file(rec1["file_id"])
        assert got["kind"] == "report_md"
        assert got["origin_name"] == "b.md"
        del reg
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
