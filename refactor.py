import re

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

themes = {
    "default": {
        "theme-primary-50": "#eef2ff",
        "theme-primary-100": "#e0e7ff",
        "theme-primary-200": "#c7d2fe",
        "theme-primary-300": "#a5b4fc",
        "theme-primary-400": "#818cf8",
        "theme-primary-500": "#6366f1",
        "theme-primary-600": "#4f46e5",
        "theme-primary-700": "#4338ca",
        "theme-primary-800": "#3730a3",
        "theme-primary-900": "#312e81",
        "theme-secondary-300": "#7dd3fc",
        "theme-secondary-400": "#38bdf8",
        "theme-secondary-500": "#0ea5e9",
        "theme-secondary-600": "#0284c7",
        "theme-bg": "#030712",
        "theme-bg-alt": "#0B0C0E",
        "theme-bg-panel": "#141416",
        "theme-bg-sidebar": "#0f1115",
        "theme-bg-footer": "#05080f",
    },
    "cyberpunk": {
        "theme-primary-50": "#fdf2f8",
        "theme-primary-100": "#fce7f3",
        "theme-primary-200": "#fbcfe8",
        "theme-primary-300": "#f9a8d4",
        "theme-primary-400": "#f472b6",
        "theme-primary-500": "#ec4899",
        "theme-primary-600": "#db2777",
        "theme-primary-700": "#be185d",
        "theme-primary-800": "#9d174d",
        "theme-primary-900": "#831843",
        "theme-secondary-300": "#5eead4",
        "theme-secondary-400": "#2dd4bf",
        "theme-secondary-500": "#14b8a6",
        "theme-secondary-600": "#0d9488",
        "theme-bg": "#05000a",
        "theme-bg-alt": "#0a0014",
        "theme-bg-panel": "#0f001a",
        "theme-bg-sidebar": "#0d0016",
        "theme-bg-footer": "#07000d",
    },
    "emerald": {
        "theme-primary-50": "#ecfdf5",
        "theme-primary-100": "#d1fae5",
        "theme-primary-200": "#a7f3d0",
        "theme-primary-300": "#6ee7b7",
        "theme-primary-400": "#34d399",
        "theme-primary-500": "#10b981",
        "theme-primary-600": "#059669",
        "theme-primary-700": "#047857",
        "theme-primary-800": "#065f46",
        "theme-primary-900": "#064e3b",
        "theme-secondary-300": "#fcd34d",
        "theme-secondary-400": "#fbbf24",
        "theme-secondary-500": "#f59e0b",
        "theme-secondary-600": "#d97706",
        "theme-bg": "#020604",
        "theme-bg-alt": "#06120a",
        "theme-bg-panel": "#091a0e",
        "theme-bg-sidebar": "#050f08",
        "theme-bg-footer": "#030a06",
    },
    "crimson": {
        "theme-primary-50": "#fff1f2",
        "theme-primary-100": "#ffe4e6",
        "theme-primary-200": "#fecdd3",
        "theme-primary-300": "#fda4af",
        "theme-primary-400": "#fb7185",
        "theme-primary-500": "#f43f5e",
        "theme-primary-600": "#e11d48",
        "theme-primary-700": "#be123c",
        "theme-primary-800": "#9f1239",
        "theme-primary-900": "#881337",
        "theme-secondary-300": "#fdba74",
        "theme-secondary-400": "#fb923c",
        "theme-secondary-500": "#f97316",
        "theme-secondary-600": "#ea580c",
        "theme-bg": "#080304",
        "theme-bg-alt": "#120508",
        "theme-bg-panel": "#1a080b",
        "theme-bg-sidebar": "#0f0406",
        "theme-bg-footer": "#0a0305",
    },
    "minimal": {
        "theme-primary-50": "#f8fafc",
        "theme-primary-100": "#f1f5f9",
        "theme-primary-200": "#e2e8f0",
        "theme-primary-300": "#cbd5e1",
        "theme-primary-400": "#94a3b8",
        "theme-primary-500": "#64748b",
        "theme-primary-600": "#475569",
        "theme-primary-700": "#334155",
        "theme-primary-800": "#1e293b",
        "theme-primary-900": "#0f172a",
        "theme-secondary-300": "#d4d4d8",
        "theme-secondary-400": "#a1a1aa",
        "theme-secondary-500": "#71717a",
        "theme-secondary-600": "#52525b",
        "theme-bg": "#000000",
        "theme-bg-alt": "#09090b",
        "theme-bg-panel": "#18181b",
        "theme-bg-sidebar": "#0f0f11",
        "theme-bg-footer": "#050505",
    }
}

theme_styles = "\n".join([gen_theme(name, colors) for name, colors in themes.items()])

with open('x:/test_2/templates/landing.html', 'r', encoding='utf-8') as f:
    html = f.read()

# Replace hardcoded hex colors
html = html.replace('[#030712]', 'theme-bg')
html = html.replace('[#0B0C0E]', 'theme-bg-alt')
html = html.replace('[#141416]', 'theme-bg-panel')
html = html.replace('[#0f1115]', 'theme-bg-sidebar')
html = html.replace('[#05080f]', 'theme-bg-footer')

# Replace rgba wrappers
html = html.replace('rgba(15, 23, 42, 0.6)', 'rgb(var(--theme-bg-sidebar) / 0.6)')
html = html.replace('rgba(30, 41, 59, 0.4)', 'rgb(var(--theme-bg-alt) / 0.4)')
html = html.replace('rgba(15, 23, 42, 0.4)', 'rgb(var(--theme-bg-sidebar) / 0.4)')
html = html.replace('rgba(56, 189, 248, 0.3)', 'rgb(var(--theme-secondary-400) / 0.3)')
html = html.replace('rgba(56, 189, 248, 0.15)', 'rgb(var(--theme-secondary-400) / 0.15)')
html = html.replace('rgba(3, 7, 18, 0)', 'rgb(var(--theme-bg) / 0)')
html = html.replace('background-color: #030712;', 'background-color: rgb(var(--theme-bg));')

# Inject tailwind config before </head>
tailwind_config = """
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        indigo: {
                            50: 'rgb(var(--theme-primary-50) / <alpha-value>)',
                            100: 'rgb(var(--theme-primary-100) / <alpha-value>)',
                            200: 'rgb(var(--theme-primary-200) / <alpha-value>)',
                            300: 'rgb(var(--theme-primary-300) / <alpha-value>)',
                            400: 'rgb(var(--theme-primary-400) / <alpha-value>)',
                            500: 'rgb(var(--theme-primary-500) / <alpha-value>)',
                            600: 'rgb(var(--theme-primary-600) / <alpha-value>)',
                            700: 'rgb(var(--theme-primary-700) / <alpha-value>)',
                            800: 'rgb(var(--theme-primary-800) / <alpha-value>)',
                            900: 'rgb(var(--theme-primary-900) / <alpha-value>)',
                        },
                        sky: {
                            300: 'rgb(var(--theme-secondary-300) / <alpha-value>)',
                            400: 'rgb(var(--theme-secondary-400) / <alpha-value>)',
                            500: 'rgb(var(--theme-secondary-500) / <alpha-value>)',
                            600: 'rgb(var(--theme-secondary-600) / <alpha-value>)',
                        },
                        theme: {
                            bg: 'rgb(var(--theme-bg) / <alpha-value>)',
                            'bg-alt': 'rgb(var(--theme-bg-alt) / <alpha-value>)',
                            'bg-panel': 'rgb(var(--theme-bg-panel) / <alpha-value>)',
                            'bg-sidebar': 'rgb(var(--theme-bg-sidebar) / <alpha-value>)',
                            'bg-footer': 'rgb(var(--theme-bg-footer) / <alpha-value>)',
                        }
                    }
                }
            }
        }
    </script>
"""

html = html.replace('</head>', tailwind_config + '\n</head>')
html = html.replace('</style>', theme_styles + '\n    </style>')

workshop_panel = """
    <!-- Theme Workshop Panel -->
    <div class="fixed bottom-6 right-6 z-[100] glass-card rounded-2xl p-4 shadow-2xl border border-white/10 w-64 transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] translate-y-0" id="theme-workshop">
        <div class="flex items-center justify-between mb-4">
            <div class="flex items-center gap-2">
                <iconify-icon icon="solar:palette-round-linear" class="text-white text-lg"></iconify-icon>
                <h3 class="text-sm font-medium text-white">主题工作坊</h3>
            </div>
            <button onclick="document.getElementById('theme-workshop').classList.add('translate-y-[150%]'); document.getElementById('theme-toggle-btn').classList.remove('translate-y-[150%]')" class="text-slate-400 hover:text-white transition-colors" title="隐藏面板">
                <iconify-icon icon="solar:close-square-linear" width="20"></iconify-icon>
            </button>
        </div>
        <div class="space-y-3">
            <button onclick="setTheme('default')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors border border-transparent hover:border-white/10 group">
                <span class="text-xs text-slate-300 group-hover:text-white transition-colors">Midnight Indigo</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#6366f1] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#030712] border border-white/20 shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('cyberpunk')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors border border-transparent hover:border-white/10 group">
                <span class="text-xs text-slate-300 group-hover:text-white transition-colors">Cyberpunk Neon</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#ec4899] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#05000a] border border-white/20 shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('emerald')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors border border-transparent hover:border-white/10 group">
                <span class="text-xs text-slate-300 group-hover:text-white transition-colors">Emerald Forest</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#10b981] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#020604] border border-white/20 shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('crimson')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors border border-transparent hover:border-white/10 group">
                <span class="text-xs text-slate-300 group-hover:text-white transition-colors">Sunset Crimson</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#f43f5e] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#080304] border border-white/20 shadow-sm"></div>
                </div>
            </button>
            <button onclick="setTheme('minimal')" class="w-full flex items-center justify-between p-2 rounded-lg hover:bg-white/5 transition-colors border border-transparent hover:border-white/10 group">
                <span class="text-xs text-slate-300 group-hover:text-white transition-colors">Mono Minimal</span>
                <div class="flex gap-1">
                    <div class="w-3 h-3 rounded-full bg-[#64748b] shadow-sm"></div>
                    <div class="w-3 h-3 rounded-full bg-[#000000] border border-white/20 shadow-sm"></div>
                </div>
            </button>
        </div>
    </div>
    
    <!-- Floating toggle button to bring panel back -->
    <button id="theme-toggle-btn" onclick="document.getElementById('theme-workshop').classList.remove('translate-y-[150%]'); this.classList.add('translate-y-[150%]')" class="fixed bottom-6 right-6 z-[90] w-12 h-12 rounded-full glass-card flex items-center justify-center text-white hover:scale-110 transition-transform duration-500 ease-[cubic-bezier(0.34,1.56,0.64,1)] shadow-xl border border-white/10 group translate-y-[150%]">
        <iconify-icon icon="solar:palette-round-linear" class="text-xl group-hover:rotate-45 transition-transform duration-300"></iconify-icon>
    </button>
    
    <script>
        function setTheme(theme) {
            document.documentElement.setAttribute('data-theme', theme);
            localStorage.setItem('selected-theme', theme);
        }
        // Load saved theme
        const savedTheme = localStorage.getItem('selected-theme');
        if (savedTheme) {
            setTheme(savedTheme);
        }
    </script>
"""

html = html.replace('</body>', workshop_panel + '\n</body>')

with open('x:/test_2/templates/landing.html', 'w', encoding='utf-8') as f:
    f.write(html)
print("Landing page refactored with themes.")
