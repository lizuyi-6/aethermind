import re

file_path = r'x:\test_2\templates\landing.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Remove the .glass-card CSS block entirely
html = re.sub(
    r'\s*\.glass-card\s*\{[^}]+\}\s*\.glass-card:hover\s*\{[^}]+\}',
    '',
    html,
    flags=re.MULTILINE
)

# Replace 'glass-card' with the new robust tailwind classes for the feature cards
new_classes = (
    "bg-theme-30 border border-theme-border shadow-[0_8px_30px_rgb(var(--theme-primary)/0.04)] "
    "hover:shadow-[0_8px_30px_rgb(var(--theme-primary)/0.12)] transition-all duration-300 hover:-translate-y-1"
)

html = html.replace('glass-card', new_classes)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("Replaced glass-card with pristine Tailwind modern card classes.")
