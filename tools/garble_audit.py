import argparse
import json
import os
import re
from pathlib import Path

TEXT_EXTS = {
    '.py', '.js', '.html', '.css', '.md', '.txt', '.json', '.wxml', '.wxss'
}
EXCLUDE_DIRS = {
    '.git', '__pycache__', '_cleanup_archive', 'reports', '.venv', 'venv', 'node_modules', 'tools'
}
EXCLUDE_FILES = {'runtime_state.json'}

# Common mojibake chars from UTF-8<->GBK confusion in this repo.
GARBLE_MARKERS = set('鍙鏄鐨绗浠鏈寮閰楠鑾濡璇鏂澶勬洿绔犺妭銆锛寤娴嬭瘉瀛楀彇浣跨敤鏍鍖犲壊鎺掕穭鐣坓€')


def should_scan(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_EXTS:
        return False
    if path.name in EXCLUDE_FILES:
        return False
    parts = set(path.parts)
    return not any(d in parts for d in EXCLUDE_DIRS)


def line_marker_count(line: str) -> int:
    return sum(1 for c in line if c in GARBLE_MARKERS)


def has_private_use(line: str) -> bool:
    return any(0xE000 <= ord(c) <= 0xF8FF for c in line)


def collect(root: Path):
    findings = []
    for p in root.rglob('*'):
        if not p.is_file() or not should_scan(p):
            continue
        try:
            lines = p.read_text(encoding='utf-8', errors='replace').splitlines()
        except Exception:
            continue
        bad_lines = []
        for i, line in enumerate(lines, 1):
            markers = line_marker_count(line)
            pua = has_private_use(line)
            euro = '€' in line
            if markers >= 3 or pua or euro:
                bad_lines.append({
                    'line': i,
                    'marker_count': markers,
                    'has_private_use': pua,
                    'has_euro': euro,
                    'snippet': line[:220],
                })
        if bad_lines:
            findings.append({
                'path': str(p.relative_to(root)),
                'bad_line_count': len(bad_lines),
                'bad_lines': bad_lines,
            })
    findings.sort(key=lambda x: x['bad_line_count'], reverse=True)
    return findings


def main():
    parser = argparse.ArgumentParser(description='Audit mojibake in text files')
    parser.add_argument('--root', default='.', help='repo root')
    parser.add_argument('--json-out', default='tools/garble_audit_report.json')
    parser.add_argument('--txt-out', default='tools/garble_audit_report.txt')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    findings = collect(root)

    out_json = root / args.json_out
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({'files': findings}, ensure_ascii=False, indent=2), encoding='utf-8')

    lines = [f'Root: {root}', f'Files with suspected mojibake: {len(findings)}', '']
    for f in findings:
        lines.append(f"{f['bad_line_count']:4d}  {f['path']}")
        for bl in f['bad_lines'][:8]:
            lines.append(
                f"      L{bl['line']}: markers={bl['marker_count']} euro={bl['has_euro']} pua={bl['has_private_use']} | {bl['snippet']}"
            )
        if len(f['bad_lines']) > 8:
            lines.append(f"      ... {len(f['bad_lines']) - 8} more lines")
        lines.append('')

    out_txt = root / args.txt_out
    out_txt.write_text('\n'.join(lines), encoding='utf-8')
    print(f'Wrote {out_json}')
    print(f'Wrote {out_txt}')


if __name__ == '__main__':
    main()
