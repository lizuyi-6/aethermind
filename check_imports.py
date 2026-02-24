"""
Check which dark pages still have broken @import (split by inserted CSS block).
A broken @import looks like the URL is cut before ');
"""
import os, re
TEMPLATES = r'x:\test_2\templates'
DARK_PAGES = ['index_modern.html','admin_dashboard_modern.html','admin_login_modern.html','czyq_index.html']
for fname in DARK_PAGES:
    path = os.path.join(TEMPLATES, fname)
    if not os.path.exists(path):
        print(f"SKIP: {fname}")
        continue
    with open(path, encoding='utf-8') as f:
        content = f.read()
    # Find style block
    m = re.search(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    if m:
        inner = m.group(1)
        imports = re.findall(r"@import[^;]*;", inner)
        broken = [i for i in imports if '://' not in i or "');" not in i]
        has_ds_bg = '--ds-bg' in inner
        print(f"{fname}: imports={imports[:1]}, broken={broken}, has_ds_bg={has_ds_bg}")
    else:
        print(f"{fname}: NO STYLE BLOCK")
