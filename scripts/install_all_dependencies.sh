#!/bin/bash
# 完整依赖安装脚本（系统依赖 + Python 依赖）

set -e

echo "=========================================="
echo "  完整依赖安装脚本"
echo "=========================================="
echo ""

# 1. 安装系统依赖
echo "步骤 1/3: 安装系统级依赖..."
if [ -f "install_system_dependencies.sh" ]; then
    chmod +x install_system_dependencies.sh
    ./install_system_dependencies.sh
else
    echo "⚠️  未找到 install_system_dependencies.sh，尝试自动安装..."
    
    # 自动检测并安装
    if command -v yum &> /dev/null; then
        echo "使用 yum 安装依赖..."
        yum groupinstall -y "Development Tools" || true
        yum install -y python3-devel libxml2-devel libxslt-devel libffi-devel openssl-devel
    elif command -v apt-get &> /dev/null; then
        echo "使用 apt-get 安装依赖..."
        apt-get update
        apt-get install -y build-essential python3-dev libxml2-dev libxslt1-dev libffi-dev libssl-dev
    else
        echo "❌ 无法自动安装系统依赖，请手动安装"
        exit 1
    fi
fi
echo ""

# 2. 升级 pip
echo "步骤 2/3: 升级 pip..."
pip3 install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 3. 安装 Python 依赖
echo "步骤 3/3: 安装 Python 依赖..."
echo ""

# 先安装 wheel（用于构建二进制包）
echo "安装 wheel..."
pip3 install wheel -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 先安装 jiter（使用可用版本）
echo "安装 jiter..."
pip3 install "jiter>=0.9.0,<1.0" -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  jiter 安装失败，尝试安装最新版本..."
    pip3 install jiter -i https://pypi.tuna.tsinghua.edu.cn/simple
}
echo ""

# 安装 openai
echo "安装 openai..."
pip3 install "openai>=1.0.0,<2.0.0" -i https://pypi.tuna.tsinghua.edu.cn/simple
echo ""

# 安装其他依赖（逐个安装以便定位问题）
echo "安装其他依赖..."
pip3 install python-dotenv -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install PyPDF2 -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install python-docx -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install pandas -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install openpyxl -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install flask -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install flask-cors -i https://pypi.tuna.tsinghua.edu.cn/simple
pip3 install markdown -i https://pypi.tuna.tsinghua.edu.cn/simple

# weasyprint 和 reportlab 可能需要额外依赖
echo "安装 PDF 生成库..."
pip3 install reportlab -i https://pypi.tuna.tsinghua.edu.cn/simple

# weasyprint 依赖较多，如果失败可以跳过
pip3 install weasyprint -i https://pypi.tuna.tsinghua.edu.cn/simple || {
    echo "⚠️  weasyprint 安装失败，可能需要额外系统依赖"
    echo "   可以稍后手动安装: pip3 install weasyprint"
}
echo ""

echo "=========================================="
echo "  依赖安装完成"
echo "=========================================="
echo ""
echo "验证安装:"
pip3 list | grep -E "openai|flask|jiter|python-docx|lxml"

