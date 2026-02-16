#!/bin/bash
# 快速安装依赖脚本（使用预编译包，避免编译）

set -e

echo "=========================================="
echo "  快速安装依赖（使用预编译包）"
echo "=========================================="
echo ""

# 1. 升级 pip
echo "步骤 1: 升级 pip..."
pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 2. 安装 wheel（确保使用二进制包）
echo "步骤 2: 安装 wheel..."
pip3 install wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 3. 优先安装预编译的 lxml（如果可用）
echo "步骤 3: 尝试安装预编译的 lxml..."
pip3 install lxml -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  预编译包不可用，将使用源码编译（可能需要较长时间）"
    echo "   如果编译时间过长，可以按 Ctrl+C 中断，然后使用替代方案"
}
echo ""

# 4. 安装其他依赖（使用预编译包）
echo "步骤 4: 安装其他依赖..."
pip3 install "jiter>=0.9.0,<1.0" -i https://pypi.tuna.tsinghua.edu.cn/simple || pip3 install jiter -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install "openai>=1.0.0,<2.0.0" -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install python-dotenv -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install PyPDF2 -i https://pypi.tuna.tsinghua.edu.cn/simple

# python-docx 依赖 lxml，如果 lxml 安装失败，可以稍后处理
echo "安装 python-docx（依赖 lxml）..."
pip3 install python-docx -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  python-docx 安装失败（可能因为 lxml），可以稍后安装"
}

pip3 install pandas openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install flask flask-cors -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install markdown reportlab -i https://pypi.tuna.tsinghua.edu.cn/simple

# weasyprint 可选
pip3 install weasyprint -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  weasyprint 安装失败，可以稍后安装"
}
echo ""

echo "=========================================="
echo "  安装完成"
echo "=========================================="
echo ""
echo "验证安装:"
pip3 list | grep -E "openai|flask|lxml|python-docx"

