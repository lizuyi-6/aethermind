#!/bin/bash
# 修复 blinker 冲突的安装脚本

set -e

echo "=========================================="
echo "  安装依赖（修复 blinker 冲突）"
echo "=========================================="
echo ""

# 升级 pip
echo "步骤 1: 升级 pip..."
pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 安装 wheel
echo "步骤 2: 安装 wheel..."
pip3 install wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 安装依赖时忽略已安装的包（解决 blinker 冲突）
echo "步骤 3: 安装依赖（忽略已安装的包）..."
pip3 install --ignore-installed blinker -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install --ignore-installed "jiter>=0.9.0,<1.0" -i https://pypi.tuna.tsinghua.edu.cn/simple || pip3 install --ignore-installed jiter -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install --ignore-installed "openai>=1.0.0,<2.0.0" -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install --ignore-installed python-dotenv -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install --ignore-installed PyPDF2 -i https://pypi.tuna.tsinghua.edu.cn/simple

# lxml 和 python-docx（如果之前编译完成）
pip3 install --ignore-installed lxml -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  lxml 安装失败，跳过..."
}
pip3 install --ignore-installed python-docx -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  python-docx 安装失败（可能因为 lxml），跳过..."
}

pip3 install --ignore-installed pandas openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install --ignore-installed flask flask-cors -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install --ignore-installed markdown reportlab -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install --ignore-installed weasyprint -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  weasyprint 安装失败，跳过..."
}
echo ""

echo "=========================================="
echo "  安装完成"
echo "=========================================="
echo ""
echo "验证安装:"
pip3 list | grep -E "openai|flask|blinker"

