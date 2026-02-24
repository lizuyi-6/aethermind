"""
Fix the 3 remaining dark pages with broken @import.
The broken pattern is:
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;
  [... CSS var block ...]
  400;500;600&family=Noto+Sans+SC:wght@300;400;500;600&display=swap');

Replace this with the correct pattern (CSS vars then the full import).
"""
import os
import re

TEMPLATES = r'x:\test_2\templates'

# Files to fix
FILES = [
    'index_modern.html',
    'admin_dashboard_modern.html',
    'admin_login_modern.html',
]

# The broken import prefix and suffix
BROKEN_PREFIX = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;"
BROKEN_SUFFIX = "400;500;600&family=Noto+Sans+SC:wght@300;400;500;600&display=swap');"

CORRECT_IMPORT = "@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&family=Noto+Sans+SC:wght@300;400;500;600&display=swap');"

DS_VARS = """
        /* ================================================
           主题变量 - 通过 theme-loader.js 动态切换
        ================================================ */
        :root {
            --ds-bg:          3 7 18;
            --ds-bg-2:        15 23 42;
            --ds-bg-3:        30 41 59;
            --ds-text:        226 232 240;
            --ds-text-muted:  100 116 139;
            --ds-accent:      99 102 241;
            --ds-accent-2:    56 189 248;
            --ds-scrollbar:   51 65 85;
        }
        [data-theme="cashmere-chestnut"] {
            --ds-bg:          35 25 20;
            --ds-bg-2:        50 35 28;
            --ds-bg-3:        70 50 40;
            --ds-text:        240 230 220;
            --ds-text-muted:  180 160 145;
            --ds-accent:      160 80 55;
            --ds-accent-2:    200 120 80;
            --ds-scrollbar:   100 70 55;
        }
        [data-theme="default"] {
            --ds-bg:          15 23 42;
            --ds-bg-2:        30 41 59;
            --ds-bg-3:        51 65 85;
            --ds-text:        226 232 240;
            --ds-text-muted:  148 163 184;
            --ds-accent:      37 99 235;
            --ds-accent-2:    96 165 250;
            --ds-scrollbar:   100 116 139;
        }
        [data-theme="deep-space"] {
            --ds-bg:          3 7 18;
            --ds-bg-2:        15 23 42;
            --ds-bg-3:        30 41 59;
            --ds-text:        226 232 240;
            --ds-text-muted:  100 116 139;
            --ds-accent:      99 102 241;
            --ds-accent-2:    56 189 248;
            --ds-scrollbar:   51 65 85;
        }
"""

for fname in FILES:
    path = os.path.join(TEMPLATES, fname)
    if not os.path.exists(path):
        print(f"SKIP: {fname}")
        continue
    
    with open(path, encoding='utf-8') as f:
        content = f.read()
    
    # Find the broken section: prefix [CSS stuff] suffix
    # Build a regex to match: broken_prefix + anything + broken_suffix
    broken_re = re.compile(
        re.escape(BROKEN_PREFIX) + r'.*?' + re.escape(BROKEN_SUFFIX),
        re.DOTALL
    )
    
    m = broken_re.search(content)
    if not m:
        print(f"NO BROKEN IMPORT FOUND: {fname}")
        continue
    
    # Replace with correct import + DS vars
    new_section = CORRECT_IMPORT + '\n' + DS_VARS
    new_content = content[:m.start()] + new_section + content[m.end():]
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"FIXED: {fname}")

print("Done.")
