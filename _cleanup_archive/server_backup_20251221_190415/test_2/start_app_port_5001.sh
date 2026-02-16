#!/bin/bash
# 启动 Flask 应用（端口 5001）

cd "/root/test_2"

# 停止可能正在运行的进程
pkill -f "python.*app.py.*port=5001" 2>/dev/null || true
sleep 1

# 后台运行
nohup python3 app.py --port 5001 > app_5001.log 2>&1 &

PID=$!
sleep 2

if ps -p $PID > /dev/null; then
    echo "✅ Flask 应用已启动"
    echo "   进程ID: $PID"
    echo "   端口: 5001"
    echo "   日志: /root/test_2/app_5001.log"
    if [ "1" = "1" ]; then
        echo "   访问地址: http://app.chaozhiyinqing.top"
    else
        echo "   访问地址: http://chaozhiyinqing.top/app"
    fi
    echo "   本地测试: http://localhost:5001"
else
    echo "❌ 应用启动失败，请查看日志:"
    echo "   tail -f /root/test_2/app_5001.log"
    exit 1
fi
