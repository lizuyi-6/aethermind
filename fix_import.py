"""
修复 migrate_all.py 破坏的 @import 语句。
问题：@import url 里包含 ; 符号（font weight 范围参数），
被 re 误判为 @import 语句的结束位置，导致 CSS 变量块插入到 URL 中间。

修复策略：移除错误插入的块，重新正确插入（在整个 @import 语句之后）。
"""
import os
import re

TEMPLATES = r'x:\test_2\templates'

DARK_PAGES = [
    'product_form.html',
    'index_modern.html',
    'admin_dashboard_modern.html',
    'admin_login_modern.html',
    'czyq_index.html',
]

DARK_PAGE_CSS_VARS = """
        /* ================================================
           主题变量 - 深空暗色系 (Deep Space Dark)
           通过 theme-loader.js 动态切换
        ================================================ */
        :root {
            --ds-bg:          3 7 18;
            --ds-bg-2:        15 23 42;
            --ds-bg-3:        30 41 59;
            --ds-border:      255 255 255;
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
            --ds-border:      255 220 200;
            --ds-text:        240 230 220;
            --ds-text-muted:  180 160 145;
            --ds-accent:      160 80 55;
            --ds-accent-2:    200 120 80;
            --ds-scrollbar:   100 70 55;
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
        [data-theme="default"] {
            --ds-bg:          241 245 249;
            --ds-bg-2:        226 232 240;
            --ds-bg-3:        203 213 225;
            --ds-text:        30 41 59;
            --ds-text-muted:  100 116 139;
            --ds-accent:      37 99 235;
            --ds-accent-2:    96 165 250;
            --ds-scrollbar:   203 213 225;
        }
"""


def fix_file(fname):
    path = os.path.join(TEMPLATES, fname)
    if not os.path.exists(path):
        print(f"  NOT FOUND: {fname}")
        return False
    
    with open(path, encoding='utf-8') as f:
        content = f.read()
    
    # Find <style> block
    style_match = re.search(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    if not style_match:
        print(f"  NO STYLE: {fname}")
        return False
    
    style_open  = style_match.group(0)[:style_match.group(0).index(style_match.group(1))]
    style_inner = style_match.group(1)
    style_close = '</style>'
    
    # Step 1: Remove any previously injected broken CSS var block
    # (the block starts with /* === 主题变量 and ends before the next real CSS rule)
    style_inner = re.sub(
        r'/\* ={3,}\s*主题变量.*?(?=\n\s*(?:@import|body\s*\{|/\*(?!\s*={3,}\s*主题变量)))',
        '',
        style_inner,
        flags=re.DOTALL
    )
    
    # Step 2: Reassemble broken @import if needed
    # Check if @import is split (has content between @import and the URL end)
    # Pattern for broken import: @import url('...incomplete...\n\n/* vars */\n...rest...')
    # Actually, the problem is that the url string got split, let's detect that
    # A valid @import url() ends with ); on the same logical line
    # Let's find any @import that doesn't have ); before a newline with CSS rules
    
    # More reliable: just rebuild from scratch using the original parts
    # Find @import statements (they may be split)
    # Look for @import ... everything until '); which might span multiple lines now
    
    # Remove misplaced CSS var content inside @import if present
    # This happens when content between @import url(' and '); contains our block
    def fix_broken_import(m):
        full = m.group(0)
        # If our marker is inside it, remove it
        full = re.sub(r'/\*\s*={3,}.*?={3,}\s*\*/.*?(?=\w)', '', full, flags=re.DOTALL)
        return full
    
    style_inner = re.sub(r"@import\s+url\('[^']*'\s*\)", fix_broken_import, style_inner, flags=re.DOTALL)
    
    # Step 3: Find the correct insertion point - AFTER all @import lines
    # @import must be the first rules in a stylesheet
    # Find the end of all @import statements
    remaining = style_inner
    
    # Find last @import
    import_matches = list(re.finditer(r"@import\s+url\('[^']+'\);?", remaining))
    if import_matches:
        insert_pos = import_matches[-1].end()
    else:
        insert_pos = 0
    
    # Insert CSS vars at the right position
    style_inner = remaining[:insert_pos] + '\n' + DARK_PAGE_CSS_VARS + remaining[insert_pos:]
    
    # Rebuild the full content
    new_content = (
        content[:style_match.start()] + 
        style_open + 
        style_inner + 
        style_close + 
        content[style_match.end():]
    )
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"  FIXED: {fname}")
    return True


for fname in DARK_PAGES:
    fix_file(fname)

print("\nDone.")
