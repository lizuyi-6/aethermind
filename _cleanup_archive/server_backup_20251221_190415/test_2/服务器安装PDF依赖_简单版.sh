#!/bin/bash
# 简单版本：只安装reportlab（不依赖系统库）

echo "安装PDF生成依赖（使用reportlab）..."

# 使用python3 -m pip
/usr/local/python3.11/bin/python3 -m pip install markdown reportlab --user

if [ $? -eq 0 ]; then
    echo "✅ 安装成功！"
    echo ""
    echo "已安装："
    echo "  - markdown: Markdown解析"
    echo "  - reportlab: PDF生成（备用方案）"
    echo ""
    echo "注意: 如果weasyprint不可用，系统会自动使用reportlab生成PDF"
else
    echo "❌ 安装失败"
    exit 1
fi

