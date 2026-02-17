#!/bin/bash
# 跳过 lxml 安装脚本（如果编译时间过长）

set -e

echo "=========================================="
echo "  安装依赖（跳过 lxml，使用替代方案）"
echo "=========================================="
echo ""

# 升级 pip
pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 安装核心依赖（不包含需要 lxml 的包）
echo "安装核心依赖..."
pip3 install "jiter>=0.9.0,<1.0" -i https://pypi.tuna.tsinghua.edu.cn/simple || pip3 install jiter -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install "openai>=1.0.0,<2.0.0" -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install python-dotenv -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install PyPDF2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install pandas openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install flask flask-cors -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install markdown reportlab -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

echo "⚠️  已跳过 lxml 和 python-docx（需要 lxml）"
echo "   如果项目需要处理 Word 文档，可以稍后安装："
echo "   1. 等待 lxml 编译完成（如果正在编译）"
echo "   2. 或使用: pip3 install lxml python-docx"
echo ""

echo "=========================================="
echo "  核心依赖安装完成"
echo "=========================================="
echo ""
echo "验证安装:"
pip3 list | grep -E "openai|flask"

