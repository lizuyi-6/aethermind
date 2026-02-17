#!/bin/bash
# 重启 Flask 应用脚本

set -e

APP_PORT=5001
PROJECT_DIR="/root/test_2"
LOG_FILE="$PROJECT_DIR/app_${APP_PORT}.log"

echo "=========================================="
echo "  重启 Flask 应用"
echo "=========================================="
echo ""

cd "$PROJECT_DIR"

# 1. 停止现有进程
echo "步骤 1: 停止现有进程..."
pkill -f "python.*app.py.*port=$APP_PORT" 2>/dev/null || true
sleep 2

# 检查是否还有进程
if pgrep -f "python.*app.py.*port=$APP_PORT" > /dev/null; then
    echo "⚠️  仍有进程运行，强制停止..."
    pkill -9 -f "python.*app.py.*port=$APP_PORT" 2>/dev/null || true
    sleep 1
fi

echo "✅ 进程已停止"
echo ""

# 2. 检查端口是否释放
echo "步骤 2: 检查端口..."
if netstat -tlnp 2>/dev/null | grep -q ":$APP_PORT " || ss -tlnp 2>/dev/null | grep -q ":$APP_PORT "; then
    echo "⚠️  端口 $APP_PORT 仍被占用"
    lsof -ti:$APP_PORT | xargs kill -9 2>/dev/null || true
    sleep 1
else
    echo "✅ 端口 $APP_PORT 已释放"
fi
echo ""

# 3. 检查 Python 和依赖
echo "步骤 3: 检查环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装"
    exit 1
fi

echo "✅ Python3: $(python3 --version)"
echo ""

# 4. 检查应用文件
echo "步骤 4: 检查应用文件..."
if [ ! -f "$PROJECT_DIR/app.py" ]; then
    echo "❌ 应用文件不存在: $PROJECT_DIR/app.py"
    exit 1
fi

echo "✅ 应用文件存在"
echo ""

# 5. 启动应用
echo "步骤 5: 启动应用..."
nohup python3 app.py --port $APP_PORT > "$LOG_FILE" 2>&1 &

PID=$!
sleep 3

# 6. 验证启动
echo "步骤 6: 验证启动..."
if ps -p $PID > /dev/null 2>&1; then
    echo "✅ 应用已启动"
    echo "   进程ID: $PID"
    echo "   端口: $APP_PORT"
    echo "   日志文件: $LOG_FILE"
    echo ""
    
    # 检查端口监听
    if netstat -tlnp 2>/dev/null | grep -q ":$APP_PORT " || ss -tlnp 2>/dev/null | grep -q ":$APP_PORT "; then
        echo "✅ 端口 $APP_PORT 正在监听"
    else
        echo "⚠️  端口 $APP_PORT 未监听，检查日志..."
        tail -20 "$LOG_FILE"
    fi
    
    # 测试本地访问
    echo ""
    echo "步骤 7: 测试本地访问..."
    sleep 1
    if curl -s -o /dev/null -w "%{http_code}" http://localhost:$APP_PORT | grep -q "200\|301\|302"; then
        echo "✅ 本地访问正常"
    else
        echo "⚠️  本地访问失败，查看日志:"
        tail -30 "$LOG_FILE"
    fi
else
    echo "❌ 应用启动失败"
    echo ""
    echo "查看日志:"
    tail -50 "$LOG_FILE"
    exit 1
fi

echo ""
echo "=========================================="
echo "  应用重启完成"
echo "=========================================="
echo ""
echo "访问地址:"
echo "  http://chaozhiyinqing.top"
echo "  http://app.chaozhiyinqing.top"
echo ""
echo "查看日志:"
echo "  tail -f $LOG_FILE"
echo ""
echo "停止应用:"
echo "  pkill -f 'python.*app.py.*port=$APP_PORT'"
echo ""

