import re

html_path = 'x:/test_2/templates/landing.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Custom Scrollbar
html = html.replace('background: #0f172a;', 'background: rgb(var(--theme-bg-sidebar));')
html = html.replace('background: #334155;', 'background: rgb(var(--theme-border));')
html = html.replace('background: #475569;', 'background: rgb(var(--theme-secondary));')
# Make scrollbar border radius slightly larger for a softer look
html = html.replace('border-radius: 4px;', 'border-radius: 9999px;') 
# Also remove the hardcoded width if there's any, or tone it down.
# Let's keep width 8px but make it look nicer.

# 2. Application Scenarios Cards
# bg-slate-900/40 is completely mismatched with light themes. 
# We'll use bg-theme-30/40 or just bg-theme-30 for better legibility and border-theme-border
html = html.replace('bg-slate-900/40 hover:border-theme-accent/30', 'bg-theme-30 border-theme-border shadow-sm hover:border-theme-accent/30 hover:shadow-md')
html = html.replace('bg-slate-900/40 border border-white/5 hover:border-theme-accent/30', 'bg-theme-30 border border-theme-border shadow-sm hover:border-theme-accent/50 hover:shadow-md')

# Some icons in Scenarios are still hardcoded sky-400, emerald-400, amber-400
# We can keep them since they are colorful, but let's make sure text below is theme-primary
html = html.replace('class="text-theme-primary text-sm font-medium"', 'class="text-theme-primary text-sm font-semibold"')

# Scenario mobile banner
html = html.replace('bg-gradient-to-r from-slate-900 to-slate-800 border border-white/5', 'bg-gradient-to-r from-theme-30 to-theme-sidebar border border-theme-border shadow-sm')

# 3. Knowledge Base visualization component (Mock UI right panel)
html = html.replace('bg-slate-700', 'bg-theme-border')
html = html.replace('bg-slate-600', 'bg-theme-secondary')
html = html.replace('border-slate-700', 'border-theme-border')
html = html.replace('bg-slate-800', 'bg-theme-border/50')
html = html.replace('bg-slate-800/50 rounded p-2 border border-white/5', 'bg-theme-60 rounded p-2 border border-theme-border')

# 4. Main Chat Area
html = html.replace('bg-slate-900/50 border border-white/5', 'bg-theme-30 border border-theme-border shadow-sm')
html = re.sub(r'bg-slate-800 text-theme-primary', 'bg-theme-accent text-white shadow-md', html) # User message bubble, always white text and accent background looks best
html = html.replace('bg-slate-700 flex-shrink-0 flex items-center justify-center text-theme-primary', 'bg-theme-accent flex-shrink-0 flex items-center justify-center text-white font-bold shadow-md') # User avatar
html = html.replace('bg-[#141416]', 'bg-theme-30')

# Hero glowing buttons shadows
html = html.replace('shadow-indigo-900/20', 'shadow-theme-accent/20')

# Tech Stack icons background
html = html.replace('w-10 h-10 rounded bg-slate-800/50 flex items-center justify-center border border-white/5', 'w-10 h-10 rounded bg-theme-30 flex items-center justify-center border border-theme-border shadow-sm')

# 5. Footer fixes
html = html.replace('w-5 h-5 rounded-full bg-slate-800 flex items-center justify-center', 'w-5 h-5 rounded-full bg-theme-primary flex items-center justify-center')
html = html.replace('text-slate-600 hover:text-slate-400', 'text-theme-secondary hover:text-theme-accent')

# 6. Some text fixes
html = html.replace('text-slate-400', 'text-theme-secondary')
html = html.replace('text-slate-500', 'text-theme-secondary')
html = html.replace('text-slate-300', 'text-theme-primary')
html = html.replace('text-white', 'text-theme-primary') 
html = html.replace('text-indigo-200', 'text-theme-primary') # selection color
html = html.replace('bg-indigo-900/30', 'bg-theme-border/50') # progress bar background
html = html.replace('bg-[#0B0C0E]', 'bg-theme-30')

# For the user avatar, let's revert back the text color override so it's always white because it's on accent bg
html = html.replace('text-theme-primary text-xs w-8 h-8 rounded-full bg-theme-accent', 'text-white text-xs w-8 h-8 rounded-full bg-theme-accent')
html = html.replace('text-theme-primary text-sm py-2 px-4 rounded-2xl rounded-tr-sm bg-theme-accent', 'text-white text-sm py-2 px-4 rounded-2xl rounded-tr-sm bg-theme-accent')

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("V4 deep cleanup complete.")
