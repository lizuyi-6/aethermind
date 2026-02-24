import re
import os

def h2rgb(hex_str):
    h = hex_str.lstrip('#')
    if len(h) == 3:
        h = ''.join(c*2 for c in h)
    return f"{int(h[0:2], 16)} {int(h[2:4], 16)} {int(h[4:6], 16)}"

def gen_theme(name, colors):
    if name == "default":
        css = "        :root {\n"
    else:
        css = f"        [data-theme=\"{name}\"] {{\n"
    for k, v in colors.items():
        css += f"            --{k}: {h2rgb(v)};\n"
    css += "        }\n"
    return css

# 2024 Modern Pure Light Themes
themes = {
    # 1. Coastal Chic (Default)
    "default": {
        "theme-primary": "#1e293b", # slate-800 text (very dark for readability)
        "theme-secondary": "#64748b", # slate-500 text
        "theme-bg-60": "#f1f5f9", # slate-100 (soft icy blue-white)
        "theme-bg-30": "#ffffff", # Pure white panels
        "theme-bg-sidebar": "#e2e8f0", # slate-200
        "theme-border": "#cbd5e1", # slate-300
        "theme-accent-10": "#2563eb", # blue-600 (royal blue)
        "theme-accent-hover": "#1d4ed8",
        "theme-accent-light": "#60a5fa",
        "theme-glass-bg": "#ffffff", # For light glass panels
    },
    # 2. Peach Fuzz (Pantone 2024)
    "peach": {
        "theme-primary": "#431407", # Deep warm brown text
        "theme-secondary": "#78350f", # amber-900 text
        "theme-bg-60": "#fff7ed", # orange-50 (very soft peach/cream)
        "theme-bg-30": "#ffffff", # Pure white panels
        "theme-bg-sidebar": "#ffedd5", # orange-100
        "theme-border": "#fed7aa", # orange-200
        "theme-accent-10": "#f97316", # orange-500 (coral/peach accent)
        "theme-accent-hover": "#ea580c",
        "theme-accent-light": "#fdba74",
        "theme-glass-bg": "#ffffff",
    },
    # 3. Botanical Sage
    "sage": {
        "theme-primary": "#064e3b", # emerald-900 text
        "theme-secondary": "#047857", # emerald-700 text
        "theme-bg-60": "#f0fdf4", # green-50 (soft sage/mint)
        "theme-bg-30": "#ffffff", # Pure white panels
        "theme-bg-sidebar": "#dcfce7", # green-100
        "theme-border": "#bbf7d0", # green-200
        "theme-accent-10": "#059669", # emerald-600
        "theme-accent-hover": "#047857",
        "theme-accent-light": "#34d399",
        "theme-glass-bg": "#ffffff",
    },
    # 4. Lavender Haze
    "lavender": {
        "theme-primary": "#3b0764", # purple-900 text
        "theme-secondary": "#6b21a8", # purple-800 text
        "theme-bg-60": "#faf5ff", # purple-50 (very soft lavender)
        "theme-bg-30": "#ffffff", # Pure white panels
        "theme-bg-sidebar": "#f3e8ff", # purple-100
        "theme-border": "#e9d5ff", # purple-200
        "theme-accent-10": "#9333ea", # purple-600
        "theme-accent-hover": "#7e22ce",
        "theme-accent-light": "#c084fc",
        "theme-glass-bg": "#ffffff",
    },
    # 5. Nordic Minimal
    "nordic": {
        "theme-primary": "#000000", # Pure black text
        "theme-secondary": "#52525b", # zinc-600 text
        "theme-bg-60": "#ffffff", # Pure white background
        "theme-bg-30": "#fafafa", # zinc-50 panels (very subtle gray)
        "theme-bg-sidebar": "#f4f4f5", # zinc-100
        "theme-border": "#e4e4e7", # zinc-200
        "theme-accent-10": "#18181b", # zinc-900 (almost black buttons)
        "theme-accent-hover": "#000000",
        "theme-accent-light": "#71717a",
        "theme-glass-bg": "#fafafa",
    }
}

theme_styles = "\n".join([gen_theme(name, colors) for name, colors in themes.items()])

html_path = 'x:/test_2/templates/landing.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# Replace Tailwind config script with the new one including theme-glass-bg
new_config = """
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        theme: {
                            primary: 'rgb(var(--theme-primary) / <alpha-value>)',
                            secondary: 'rgb(var(--theme-secondary) / <alpha-value>)',
                            60: 'rgb(var(--theme-bg-60) / <alpha-value>)',
                            30: 'rgb(var(--theme-bg-30) / <alpha-value>)',
                            sidebar: 'rgb(var(--theme-bg-sidebar) / <alpha-value>)',
                            border: 'rgb(var(--theme-border) / <alpha-value>)',
                            accent: 'rgb(var(--theme-accent-10) / <alpha-value>)',
                            'accent-hover': 'rgb(var(--theme-accent-hover) / <alpha-value>)',
                            'accent-light': 'rgb(var(--theme-accent-light) / <alpha-value>)',
                            'glass-bg': 'rgb(var(--theme-glass-bg) / <alpha-value>)',
                        }
                    }
                }
            }
        }
    </script>
"""

html = re.sub(r'<script>\s*tailwind\.config.+?</script>', new_config, html, flags=re.DOTALL)

# Adjust glass panels for light themes: 
# Previously panels had 0.4 opacity of a dark color. 
# For pure light themes, we want a white frost effect.
html = re.sub(r'linear-gradient\(180deg, rgba\(30, 41, 59, 0\.4\) 0%, rgba\(15, 23, 42, 0\.4\) 100%\)', 'linear-gradient(180deg, rgb(var(--theme-glass-bg)/0.8) 0%, rgb(var(--theme-glass-bg)/0.6) 100%)', html)
html = re.sub(r'rgba\(15, 23, 42, 0\.6\)', 'rgb(var(--theme-glass-bg) / 0.8)', html)
html = html.replace('text-shadow: 0 0 20px rgb(var(--theme-accent-10) / 0.3);', 'text-shadow: none;') # Remove text glow on light backgrounds for better readability
# Fix the radial gradient again
html = re.sub(r'radial-gradient\(circle at center, rgb\(var\(--theme-accent-10\) / 0\.15\) 0%, rgb\(var\(--theme-bg-60\) / 0\) 70%\)', 'radial-gradient(circle at center, rgb(var(--theme-accent-10) / 0.08) 0%, rgb(var(--theme-bg-60) / 0) 70%)', html)

# Replace old theme variables with new ones
html = re.sub(r':root\s*{[^}]+}', '', html)
html = re.sub(r'\[data-theme="[^"]+"\]\s*{[^}]+}', '', html)

# Inject new theme variables
html = html.replace('</style>', theme_styles + '\n    </style>')

# Replace the panel completely
new_panel = """
    <!-- Theme Workshop Panel -->
    <div class="fixed bottom-6 right-6 z-[100] bg-theme-30 rounded-2xl p-4 shadow-2xl shadow-theme-accent/10 border border-theme-border flex-col w-64 transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] translate-y-0" id="theme-workshop">
        <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
                <iconify-icon icon="solar:palette-bold" class="text-theme-accent text-lg"></iconify-icon>
                <h3 class="text-sm font-semibold text-theme-primary">纯白主题工坊 (2024版)</h3>
            </div>
            <button onclick="document.getElementById('theme-workshop').classList.add('translate-y-[150%]'); document.getElementById('theme-toggle-btn').classList.remove('translate-y-[150%]')" class="text-theme-secondary hover:text-theme-primary transition-colors" title="隐藏面板">
                <iconify-icon icon="solar:close-square-linear" width="20"></iconify-icon>
            </button>
        </div>
        <div class="space-y-3">
            <button onclick="setTheme('default')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-60 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs font-medium text-theme-secondary group-hover:text-theme-primary transition-colors">海岸微风 (Coastal Chic)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#2563eb] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#f1f5f9] border border-theme-border shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('peach')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-60 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs font-medium text-theme-secondary group-hover:text-theme-primary transition-colors">年度蜜桃 (Peach Fuzz)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#f97316] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#fff7ed] border border-theme-border shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('sage')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-60 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs font-medium text-theme-secondary group-hover:text-theme-primary transition-colors">植物鼠尾草 (Botanical Sage)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#059669] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#f0fdf4] border border-theme-border shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('lavender')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-60 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs font-medium text-theme-secondary group-hover:text-theme-primary transition-colors">薰衣草薄雾 (Lavender Haze)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#9333ea] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#faf5ff] border border-theme-border shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('nordic')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-60 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs font-medium text-theme-secondary group-hover:text-theme-primary transition-colors">北欧极简白 (Nordic Minimal)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#18181b] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#ffffff] border border-theme-border shadow-sm"></div>
                </div>
            </button>
        </div>
    </div>
    
    <!-- Floating toggle button to bring panel back -->
    <button id="theme-toggle-btn" onclick="document.getElementById('theme-workshop').classList.remove('translate-y-[150%]'); this.classList.add('translate-y-[150%]')" class="fixed bottom-6 right-6 z-[90] w-12 h-12 rounded-full bg-theme-30 flex items-center justify-center text-theme-accent hover:scale-110 transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] shadow-xl shadow-theme-accent/20 border border-theme-border group translate-y-[150%]">
        <iconify-icon icon="solar:palette-bold" class="text-xl group-hover:rotate-45 transition-transform duration-300"></iconify-icon>
    </button>
"""

html = re.sub(r'<!-- Theme Workshop Panel -->.*?</button>\s*(<script>.*?</script>)?', new_panel + r'\1', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("Pure light themes refactoring complete.")
