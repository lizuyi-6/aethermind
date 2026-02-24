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

# 60-30-10 Principle Themes
themes = {
    # 1. Midnight Indigo (Dark - Default)
    "default": {
        "theme-primary": "#ffffff", # mostly white text 
        "theme-secondary": "#94a3b8", # slate-400 text
        "theme-bg-60": "#0B0F19", # Deep background
        "theme-bg-30": "#151C2C", # Panels
        "theme-bg-sidebar": "#0f1115",
        "theme-border": "#334155", # slate-700
        "theme-accent-10": "#6366f1", # Indigo 500
        "theme-accent-hover": "#4f46e5",
        "theme-accent-light": "#818cf8",
    },
    # 2. Pearl White (Light)
    "pearl": {
        "theme-primary": "#0f172a", # slate-900 text
        "theme-secondary": "#475569", # slate-600 text
        "theme-bg-60": "#F8FAFC", # Light background
        "theme-bg-30": "#FFFFFF", # White Panels
        "theme-bg-sidebar": "#F1F5F9",
        "theme-border": "#e2e8f0", # slate-200
        "theme-accent-10": "#4F46E5", # Royal Blue
        "theme-accent-hover": "#4338ca",
        "theme-accent-light": "#818cf8",
    },
    # 3. Matcha Mint (Light)
    "matcha": {
        "theme-primary": "#064e3b", # emerald-900 text
        "theme-secondary": "#059669", # emerald-600 text
        "theme-bg-60": "#ECFDF5", # Mint background
        "theme-bg-30": "#FFFFFF", # White Panels
        "theme-bg-sidebar": "#d1fae5",
        "theme-border": "#a7f3d0", # emerald-200
        "theme-accent-10": "#10B981", # Emerald 500
        "theme-accent-hover": "#059669",
        "theme-accent-light": "#34d399",
    },
    # 4. Warm Mocha (Dark)
    "mocha": {
        "theme-primary": "#fafaf9", # stone-50 text
        "theme-secondary": "#a8a29e", # stone-400 text
        "theme-bg-60": "#292524", # stone-800
        "theme-bg-30": "#44403C", # stone-700
        "theme-bg-sidebar": "#1c1917", # stone-900
        "theme-border": "#57534e", # stone-600
        "theme-accent-10": "#F59E0B", # amber 500
        "theme-accent-hover": "#d97706",
        "theme-accent-light": "#fbbf24",
    },
    # 5. Cyber Neon (Dark)
    "cyber": {
        "theme-primary": "#fdf2f8", # pink-50 text
        "theme-secondary": "#f472b6", # pink-400 text
        "theme-bg-60": "#170229", # Dark purple
        "theme-bg-30": "#2E0452", # Purple panel
        "theme-bg-sidebar": "#0f001a",
        "theme-border": "#701a75", # fuchsia-900
        "theme-accent-10": "#F472B6", # pink 400
        "theme-accent-hover": "#db2777",
        "theme-accent-light": "#fbcfe8",
    }
}

theme_styles = "\n".join([gen_theme(name, colors) for name, colors in themes.items()])

html_path = 'x:/test_2/templates/landing.html'

with open(html_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Backgrounds (60/30)
html = html.replace('bg-brand-bg1', 'bg-theme-60') # in case they exist
html = html.replace('bg-theme-bg', 'bg-theme-60')
html = html.replace('bg-theme-bg-alt', 'bg-theme-30')
html = html.replace('bg-theme-bg-panel', 'bg-theme-30')
html = html.replace('bg-theme-bg-footer', 'bg-theme-60')
html = html.replace('bg-[#030712]', 'bg-theme-60')
html = html.replace('bg-[#0B0C0E]', 'bg-theme-30')
html = html.replace('bg-[#141416]', 'bg-theme-30')
html = html.replace('bg-[#05080f]', 'bg-theme-60')

# 2. Text Colors
html = re.sub(r'\btext-white\b', 'text-theme-primary', html)
html = re.sub(r'\btext-slate-200\b', 'text-theme-primary', html)
html = re.sub(r'\btext-slate-300\b', 'text-theme-secondary', html)
html = re.sub(r'\btext-slate-400\b', 'text-theme-secondary', html)
html = re.sub(r'\btext-slate-500\b', 'text-theme-secondary', html)

# 3. Accents
html = re.sub(r'\btext-indigo-400\b', 'text-theme-accent-light', html)
html = re.sub(r'\btext-indigo-300\b', 'text-theme-accent-light', html)
html = re.sub(r'\bbg-indigo-500\b', 'bg-theme-accent', html)
html = re.sub(r'\bbg-indigo-500/10\b', 'bg-theme-accent/10', html)
html = re.sub(r'\bbg-indigo-500/20\b', 'bg-theme-accent/20', html)
html = re.sub(r'\bbg-indigo-600\b', 'bg-theme-accent-hover', html)
html = re.sub(r'\bhover:bg-indigo-500\b', 'hover:bg-theme-accent', html)
html = re.sub(r'\bborder-indigo-500\b', 'border-theme-accent', html)
html = re.sub(r'\bborder-indigo-500/30\b', 'border-theme-accent/30', html)
html = re.sub(r'\bborder-indigo-500/20\b', 'border-theme-accent/20', html)

# 4. Borders & Lines
html = re.sub(r'\border-white/5\b', 'border-theme-border/50', html)
html = re.sub(r'\border-white/10\b', 'border-theme-border/80', html)
html = re.sub(r'\bbg-white/5\b', 'bg-theme-border/50', html)

# 5. Fix body background in CSS
html = html.replace('background-color: rgb(var(--theme-bg));', 'background-color: rgb(var(--theme-bg-60));')
html = html.replace('background-color: #030712;', 'background-color: rgb(var(--theme-bg-60));')

# Replace inline style for hero-glow
html = re.sub(r'radius-gradient\(circle at center, rgba\(56, 189, 248, 0\.15\) 0%, rgba\(3, 7, 18, 0\) 70%\)', 'radial-gradient(circle at center, rgb(var(--theme-accent-10) / 0.15) 0%, rgb(var(--theme-bg-60) / 0) 70%)', html)
html = html.replace('rgba(56, 189, 248, 0.3)', 'rgb(var(--theme-accent-10) / 0.3)')
html = html.replace('rgba(56, 189, 248, 0.15)', 'rgb(var(--theme-accent-10) / 0.15)')

# 6. Rewrite Tailwind config script
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
                        }
                    }
                }
            }
        }
    </script>
"""

html = re.sub(r'<script>\s*tailwind\.config.+?</script>', new_config, html, flags=re.DOTALL)
html = html.replace('<!-- 开发环境使用 Tailwind CDN，生产环境建议使用 PostCSS 或 Tailwind CLI -->', '<!-- 开发环境使用 Tailwind CDN，生产环境建议使用 PostCSS 或 Tailwind CLI -->\n' + new_config)


# Replace old theme variables with new ones
html = re.sub(r':root\s*{[^}]+}', '', html)
html = re.sub(r'\[data-theme="[^"]+"\]\s*{[^}]+}', '', html)

# Inject new theme variables
html = html.replace('</style>', theme_styles + '\n    </style>')

# Replace the old panel with the new one
new_panel = """
    <!-- Theme Workshop Panel -->
    <div class="fixed bottom-6 right-6 z-[100] bg-theme-30 rounded-2xl p-4 shadow-2xl border border-theme-border w-64 transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] translate-y-0" id="theme-workshop">
        <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
                <iconify-icon icon="solar:palette-round-linear" class="text-theme-primary text-lg"></iconify-icon>
                <h3 class="text-sm font-medium text-theme-primary">主题工作坊</h3>
            </div>
            <button onclick="document.getElementById('theme-workshop').classList.add('translate-y-[150%]'); document.getElementById('theme-toggle-btn').classList.remove('translate-y-[150%]')" class="text-theme-secondary hover:text-theme-primary transition-colors" title="隐藏面板">
                <iconify-icon icon="solar:close-square-linear" width="20"></iconify-icon>
            </button>
        </div>
        <div class="space-y-3">
            <button onclick="setTheme('default')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-border/30 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs text-theme-secondary group-hover:text-theme-primary transition-colors">深海靛蓝 (Midnight)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#6366f1] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#0B0F19] border border-theme-border shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('pearl')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-border/30 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs text-theme-secondary group-hover:text-theme-primary transition-colors">珍珠纯白 (Pearl Light)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#4F46E5] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#F8FAFC] border border-theme-border shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('matcha')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-border/30 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs text-theme-secondary group-hover:text-theme-primary transition-colors">抹茶薄荷 (Matcha Light)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#10B981] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#ECFDF5] border border-theme-border shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('mocha')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-border/30 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs text-theme-secondary group-hover:text-theme-primary transition-colors">温暖摩卡 (Warm Mocha)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#F59E0B] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#292524] border border-theme-border shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('cyber')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-theme-border/30 transition-colors border border-transparent hover:border-theme-border group">
                <span class="text-xs text-theme-secondary group-hover:text-theme-primary transition-colors">赛博霓虹 (Cyber Neon)</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#F472B6] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#170229] border border-theme-border shadow-sm"></div>
                </div>
            </button>
        </div>
    </div>
    
    <!-- Floating toggle button to bring panel back -->
    <button id="theme-toggle-btn" onclick="document.getElementById('theme-workshop').classList.remove('translate-y-[150%]'); this.classList.add('translate-y-[150%]')" class="fixed bottom-6 right-6 z-[90] w-12 h-12 rounded-full bg-theme-30 flex items-center justify-center text-theme-primary hover:scale-110 transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] shadow-xl border border-theme-border group translate-y-[150%]">
        <iconify-icon icon="solar:palette-round-linear" class="text-xl group-hover:rotate-45 transition-transform duration-300"></iconify-icon>
    </button>
"""

# replace the old panel
html = re.sub(r'<!-- Theme Workshop Panel -->.*?</button>\s*(<script>.*?</script>)?', new_panel + r'\1', html, flags=re.DOTALL)

with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html)
print("Deep refactoring complete.")
