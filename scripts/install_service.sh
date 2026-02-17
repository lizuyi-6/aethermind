#!/bin/bash
# systemd服务安装脚本
# 用于将Flask应用安装为systemd服务，确保SSH断开后继续运行

set -e

echo "=========================================="
echo "  Flask应用 systemd服务安装脚本"
echo "=========================================="
echo ""

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then 
    echo "❌ 错误: 请使用sudo运行此脚本"
    echo "   使用方法: sudo ./install_service.sh"
    exit 1
fi

# 获取当前目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SERVICE_FILE="$SCRIPT_DIR/flask-app.service"

# 检查服务文件是否存在
if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ 错误: 未找到服务文件: $SERVICE_FILE"
    exit 1
fi

# 读取配置
echo "📋 当前配置:"
echo "   服务文件: $SERVICE_FILE"
echo ""

# 询问项目路径
read -p "请输入项目路径 [默认: /var/www/html]: " PROJECT_DIR
PROJECT_DIR=${PROJECT_DIR:-/var/www/html}

# 检查项目路径是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo "❌ 错误: 项目路径不存在: $PROJECT_DIR"
    exit 1
fi

# 检查app.py是否存在
if [ ! -f "$PROJECT_DIR/app.py" ]; then
    echo "❌ 错误: 未找到app.py文件: $PROJECT_DIR/app.py"
    exit 1
fi

# 自动检测Python路径
echo "🔍 正在检测Python路径..."
PYTHON_PATH=""

# 尝试常见的Python路径
if command -v python3 >/dev/null 2>&1; then
    PYTHON_PATH=$(which python3)
    echo "   ✅ 找到: $PYTHON_PATH"
elif [ -f "/usr/bin/python3" ]; then
    PYTHON_PATH="/usr/bin/python3"
    echo "   ✅ 找到: $PYTHON_PATH"
elif [ -f "/usr/local/bin/python3" ]; then
    PYTHON_PATH="/usr/local/bin/python3"
    echo "   ✅ 找到: $PYTHON_PATH"
elif [ -f "/usr/local/python3.11/bin/python3" ]; then
    PYTHON_PATH="/usr/local/python3.11/bin/python3"
    echo "   ✅ 找到: $PYTHON_PATH"
elif [ -f "/usr/local/python3/bin/python3" ]; then
    PYTHON_PATH="/usr/local/python3/bin/python3"
    echo "   ✅ 找到: $PYTHON_PATH"
else
    echo "   ⚠️  未自动检测到Python路径"
fi

# 如果未找到，询问用户
if [ -z "$PYTHON_PATH" ] || [ ! -f "$PYTHON_PATH" ]; then
    echo ""
    echo "请手动输入Python3路径，或按回车使用默认路径"
    echo "常见路径："
    echo "  - /usr/bin/python3"
    echo "  - /usr/local/bin/python3"
    echo "  - /usr/local/python3.11/bin/python3"
    echo ""
    read -p "请输入Python3路径 [默认: /usr/bin/python3]: " USER_PYTHON_PATH
    PYTHON_PATH=${USER_PYTHON_PATH:-/usr/bin/python3}
fi

# 最终检查Python是否存在
if [ ! -f "$PYTHON_PATH" ]; then
    echo ""
    echo "❌ 错误: Python路径不存在: $PYTHON_PATH"
    echo ""
    echo "请先确认Python已安装，然后手动指定路径："
    echo "  1. 查找Python: which python3"
    echo "  2. 或查找所有Python: find /usr -name python3 2>/dev/null"
    echo "  3. 重新运行此脚本并输入正确的路径"
    exit 1
fi

# 验证Python版本
echo "   📋 Python版本:"
$PYTHON_PATH --version 2>&1 || {
    echo "   ❌ 无法执行Python，请检查路径是否正确"
    exit 1
}

# 询问运行用户
read -p "请输入运行用户 [默认: root]: " RUN_USER
RUN_USER=${RUN_USER:-root}

# 创建临时服务文件
TEMP_SERVICE="/tmp/flask-app.service"
cp "$SERVICE_FILE" "$TEMP_SERVICE"

# 替换路径
sed -i "s|WorkingDirectory=/var/www/html|WorkingDirectory=$PROJECT_DIR|g" "$TEMP_SERVICE"
sed -i "s|ExecStart=/usr/local/python3.11/bin/python3 /var/www/html/app.py|ExecStart=$PYTHON_PATH $PROJECT_DIR/app.py|g" "$TEMP_SERVICE"
sed -i "s|User=root|User=$RUN_USER|g" "$TEMP_SERVICE"

# 询问是否配置环境变量
echo ""
read -p "是否配置环境变量? (y/n) [默认: n]: " CONFIG_ENV
if [ "$CONFIG_ENV" = "y" ]; then
    echo ""
    echo "环境变量配置（留空跳过）:"
    read -p "MODEL_PROVIDER [默认: custom]: " MODEL_PROVIDER
    MODEL_PROVIDER=${MODEL_PROVIDER:-custom}
    
    read -p "API_BASE_URL [默认: http://60.10.230.156:1025/v1]: " API_BASE_URL
    API_BASE_URL=${API_BASE_URL:-http://60.10.230.156:1025/v1}
    
    read -p "MODEL_NAME [默认: qwen3-32b]: " MODEL_NAME
    MODEL_NAME=${MODEL_NAME:-qwen3-32b}
    
    read -p "OPENAI_API_KEY: " OPENAI_API_KEY
    read -p "DASHSCOPE_API_KEY: " DASHSCOPE_API_KEY
    
    # 添加环境变量到服务文件
    ENV_LINES=""
    [ -n "$MODEL_PROVIDER" ] && ENV_LINES="${ENV_LINES}Environment=\"MODEL_PROVIDER=$MODEL_PROVIDER\"\n"
    [ -n "$API_BASE_URL" ] && ENV_LINES="${ENV_LINES}Environment=\"API_BASE_URL=$API_BASE_URL\"\n"
    [ -n "$MODEL_NAME" ] && ENV_LINES="${ENV_LINES}Environment=\"MODEL_NAME=$MODEL_NAME\"\n"
    [ -n "$OPENAI_API_KEY" ] && ENV_LINES="${ENV_LINES}Environment=\"OPENAI_API_KEY=$OPENAI_API_KEY\"\n"
    [ -n "$DASHSCOPE_API_KEY" ] && ENV_LINES="${ENV_LINES}Environment=\"DASHSCOPE_API_KEY=$DASHSCOPE_API_KEY\"\n"
    
    # 在ExecStart之前插入环境变量
    sed -i "/^ExecStart=/i\\$ENV_LINES" "$TEMP_SERVICE"
fi

# 显示配置摘要
echo ""
echo "=========================================="
echo "  配置摘要"
echo "=========================================="
echo "项目路径: $PROJECT_DIR"
echo "Python路径: $PYTHON_PATH"
echo "运行用户: $RUN_USER"
echo "服务文件: /etc/systemd/system/flask-app.service"
echo ""

# 确认安装
read -p "确认安装? (y/n): " CONFIRM
if [ "$CONFIRM" != "y" ]; then
    echo "已取消安装"
    rm -f "$TEMP_SERVICE"
    exit 0
fi

# 复制服务文件
echo ""
echo "📦 安装服务文件..."
cp "$TEMP_SERVICE" /etc/systemd/system/flask-app.service
rm -f "$TEMP_SERVICE"

# 重新加载systemd
echo "🔄 重新加载systemd配置..."
systemctl daemon-reload

# 启用服务
echo "✅ 启用服务（开机自启）..."
systemctl enable flask-app.service

# 询问是否立即启动
echo ""
read -p "是否立即启动服务? (y/n) [默认: y]: " START_NOW
START_NOW=${START_NOW:-y}

if [ "$START_NOW" = "y" ]; then
    echo "🚀 启动服务..."
    systemctl start flask-app.service
    
    # 等待服务启动
    sleep 2
    
    # 检查服务状态
    if systemctl is-active --quiet flask-app.service; then
        echo "✅ 服务启动成功!"
    else
        echo "❌ 服务启动失败，请查看日志:"
        echo "   sudo journalctl -u flask-app.service -n 50"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "  安装完成!"
echo "=========================================="
echo ""
echo "常用命令:"
echo "  查看状态: sudo systemctl status flask-app.service"
echo "  查看日志: sudo journalctl -u flask-app.service -f"
echo "  启动服务: sudo systemctl start flask-app.service"
echo "  停止服务: sudo systemctl stop flask-app.service"
echo "  重启服务: sudo systemctl restart flask-app.service"
echo "  禁用自启: sudo systemctl disable flask-app.service"
echo ""

