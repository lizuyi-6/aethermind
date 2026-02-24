"""
批量修复所有模板的主题问题：
1. 将暗色页面的hardcoded颜色替换为CSS变量（使用原来的颜色作为fallback）
2. 修复index_server.html缺少theme-loader.js
3. 给暗色页面的<style>块顶部注入CSS变量定义块

暗色页面使用 deep-space 主题变量前缀 --ds-*
亮色页面使用 --theme-* 变量（已有theme-loader处理）
"""
import os
import re

TEMPLATES = r'x:\test_2\templates'

# ============================================================
# 1. product_form.html / index_modern.html / admin_dashboard_modern.html
#    / admin_login_modern.html / czyq_index.html
#    这些都是深蓝暗色页面，使用 #030712 / #0f172a / slate 调色板
# ============================================================
DARK_PAGE_CSS_VARS = """
        /* ================================================
           主题变量 - 深空暗色系 (Deep Space Dark)
           通过 theme-loader.js 动态切换
        ================================================ */
        :root {
            --ds-bg:          3 7 18;       /* #030712 */
            --ds-bg-2:        15 23 42;     /* #0f172a */
            --ds-bg-3:        30 41 59;     /* #1e293b */
            --ds-border:      255 255 255;  /* white at low opacity */
            --ds-text:        226 232 240;  /* #E2E8F0 */
            --ds-text-muted:  100 116 139;  /* #64748B */
            --ds-accent:      99 102 241;   /* #6366f1 indigo-500 */
            --ds-accent-2:    56 189 248;   /* #38bdf8 sky-400 */
            --ds-scrollbar:   51 65 85;     /* #334155 */
        }
        /* Cashmere & Chestnut 暖色主题覆盖 */
        [data-theme="cashmere-chestnut"] {
            --ds-bg:          35 25 20;
            --ds-bg-2:        50 35 28;
            --ds-bg-3:        70 50 40;
            --ds-border:      255 220 200;
            --ds-text:        240 230 220;
            --ds-text-muted:  180 160 145;
            --ds-accent:      160 80 55;
            --ds-accent-2:    200 120 80;
            --ds-scrollbar:   100 70 55;
        }
"""

DARK_PAGE_STYLE_REPLACEMENTS = [
    # body background and text
    (r'background-color:\s*#030712', 'background-color: rgb(var(--ds-bg))'),
    (r'background:\s*#030712', 'background: rgb(var(--ds-bg))'),
    (r'color:\s*#E2E8F0(?![\w-])', 'color: rgb(var(--ds-text))'),
    # scrollbar track
    (r'background:\s*#0f172a(?![\w-])', 'background: rgb(var(--ds-bg-2))'),
    # scrollbar thumb  
    (r'background:\s*#334155(?![\w-])', 'background: rgb(var(--ds-scrollbar))'),
    (r'background:\s*#475569(?![\w-])', 'background: rgb(var(--ds-scrollbar) / 0.8)'),
    # glass panel - dark bg with opacity
    (r'background:\s*rgba\(15,\s*23,\s*42,\s*0\.6\)', 'background: rgba(var(--ds-bg-2), 0.6)'),
    (r'background:\s*rgba\(15,\s*23,\s*42,\s*0\.8\)', 'background: rgba(var(--ds-bg-2), 0.8)'),
    # glass card gradient
    (r'background:\s*linear-gradient\(180deg,\s*rgba\(30,\s*41,\s*59,\s*0\.4\)\s*0%,\s*rgba\(15,\s*23,\s*42,\s*0\.4\)\s*100%\)',
     'background: linear-gradient(180deg, rgb(var(--ds-bg-3) / 0.4) 0%, rgb(var(--ds-bg-2) / 0.4) 100%)'),
    # text glow / hero glow with sky color
    (r'rgba\(56,\s*189,\s*248,\s*0\.3\)', 'rgba(var(--ds-accent-2), 0.3)'),
    (r'rgba\(56,\s*189,\s*248,\s*0\.15\)', 'rgba(var(--ds-accent-2), 0.15)'),
    (r'rgba\(3,\s*7,\s*18,\s*0\)', 'rgb(var(--ds-bg) / 0)'),
    # input field text
    (r'color:\s*#64748B(?![\w-])', 'color: rgb(var(--ds-text-muted))'),
    # step indicator accent
    (r'background:\s*linear-gradient\(135deg,\s*#6366f1\s*0%,\s*#3b82f6\s*100%\)',
     'background: linear-gradient(135deg, rgb(var(--ds-accent)) 0%, rgb(var(--ds-accent-2)) 100%)'),
]

def apply_dark_page_migration(content, filename):
    """Replace hardcoded dark colors with CSS variable calls inside <style> blocks."""
    style_match = re.search(r'(<style[^>]*>)(.*?)(</style>)', content, re.DOTALL)
    if not style_match:
        return content, False
    
    style_open  = style_match.group(1)
    style_inner = style_match.group(2)
    style_close = style_match.group(3)
    
    # Check if already migrated
    if '--ds-bg' in style_inner:
        print(f"  SKIP (already migrated): {filename}")
        return content, False
    
    # Apply replacements inside <style>
    new_inner = style_inner
    for pattern, replacement in DARK_PAGE_STYLE_REPLACEMENTS:
        new_inner = re.sub(pattern, replacement, new_inner)
    
    # Prepend CSS variable definitions (right after @import if present, otherwise at start)
    if '@import' in new_inner:
        # Insert after last @import line
        import_end = max(m.end() for m in re.finditer(r'@import[^;]+;', new_inner))
        new_inner = new_inner[:import_end] + '\n' + DARK_PAGE_CSS_VARS + new_inner[import_end:]
    else:
        new_inner = DARK_PAGE_CSS_VARS + new_inner
    
    new_content = content[:style_match.start()] + style_open + new_inner + style_close + content[style_match.end():]
    return new_content, True


# ============================================================
# 2. Light pages with hardcoded colors (admin_dashboard.html etc)
# ============================================================

LIGHT_PAGE_CSS_VARS = """
        :root {
            --lp-bg:        245 247 250;   /* #f5f7fa */
            --lp-text:      44 62 80;      /* #2c3e50 */
            --lp-text-muted: 90 108 125;   /* #5a6c7d */
            --lp-accent:    102 126 234;   /* #667eea */
            --lp-border:    220 227 235;
        }
        [data-theme="cashmere-chestnut"] {
            --lp-bg:        248 245 240;
            --lp-text:      45 40 38;
            --lp-text-muted: 140 135 130;
            --lp-accent:    140 70 50;
            --lp-border:    235 230 225;
        }
"""

# ============================================================
# Main
# ============================================================

# Dark pages (slate/indigo dark design)
DARK_PAGES = [
    'product_form.html',
    'index_modern.html',
    'admin_dashboard_modern.html',
    'admin_login_modern.html',
    'czyq_index.html',
]

changed_count = 0

for fname in DARK_PAGES:
    path = os.path.join(TEMPLATES, fname)
    if not os.path.exists(path):
        print(f"  NOT FOUND: {fname}")
        continue
    with open(path, encoding='utf-8') as f:
        content = f.read()
    new_content, changed = apply_dark_page_migration(content, fname)
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"  MIGRATED (dark): {fname}")
        changed_count += 1

# Fix missing theme-loader in index_server.html
server_path = os.path.join(TEMPLATES, 'index_server.html')
if os.path.exists(server_path):
    with open(server_path, encoding='utf-8') as f:
        c = f.read()
    if 'theme-loader.js' not in c:
        tag = '    <!-- 全局主题加载器 -->\n    <script src="/static/theme-loader.js"></script>\n'
        if '</head>' in c:
            c = c.replace('</head>', tag + '</head>', 1)
        with open(server_path, 'w', encoding='utf-8') as f:
            f.write(c)
        print(f"  FIXED (loader added): index_server.html")
        changed_count += 1

print(f"\nDone. {changed_count} files modified.")
