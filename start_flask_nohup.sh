#!/bin/bash
# 使用nohup在后台运行Flask应用（SSH断开后继续运行）

cd /var/www/html

# 停止可能正在运行的Flask进程
pkill -f "python3.*app.py" || true

# 等待进程完全停止
sleep 2

# 使用nohup在后台启动Flask应用
nohup /usr/local/python3.11/bin/python3 app.py > flask_app.log 2>&1 &

# 获取进程ID
PID=$!

echo "Flask应用已启动，进程ID: $PID"
echo "日志文件: /var/www/html/flask_app.log"
echo ""
echo "查看日志: tail -f /var/www/html/flask_app.log"
echo "停止服务: pkill -f 'python3.*app.py'"
echo "查看进程: ps aux | grep 'python3.*app.py'"




















