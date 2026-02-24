import re

file_path = r'x:\test_2\templates\landing.html'

with open(file_path, 'r', encoding='utf-8') as f:
    html = f.read()

# 1. Add the CSS variables for the 4 new styles
css_insertion = """
        [data-theme="cloud-dancer"] {
            --theme-primary: 30 30 35;
            --theme-secondary: 150 150 160;
            --theme-bg-60: 252 250 248;
            --theme-bg-30: 255 255 255;
            --theme-bg-sidebar: 248 245 242;
            --theme-border: 240 238 235;
            --theme-accent-10: 204 255 0;
            --theme-accent-hover: 180 230 0;
            --theme-accent-light: 220 255 100;
            --theme-glass-bg: 255 255 255;
        }

        [data-theme="serotonin"] {
            --theme-primary: 20 50 150;
            --theme-secondary: 100 130 180;
            --theme-bg-60: 242 248 255;
            --theme-bg-30: 255 255 255;
            --theme-bg-sidebar: 235 242 255;
            --theme-border: 210 230 255;
            --theme-accent-10: 255 85 0;
            --theme-accent-hover: 230 70 0;
            --theme-accent-light: 255 130 80;
            --theme-glass-bg: 255 255 255;
        }

        [data-theme="neo-terra"] {
            --theme-primary: 65 50 40;
            --theme-secondary: 140 120 110;
            --theme-bg-60: 240 236 225;
            --theme-bg-30: 248 245 238;
            --theme-bg-sidebar: 232 228 215;
            --theme-border: 220 215 200;
            --theme-accent-10: 215 70 50;
            --theme-accent-hover: 190 50 40;
            --theme-accent-light: 235 110 90;
            --theme-glass-bg: 248 245 238;
        }

        [data-theme="acid-holo"] {
            --theme-primary: 40 20 60;
            --theme-secondary: 100 160 140;
            --theme-bg-60: 245 250 235;
            --theme-bg-30: 252 255 245;
            --theme-bg-sidebar: 238 245 225;
            --theme-border: 225 235 210;
            --theme-accent-10: 255 0 128;
            --theme-accent-hover: 230 0 110;
            --theme-accent-light: 255 80 160;
            --theme-glass-bg: 252 255 245;
        }
"""

if '[data-theme="cloud-dancer"]' not in html:
    html = html.replace('</style>', css_insertion + '\n    </style>')

# 2. Add the buttons to the panel
buttons_html = """
                <div class="mt-4 pt-4 border-t border-theme-border/50 space-y-2">
                    <div class="text-[10px] font-medium text-theme-secondary/70 uppercase tracking-widest pl-1 mb-2">2026 Avant-Garde (独立先锋)</div>
                    <button onclick="setTheme('cloud-dancer')" class="w-full flex items-center justify-between p-2 rounded hover:bg-theme-border/30 transition-colors group">
                        <span class="text-sm text-theme-secondary group-hover:text-theme-primary transition-colors">云舞者 (Cloud & Lime)</span>
                        <div class="flex gap-1">
                            <div class="w-3 h-3 rounded-full bg-[#1e1e23]"></div>
                            <div class="w-3 h-3 rounded-full bg-[#ccff00]"></div>
                        </div>
                    </button>
                    <button onclick="setTheme('serotonin')" class="w-full flex items-center justify-between p-2 rounded hover:bg-theme-border/30 transition-colors group">
                        <span class="text-sm text-theme-secondary group-hover:text-theme-primary transition-colors">血清素滑翔 (Serotonin)</span>
                        <div class="flex gap-1">
                            <div class="w-3 h-3 rounded-full bg-[#143296]"></div>
                            <div class="w-3 h-3 rounded-full bg-[#ff5500]"></div>
                        </div>
                    </button>
                    <button onclick="setTheme('neo-terra')" class="w-full flex items-center justify-between p-2 rounded hover:bg-theme-border/30 transition-colors group">
                        <span class="text-sm text-theme-secondary group-hover:text-theme-primary transition-colors">新野兽派 (Neo Terra)</span>
                        <div class="flex gap-1">
                            <div class="w-3 h-3 rounded-full bg-[#413228]"></div>
                            <div class="w-3 h-3 rounded-full bg-[#d74632]"></div>
                        </div>
                    </button>
                    <button onclick="setTheme('acid-holo')" class="w-full flex items-center justify-between p-2 rounded hover:bg-theme-border/30 transition-colors group">
                        <span class="text-sm text-theme-secondary group-hover:text-theme-primary transition-colors">酸性全息 (Acid Holo)</span>
                        <div class="flex gap-1">
                            <div class="w-3 h-3 rounded-full bg-[#28143c]"></div>
                            <div class="w-3 h-3 rounded-full bg-[#ff0080]"></div>
                        </div>
                    </button>
                </div>
"""

# Insert right before the panel is closed
if '2026 Avant-Garde' not in html:
    # We find the end of the space-y-2 div containing the current buttons
    html = html.replace('<!-- End of default themes --></div>\n            </div>\n        </div>', '<!-- End of default themes --></div>' + buttons_html + '\n            </div>\n        </div>')
    # Actually, the div ends aren't marked with comments. Let's find the specific block.
    # The last default theme button is "北欧极简白 (Nordic Minimal)"
    target = '北欧极简白 (Nordic Minimal)</span>\n                        <div class="flex gap-1">\n                            <div class="w-3 h-3 rounded-full bg-[#0f172a]"></div>\n                            <div class="w-3 h-3 rounded-full bg-[#f8fafc]"></div>\n                        </div>\n                    </button>\n                </div>'
    
    if target in html:
        html = html.replace(target, target + buttons_html)
    else:
        print("Couldn't find the insertion point for buttons.")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(html)

print("Injected 4 new 2026 avant-garde themes.")
