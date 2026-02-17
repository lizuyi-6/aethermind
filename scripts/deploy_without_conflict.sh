#!/bin/bash
# 在不影响现有服务的情况下部署新程序

set -e

echo "=========================================="
echo "  安全部署脚本（不影响现有服务）"
echo "=========================================="
echo ""

# 获取脚本目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. 检查现有服务
echo "步骤 1: 检查现有服务..."
if [ -f "check_existing_services.sh" ]; then
    chmod +x check_existing_services.sh
    ./check_existing_services.sh
fi
echo ""

# 2. 选择端口
echo "步骤 2: 选择运行端口"
echo "常用端口: 5000, 8000, 8080, 9000, 3000"
read -p "请输入要使用的端口 [默认: 5001]: " SELECTED_PORT
SELECTED_PORT=${SELECTED_PORT:-5001}

# 检查端口是否被占用
if command -v netstat &> /dev/null; then
    if netstat -tlnp 2>/dev/null | grep -q ":$SELECTED_PORT "; then
        echo "⚠️  警告: 端口 $SELECTED_PORT 已被占用"
        read -p "是否继续? (y/n): " CONTINUE
        if [ "$CONTINUE" != "y" ]; then
            exit 1
        fi
    fi
elif command -v ss &> /dev/null; then
    if ss -tlnp 2>/dev/null | grep -q ":$SELECTED_PORT "; then
        echo "⚠️  警告: 端口 $SELECTED_PORT 已被占用"
        read -p "是否继续? (y/n): " CONTINUE
        if [ "$CONTINUE" != "y" ]; then
            exit 1
        fi
    fi
fi

echo "✅ 将使用端口: $SELECTED_PORT"
echo ""

# 3. 创建启动脚本
echo "步骤 3: 创建启动脚本..."
START_SCRIPT="start_app_port_${SELECTED_PORT}.sh"
cat > "$START_SCRIPT" << EOF
#!/bin/bash
# 启动 Flask 应用（端口 $SELECTED_PORT）

cd "$SCRIPT_DIR"

# 停止可能正在运行的相同端口的进程
if command -v lsof &> /dev/null; then
    lsof -ti:$SELECTED_PORT | xargs kill -9 2>/dev/null || true
fi

# 设置环境变量
export FLASK_APP=app.py
export FLASK_RUN_PORT=$SELECTED_PORT
export FLASK_RUN_HOST=0.0.0.0

# 后台运行
nohup python3 -c "
import sys
sys.path.insert(0, '$SCRIPT_DIR')
from app import app
app.run(host='0.0.0.0', port=$SELECTED_PORT, debug=False, threaded=True)
" > app_${SELECTED_PORT}.log 2>&1 &

PID=\$!
echo "Flask 应用已启动"
echo "进程ID: \$PID"
echo "端口: $SELECTED_PORT"
echo "日志文件: $SCRIPT_DIR/app_${SELECTED_PORT}.log"
echo "访问地址: http://\$(hostname -I | awk '{print \$1}'):$SELECTED_PORT"
echo ""
echo "查看日志: tail -f $SCRIPT_DIR/app_${SELECTED_PORT}.log"
echo "停止服务: kill \$PID 或 pkill -f 'port=$SELECTED_PORT'"
EOF

chmod +x "$START_SCRIPT"
echo "✅ 启动脚本已创建: $START_SCRIPT"
echo ""

# 4. 创建 systemd 服务文件（可选）
echo "步骤 4: 是否创建 systemd 服务? (开机自启)"
read -p "创建 systemd 服务? (y/n) [默认: n]: " CREATE_SERVICE
CREATE_SERVICE=${CREATE_SERVICE:-n}

if [ "$CREATE_SERVICE" = "y" ]; then
    SERVICE_NAME="flask-app-port-${SELECTED_PORT}"
    SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
    
    cat > "/tmp/${SERVICE_NAME}.service" << EOF
[Unit]
Description=Flask Web Application - 超智引擎 (Port $SELECTED_PORT)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="FLASK_APP=app.py"
Environment="FLASK_RUN_PORT=$SELECTED_PORT"
Environment="FLASK_RUN_HOST=0.0.0.0"
ExecStart=/usr/bin/python3 -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from app import app; app.run(host='0.0.0.0', port=$SELECTED_PORT, debug=False, threaded=True)"
Restart=always
RestartSec=10
StandardOutput=append:$SCRIPT_DIR/app_${SELECTED_PORT}.log
StandardError=append:$SCRIPT_DIR/app_${SELECTED_PORT}.log

[Install]
WantedBy=multi-user.target
EOF
    
    if [ "$EUID" -eq 0 ]; then
        cp "/tmp/${SERVICE_NAME}.service" "$SERVICE_FILE"
        systemctl daemon-reload
        systemctl enable "${SERVICE_NAME}.service"
        echo "✅ systemd 服务已创建: $SERVICE_NAME"
        echo ""
        read -p "是否立即启动服务? (y/n) [默认: n]: " START_NOW
        if [ "$START_NOW" = "y" ]; then
            systemctl start "${SERVICE_NAME}.service"
            sleep 2
            systemctl status "${SERVICE_NAME}.service" --no-pager
        fi
    else
        echo "⚠️  需要 root 权限创建 systemd 服务"
        echo "   服务文件已保存到: /tmp/${SERVICE_NAME}.service"
        echo "   请手动复制到 /etc/systemd/system/ 并运行:"
        echo "   sudo cp /tmp/${SERVICE_NAME}.service $SERVICE_FILE"
        echo "   sudo systemctl daemon-reload"
        echo "   sudo systemctl enable ${SERVICE_NAME}.service"
        echo "   sudo systemctl start ${SERVICE_NAME}.service"
    fi
    rm -f "/tmp/${SERVICE_NAME}.service"
fi

echo ""
echo "=========================================="
echo "  部署完成"
echo "=========================================="
echo ""
echo "启动应用:"
echo "  ./$START_SCRIPT"
echo ""
echo "或直接运行:"
echo "  nohup python3 app.py --port $SELECTED_PORT > app_${SELECTED_PORT}.log 2>&1 &"
echo ""
echo "访问地址:"
echo "  http://$(hostname -I | awk '{print $1}'):$SELECTED_PORT"
echo ""

