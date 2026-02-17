import argparse
import os
import sys

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from file_registry_service import FileRegistry  # noqa: E402


def detect_kind(folder_name: str, filename: str) -> str:
    lower = filename.lower()
    if folder_name == "uploads":
        return "upload"
    if folder_name == "reports":
        if lower.endswith(".md"):
            return "report_md"
        if lower.endswith(".pdf"):
            return "report_pdf"
        return "rag_export" if lower.endswith(".json") else "report_md"
    return "upload"


def main():
    parser = argparse.ArgumentParser(description="Backfill existing uploads/reports into file registry.")
    parser.add_argument("--db", default=os.path.join(ROOT_DIR, "db", "app_meta.db"))
    parser.add_argument("--uploads", default=os.path.join(ROOT_DIR, "uploads"))
    parser.add_argument("--reports", default=os.path.join(ROOT_DIR, "reports"))
    args = parser.parse_args()

    reg = FileRegistry(args.db)
    targets = [("uploads", args.uploads), ("reports", args.reports)]
    total = 0
    ok = 0
    fail = 0

    for folder_name, folder_path in targets:
        if not os.path.isdir(folder_path):
            continue
        for name in os.listdir(folder_path):
            path = os.path.join(folder_path, name)
            if not os.path.isfile(path):
                continue
            total += 1
            try:
                kind = detect_kind(folder_name, name)
                reg.register_file(
                    stored_path=path,
                    kind=kind,
                    origin_name=name,
                    source_ref="backfill",
                    extra={"backfill": True, "folder": folder_name},
                )
                ok += 1
            except Exception as exc:
                fail += 1
                print(f"[FAIL] {path}: {exc}")

    print(f"Backfill done. total={total}, success={ok}, failed={fail}, db={args.db}")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
