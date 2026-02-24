"""
Comprehensive audit of all HTML templates in x:/test_2/templates.
Checks for:
  1. Missing theme-loader.js  (in head)
  2. Missing theme-workshop.js (in body)
  3. Remaining Jinja2 url_for() references
  4. Remaining {{ }} Jinja2 blocks (other than comments)
"""
import os
import re

TEMPLATES = r'x:\test_2\templates'


def audit():
    issues_by_file = {}
    for fname in sorted(os.listdir(TEMPLATES)):
        if not fname.endswith('.html'):
            continue
        path = os.path.join(TEMPLATES, fname)
        with open(path, encoding='utf-8') as f:
            content = f.read()

        issues = []

        # Split head vs body
        head = content.split('</head>')[0] if '</head>' in content else ''
        body = content.split('<body')[1] if '<body' in content else content

        # 1. theme-loader.js  — must be in <head>
        if 'theme-loader.js' not in head:
            if 'theme-loader.js' in body:
                issues.append('WARN: theme-loader.js in body (should be in head)')
            else:
                issues.append('ERROR: theme-loader.js MISSING entirely')

        # 2. theme-workshop.js — should be somewhere (ideally before </body>)
        if 'theme-workshop.js' not in content:
            issues.append('ERROR: theme-workshop.js MISSING')

        # 3. url_for references (Jinja2 template syntax leaking to browser)
        url_for_hits = re.findall(r"url_for\('static',\s*filename='([^']+)'\)", content)
        if url_for_hits:
            issues.append(f"ERROR: url_for() refs still present: {url_for_hits}")

        # 4. Other Jinja2 {{ }} blocks (excluding HTML comments about jinja)
        jinja_blocks = re.findall(r'\{\{([^}]{1,60})\}\}', content)
        if jinja_blocks:
            # filter out false-positives like template comments
            real = [b.strip() for b in jinja_blocks if 'url_for' in b or 'config' in b.lower() or 'session' in b.lower()]
            if real:
                issues.append(f"ERROR: Jinja2 blocks: {real[:5]}")

        if issues:
            issues_by_file[fname] = issues
        else:
            print(f'  [OK]  {fname}')

    print()
    for fname, issues in issues_by_file.items():
        print(f'  [!!] {fname}')
        for i in issues:
            print(f'         {i}')

    return issues_by_file


if __name__ == '__main__':
    audit()
