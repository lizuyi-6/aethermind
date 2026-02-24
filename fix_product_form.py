import re

def process_file():
    filepath = 'x:/test_2/templates/product_form.html'
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    # 替换各种残留的 indigo, purple, blue 为主题色
    replacements = [
        # 导航栏 logo 圆点
        ('from-indigo-500', 'from-[rgb(var(--ds-accent))]'),
        ('to-sky-400', 'to-[rgb(var(--ds-accent-2))]'),
        
        # 文本
        ('text-indigo-200', 'text-[rgb(var(--ds-accent-2))]'),
        ('text-indigo-300', 'text-[rgb(var(--ds-accent-2))]'),
        ('text-indigo-400', 'text-[rgb(var(--ds-accent-2))]'),
        ('text-purple-400', 'text-[rgb(var(--ds-accent-2))]'), # 商业计划书 icon
        
        # 背景
        ('bg-indigo-500/10', 'bg-[rgb(var(--ds-accent))]/10'),
        ('bg-indigo-500/20', 'bg-[rgb(var(--ds-accent))]/20'),
        ('bg-indigo-500/30', 'bg-[rgb(var(--ds-accent))]/30'),
        ('bg-purple-500/20', 'bg-[rgb(var(--ds-accent-2))]/20'), # 暂用 accent-2 区分
        
        # 边框
        ('border-indigo-500/20', 'border-[rgb(var(--ds-accent))]/20'),
        ('border-indigo-500/30', 'border-[rgb(var(--ds-accent))]/30'),
        ('hover:border-indigo-500/30', 'hover:border-[rgb(var(--ds-accent))]/30'),
        
        # peer-checked 系列 (Radio buttons)
        ('peer-checked:border-indigo-500', 'peer-checked:border-[rgb(var(--ds-accent))]'),
        ('peer-checked:bg-indigo-500/10', 'peer-checked:bg-[rgb(var(--ds-accent))]/10'),
        ('peer-checked:bg-indigo-500', 'peer-checked:bg-[rgb(var(--ds-accent))]'),
        
        # checkboxes / inputs focus
        ('text-indigo-600', 'text-[rgb(var(--ds-accent))]'),
        ('focus:ring-indigo-500', 'focus:ring-[rgb(var(--ds-accent))]'),
        
        # Submit Button
        ('from-indigo-600', 'from-[rgb(var(--ds-accent))]'),
        ('to-blue-600', 'to-[rgb(var(--ds-accent-2))]'),
        ('hover:from-indigo-500', 'hover:from-[rgb(var(--ds-accent))]/80'),
        ('hover:to-blue-500', 'hover:to-[rgb(var(--ds-accent-2))]/80'),
        ('shadow-indigo-900/20', 'shadow-[rgb(var(--ds-accent))]/20')
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
        
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("Done handling hardcoded accents")

process_file()
