#!/bin/bash
# 在服务器上安装PDF生成所需的依赖

echo "=========================================="
echo "  安装PDF生成依赖"
echo "=========================================="
echo ""

# 使用python3 -m pip来避免pip版本冲突
PYTHON_CMD="/usr/local/python3.11/bin/python3"
PIP_CMD="$PYTHON_CMD -m pip"

# 检查Python路径
if [ ! -f "$PYTHON_CMD" ]; then
    echo "❌ 错误: 找不到Python: $PYTHON_CMD"
    echo "请检查Python路径"
    exit 1
fi

echo "📦 使用: $PIP_CMD"
echo ""

# 升级pip
echo "[1/4] 升级pip..."
$PIP_CMD install --upgrade pip --user
if [ $? -ne 0 ]; then
    echo "⚠️  警告: pip升级失败，继续安装..."
fi

# 安装markdown
echo ""
echo "[2/4] 安装markdown..."
$PIP_CMD install markdown --user
if [ $? -ne 0 ]; then
    echo "❌ 错误: markdown安装失败"
    exit 1
fi

# 安装reportlab（备用方案，不依赖系统库）
echo ""
echo "[3/4] 安装reportlab..."
$PIP_CMD install reportlab --user
if [ $? -ne 0 ]; then
    echo "⚠️  警告: reportlab安装失败，将使用备用方案"
fi

# 尝试安装weasyprint（需要系统依赖）
echo ""
echo "[4/4] 尝试安装weasyprint..."
echo "注意: weasyprint需要系统库支持，如果失败将使用reportlab作为备用"

# 先检查系统依赖
if command -v apt-get >/dev/null 2>&1; then
    echo "检测到Debian/Ubuntu系统，安装系统依赖..."
    sudo apt-get update
    sudo apt-get install -y python3-dev python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info 2>/dev/null || echo "系统依赖安装失败，将使用reportlab"
elif command -v yum >/dev/null 2>&1; then
    echo "检测到CentOS/RHEL系统，安装系统依赖..."
    sudo yum install -y python3-devel cairo pango gdk-pixbuf2 libffi-devel 2>/dev/null || echo "系统依赖安装失败，将使用reportlab"
fi

# 尝试安装weasyprint
$PIP_CMD install weasyprint --user 2>/dev/null
if [ $? -eq 0 ]; then
    echo "✅ weasyprint安装成功"
else
    echo "⚠️  weasyprint安装失败，将使用reportlab作为备用方案"
fi

echo ""
echo "=========================================="
echo "  安装完成"
echo "=========================================="
echo ""
echo "已安装的库："
$PIP_CMD list | grep -E "markdown|reportlab|weasyprint" || echo "请检查安装状态"
echo ""
echo "如果weasyprint安装失败，系统会自动使用reportlab生成PDF"
echo ""

