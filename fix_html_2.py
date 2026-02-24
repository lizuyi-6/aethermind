import re

file_path = r'x:\test_2\templates\landing.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

# I will find the first theme-toggle-btn, and delete everything from the stray </div> after it to the end of the duplicate theme-toggle-btn.
# Specifically, we want to remove the dangling code:
# </div>
#         <div class="space-y-3">
#             <button onclick="setTheme('default')" ...>Midnight Indigo</button>
#             ...
#         </div>
#     </div>
#     <!-- Floating toggle button to bring panel back -->
#     <button id="theme-toggle-btn" ...>...</button>

pattern = re.compile(
    r'(</button>\s*</div>)\s*<div class="space-y-3">\s*<button onclick="setTheme\(\'default\'\).*?<!-- Floating toggle button to bring panel back -->\s*<button id="theme-toggle-btn".*?</button>', 
    re.DOTALL
)

new_html = pattern.sub(r'\1', html)

# Also fix the footer text color, it currently says text-slate-600
new_html = new_html.replace('text-slate-600', 'text-theme-secondary')

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_html)

print("Cleaned up remaining stray HTML and footer slate text.")
