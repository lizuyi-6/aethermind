#!/bin/bash
# 修复依赖安装脚本
# 解决 jiter 版本冲突问题

set -e

echo "=========================================="
echo "  安装项目依赖（修复版本冲突）"
echo "=========================================="
echo ""

# 升级 pip
echo "📦 升级 pip..."
pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 先安装 jiter（使用可用版本）
echo "📦 安装 jiter..."
pip3 install "jiter>=0.9.0,<1.0" -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  jiter 安装失败，尝试安装最新版本..."
    pip3 install jiter -i https://pypi.tuna.tsinghua.edu.cn/simple
}
echo ""

# 安装 openai（不指定严格版本，让 pip 自动解决依赖）
echo "📦 安装 openai..."
pip3 install "openai>=1.0.0,<2.0.0" -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  尝试安装兼容版本..."
    pip3 install "openai>=1.0.0" --no-deps -i https://pypi.tuna.tsinghua.edu.cn/simple
    pip3 install "jiter>=0.9.0" "httpx>=0.24.0" "pydantic>=2.0.0" -i https://pypi.tuna.tsinghua.edu.cn/simple
}
echo ""

# 安装其他依赖
echo "📦 安装其他依赖..."
pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  部分依赖安装失败，尝试逐个安装..."
    pip3 install python-dotenv PyPDF2 python-docx pandas openpyxl flask flask-cors markdown weasyprint reportlab -i https://pypi.tuna.tsinghua.edu.cn/simple
}
echo ""

echo "=========================================="
echo "  依赖安装完成"
echo "=========================================="
echo ""
echo "验证安装:"
pip3 list | grep -E "openai|flask|jiter"

