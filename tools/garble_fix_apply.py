import argparse
import json
from pathlib import Path

TEXT_EXTS = {
    '.py', '.js', '.html', '.css', '.md', '.txt', '.json', '.wxml', '.wxss'
}
EXCLUDE_DIRS = {
    '.git', '__pycache__', '_cleanup_archive', 'reports', '.venv', 'venv', 'node_modules', 'tools'
}
EXCLUDE_FILES = {'runtime_state.json'}

GARBLE_MARKERS = set('鍙鏄鐨绗浠鏈寮閰楠鑾濡璇鏂澶勬洿绔犺妭銆锛寤娴嬭瘉瀛楀彇浣跨敤鏍鍖犲壊鎺掕穭鐣坓€')
COMMON_CHARS = set(
    '的一是在不了有和人这中大为上个国我以要他时来用们生到作地于出就分对成会可主发年动同工也能下过子说产种面而方后多定行学法所民得经十'
    '三之进着等部度家电力里如水化高自二理起小物现实加量都两体制机当使点从业本去把性好应开它合还因由其些然前外天政四日那社义事平形相全'
    '表间样与关各重新线内数正心反你明看原又么利比或但质气第向道命此变条只没结解问意建月公无系军很情者最立代想已通并提直题党程展五果料'
    '象员革位入常文总次品式活设及管特件长求老'
)


def should_scan(path: Path) -> bool:
    if path.suffix.lower() not in TEXT_EXTS:
        return False
    if path.name in EXCLUDE_FILES:
        return False
    parts = set(path.parts)
    return not any(d in parts for d in EXCLUDE_DIRS)


def marker_count(s: str) -> int:
    return sum(1 for c in s if c in GARBLE_MARKERS)


def has_private_use(s: str) -> bool:
    return any(0xE000 <= ord(c) <= 0xF8FF for c in s)


def bad_score(s: str) -> int:
    return marker_count(s) + (5 if has_private_use(s) else 0) + (2 * s.count('€')) + (3 * s.count('�'))


def common_score(s: str) -> int:
    return sum(1 for c in s if c in COMMON_CHARS)


def cjk_count(s: str) -> int:
    return sum(1 for c in s if '\u4e00' <= c <= '\u9fff')


def try_recover(line: str):
    current = line
    best = line
    best_score = bad_score(line)
    orig_cjk = cjk_count(line)

    for _ in range(4):
        next_candidate = None
        for enc_err in ('strict', 'ignore'):
            for dec_err in ('strict', 'ignore'):
                try:
                    candidate = current.encode('gbk', errors=enc_err).decode('utf-8', errors=dec_err)
                except Exception:
                    continue
                if not candidate:
                    continue
                cand_cjk = cjk_count(candidate)
                if orig_cjk >= 4 and cand_cjk < int(orig_cjk * 0.6):
                    continue
                cand_score = bad_score(candidate)
                if cand_score < best_score or (
                    cand_score == best_score and common_score(candidate) > common_score(best)
                ):
                    best = candidate
                    best_score = cand_score
                if next_candidate is None:
                    next_candidate = candidate
        if next_candidate is None or next_candidate == current:
            break
        current = next_candidate

    if best_score < bad_score(line):
        return best
    return None


def should_replace(original: str, candidate: str) -> bool:
    if candidate is None or candidate == original:
        return False
    o_mark = marker_count(original)
    c_mark = marker_count(candidate)
    o_bad = bad_score(original)
    c_bad = bad_score(candidate)

    # Strong improvement rule.
    if o_bad >= 3 and c_bad <= max(0, o_bad - 3):
        return True

    # Moderate rule when original is clearly garbled and candidate removes key signs.
    if (o_mark >= 3 or has_private_use(original) or '€' in original) and c_bad < o_bad and c_mark <= 1:
        return True

    # Readability boost rule for Chinese text.
    if any('\u4e00' <= ch <= '\u9fff' for ch in original):
        o_common = common_score(original)
        c_common = common_score(candidate)
        if c_common >= o_common + 4 and c_bad <= o_bad:
            return True

    return False


def process_file(path: Path):
    raw = path.read_text(encoding='utf-8', errors='replace')
    had_trailing_newline = raw.endswith('\n')
    src = raw.splitlines()
    changed = False
    out = []
    line_changes = []

    for i, line in enumerate(src, 1):
        cand = try_recover(line)
        if cand and should_replace(line, cand):
            out.append(cand)
            changed = True
            line_changes.append({'line': i, 'before': line[:200], 'after': cand[:200]})
        else:
            out.append(line)

    if changed:
        path.write_text('\n'.join(out) + ('\n' if had_trailing_newline else ''), encoding='utf-8')
    return changed, line_changes


def main():
    parser = argparse.ArgumentParser(description='Apply mojibake fixes')
    parser.add_argument('--root', default='.')
    parser.add_argument('--report', default='tools/garble_fix_report.json')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    root = Path(args.root).resolve()
    changed_files = []

    for p in root.rglob('*'):
        if not p.is_file() or not should_scan(p):
            continue
        try:
            changed, line_changes = process_file(p) if not args.dry_run else (False, [])
            if args.dry_run:
                src = p.read_text(encoding='utf-8', errors='replace').splitlines()
                tmp_changes = []
                for i, line in enumerate(src, 1):
                    cand = try_recover(line)
                    if cand and should_replace(line, cand):
                        tmp_changes.append({'line': i, 'before': line[:200], 'after': cand[:200]})
                if tmp_changes:
                    changed_files.append({'path': str(p.relative_to(root)), 'changes': tmp_changes})
            else:
                if changed:
                    changed_files.append({'path': str(p.relative_to(root)), 'changes': line_changes})
        except Exception:
            continue

    report_path = root / args.report
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps({'changed_files': changed_files}, ensure_ascii=False, indent=2), encoding='utf-8')

    print(f"Changed files: {len(changed_files)}")
    print(f"Report: {report_path}")


if __name__ == '__main__':
    main()
