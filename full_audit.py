"""
Full audit: find which templates have hardcoded colors in <style> blocks
vs using CSS variables.
"""
import os
import re

TEMPLATES = r'x:\test_2\templates'

for fname in sorted(os.listdir(TEMPLATES)):
    if not fname.endswith('.html'):
        continue
    path = os.path.join(TEMPLATES, fname)
    with open(path, encoding='utf-8') as f:
        content = f.read()

    head = content.split('</head>')[0] if '</head>' in content else ''
    
    has_loader   = 'theme-loader.js' in head
    has_workshop = 'theme-workshop.js' in content
    url_for_count = len(re.findall(r"url_for\(", content))
    
    # Detect hardcoded colors in <style> blocks
    style_blocks = re.findall(r'<style[^>]*>(.*?)</style>', content, re.DOTALL)
    hardcoded_colors_in_style = []
    for block in style_blocks:
        colors = re.findall(r'(?:background|color|border)[^:]*:\s*(#[0-9a-fA-F]{3,8}|rgba?\([^)]+\))', block)
        if colors:
            hardcoded_colors_in_style.extend(colors[:3])  # first 3
    
    issues = []
    if not has_loader:
        issues.append('MISSING theme-loader.js in head')
    if not has_workshop:
        issues.append('MISSING theme-workshop.js')
    if url_for_count > 0:
        issues.append(f'{url_for_count} url_for() refs')
    if hardcoded_colors_in_style:
        issues.append(f'hardcoded colors in <style>: {hardcoded_colors_in_style[:3]}...')
    
    status = 'OK' if not issues else 'ISSUES'
    print(f"[{status}] {fname}")
    for issue in issues:
        print(f"       - {issue}")
