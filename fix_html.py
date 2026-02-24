import re

html_path = r'x:\test_2\templates\landing.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Fix the colored icons in the features section to use theme-primary and theme-accent so they adapt to all light themes
html = re.sub(r'bg-sky-500/10', 'bg-theme-secondary/10', html)
html = re.sub(r'text-sky-400', 'text-theme-secondary', html)
html = re.sub(r'border-sky-500/20', 'border-theme-secondary/20', html)

html = re.sub(r'bg-rose-500/10', 'bg-theme-accent/10', html)
html = re.sub(r'text-rose-400', 'text-theme-accent', html)
html = re.sub(r'border-rose-500/20', 'border-theme-accent/20', html)

html = re.sub(r'text-blue-400', 'text-theme-primary', html)

html = re.sub(r'bg-amber-500/10', 'bg-theme-primary/10', html)
html = re.sub(r'text-amber-400', 'text-theme-primary', html)
html = re.sub(r'border-amber-500/20', 'border-theme-primary/20', html)

html = re.sub(r'text-emerald-500', 'text-theme-accent', html)
html = re.sub(r'bg-emerald-500', 'bg-theme-accent', html)
html = re.sub(r'text-emerald-400', 'text-theme-accent-light', html)

# Fix the gradient in the logo block
html = html.replace('bg-gradient-to-tr from-indigo-500 to-sky-400', 'bg-gradient-to-tr from-theme-accent to-theme-primary')

# 2. Delete the dangling Old Theme HTML
# The structure is currently:
# </div> (closes the main floating panel)
#         <div class="space-y-3">
#             <button onclick="setTheme('default')...</button>
#             <button onclick="setTheme('pearl')...</button>
#             ...

# We will simply regex out the entire block starting with the stray <div class="space-y-3"> down to the 'mocha' button's closing tag.
# We will find the stray section carefully.
stray_pattern = re.compile(
    r'\s*</div>\s*<div class="space-y-3">\s*<button onclick="setTheme\(\'default\'\).*?温暖摩卡 \(Warm Mocha\).*?</button>\s*(?:</div>)?',
    re.DOTALL
)

html = stray_pattern.sub('', html)

# Let's also make sure to remove any rogue old theme buttons individually if the big block match fails
old_themes = ['default', 'pearl', 'matcha', 'mocha']
for t in old_themes:
    if t == 'default' and "海岸微风" in html:
        # Wait, I didn't override 'default' with Coastal chic in the new panel did I?
        # Let's check new panel code from previous step. 
        # Ah! New panel: <button onclick="setTheme('default')" ...>海岸微风 (Coastal Chic)</span>
        # Old panel: <button onclick="setTheme('default')" ...>深海靛蓝 (Midnight)</span>
        # Let's be very safe and just remove buttons that contain the old names.
        pass

# Safest way to remove just the old buttons: Remove button tags containing the old names.
html = re.sub(r'<button[^>]*>\s*<span[^>]*>深海靛蓝 \(Midnight\)</span>.*?</button>', '', html, flags=re.DOTALL)
html = re.sub(r'<button[^>]*>\s*<span[^>]*>珍珠纯白 \(Pearl Light\)</span>.*?</button>', '', html, flags=re.DOTALL)
html = re.sub(r'<button[^>]*>\s*<span[^>]*>抹茶薄荷 \(Matcha Light\)</span>.*?</button>', '', html, flags=re.DOTALL)
html = re.sub(r'<button[^>]*>\s*<span[^>]*>温暖摩卡 \(Warm Mocha\)</span>.*?</button>', '', html, flags=re.DOTALL)

# Remove any empty <div class="space-y-3"></div> that might be left over
html = re.sub(r'<div class="space-y-3">\s*</div>', '', html)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print('Applied comprehensive adaptations to landing.html')
