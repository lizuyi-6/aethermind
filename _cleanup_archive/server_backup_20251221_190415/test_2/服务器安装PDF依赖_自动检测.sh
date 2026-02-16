#!/bin/bash
# 自动检测Python路径并安装PDF依赖

echo "=========================================="
echo "  安装PDF生成依赖"
echo "=========================================="
echo ""

# 自动检测Python路径
PYTHON_CMD=""
if [ -f "/usr/local/python3.11/bin/python3" ]; then
    PYTHON_CMD="/usr/local/python3.11/bin/python3"
elif [ -f "/usr/bin/python3" ]; then
    PYTHON_CMD="/usr/bin/python3"
elif command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD=$(which python3)
else
    echo "❌ 错误: 找不到Python3"
    exit 1
fi

echo "✅ 找到Python: $PYTHON_CMD"
$PYTHON_CMD --version
echo ""

# 使用python3 -m pip安装
echo "📦 安装markdown和reportlab..."
$PYTHON_CMD -m pip install markdown reportlab --user

if [ $? -eq 0 ]; then
    echo ""
    echo "=========================================="
    echo "  ✅ 安装成功！"
    echo "=========================================="
    echo ""
    echo "已安装的库："
    $PYTHON_CMD -m pip list | grep -E "markdown|reportlab" || echo "请检查安装状态"
    echo ""
    echo "现在可以重启服务："
    echo "  sudo systemctl restart flask-app.service"
else
    echo ""
    echo "❌ 安装失败"
    echo ""
    echo "尝试全局安装..."
    $PYTHON_CMD -m pip install markdown reportlab
    if [ $? -eq 0 ]; then
        echo "✅ 全局安装成功！"
    else
        echo "❌ 安装失败，请检查错误信息"
        exit 1
    fi
fi

