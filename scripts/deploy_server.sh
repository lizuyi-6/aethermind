#!/bin/bash
# 服务器一键部署脚本
# 用于在服务器上快速部署 Flask 应用

set -e

echo "=========================================="
echo "  AetherMind - 服务器部署脚本"
echo "=========================================="
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查是否为 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo "⚠️  警告: 建议使用 root 用户运行此脚本"
    echo "   当前用户: $(whoami)"
    read -p "继续? (y/n): " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        exit 1
    fi
fi

echo "📋 项目路径: $SCRIPT_DIR"
echo ""

# 1. 检查 Python3
echo "🔍 检查 Python3..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 python3，请先安装 Python3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "   ✅ $PYTHON_VERSION"
echo ""

# 2. 检查 pip3
echo "🔍 检查 pip3..."
if ! command -v pip3 &> /dev/null; then
    echo "⚠️  未找到 pip3，正在安装..."
    if command -v apt-get &> /dev/null; then
        apt-get update && apt-get install -y python3-pip
    elif command -v yum &> /dev/null; then
        yum install -y python3-pip
    else
        echo "❌ 无法自动安装 pip3，请手动安装"
        exit 1
    fi
fi
echo "   ✅ pip3 已安装"
echo ""

# 3. 安装依赖
echo "📦 安装 Python 依赖..."
if [ -f "requirements.txt" ]; then
    pip3 install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    echo "   ✅ 依赖安装完成"
else
    echo "   ⚠️  未找到 requirements.txt"
fi
echo ""

# 4. 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p uploads
mkdir -p reports
mkdir -p __pycache__
chmod 755 uploads reports
echo "   ✅ 目录创建完成"
echo ""

# 5. 检查环境变量配置
echo "🔧 检查环境变量配置..."
if [ ! -f ".env" ]; then
    echo "   ⚠️  未找到 .env 文件"
    echo "   创建默认 .env 文件..."
    cat > .env << EOF
# 模型提供商: openai, tongyi, custom
MODEL_PROVIDER=tongyi

# 通义千问配置
DASHSCOPE_API_KEY=sk-a05fb9f14d734998a8d0a7af05503058
API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
MODEL_NAME=qwen3-max

# 模型参数
TEMPERATURE=0.7
MAX_TOKENS=32000
EOF
    echo "   ✅ 已创建默认 .env 文件"
    echo "   ⚠️  请根据需要修改 .env 文件中的配置"
else
    echo "   ✅ .env 文件已存在"
fi
echo ""

# 6. 检查端口占用
echo "🔍 检查端口 5000 是否被占用..."
if netstat -tlnp 2>/dev/null | grep -q ":5000 "; then
    echo "   ⚠️  端口 5000 已被占用"
    read -p "是否停止占用端口的进程? (y/n): " KILL_PROCESS
    if [ "$KILL_PROCESS" = "y" ]; then
        pkill -f "python3.*app.py" || true
        sleep 2
        echo "   ✅ 已停止相关进程"
    fi
else
    echo "   ✅ 端口 5000 可用"
fi
echo ""

# 7. 选择运行方式
echo "=========================================="
echo "  选择运行方式"
echo "=========================================="
echo "1. 直接运行（前台，用于测试）"
echo "2. 后台运行（使用 nohup）"
echo "3. 安装为 systemd 服务（推荐，开机自启）"
echo ""
read -p "请选择 (1/2/3) [默认: 2]: " RUN_MODE
RUN_MODE=${RUN_MODE:-2}

case $RUN_MODE in
    1)
        echo ""
        echo "🚀 启动 Flask 应用（前台运行）..."
        echo "   访问地址: http://$(hostname -I | awk '{print $1}'):5000"
        echo "   按 Ctrl+C 停止"
        echo ""
        python3 app.py
        ;;
    2)
        echo ""
        echo "🚀 启动 Flask 应用（后台运行）..."
        nohup python3 app.py > app.log 2>&1 &
        PID=$!
        sleep 2
        
        if ps -p $PID > /dev/null; then
            echo "   ✅ 应用已启动，进程ID: $PID"
            echo "   📋 日志文件: $SCRIPT_DIR/app.log"
            echo "   🌐 访问地址: http://$(hostname -I | awk '{print $1}'):5000"
            echo ""
            echo "常用命令:"
            echo "   查看日志: tail -f $SCRIPT_DIR/app.log"
            echo "   停止服务: pkill -f 'python3.*app.py'"
            echo "   查看进程: ps aux | grep 'python3.*app.py'"
        else
            echo "   ❌ 应用启动失败，请查看日志:"
            echo "   tail -f $SCRIPT_DIR/app.log"
            exit 1
        fi
        ;;
    3)
        echo ""
        echo "📦 安装 systemd 服务..."
        if [ -f "install_service.sh" ]; then
            chmod +x install_service.sh
            ./install_service.sh
        else
            echo "   ❌ 未找到 install_service.sh"
            echo "   请手动安装 systemd 服务"
        fi
        ;;
    *)
        echo "❌ 无效的选择"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "  部署完成!"
echo "=========================================="

