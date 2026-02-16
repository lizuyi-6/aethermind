#!/bin/bash

echo "=========================================="
echo "更新Python路径并重启服务"
echo "=========================================="

# 1. 查找Python路径
echo ""
echo "[1] 查找Python路径..."
PYTHON_PATH=$(which python3)
if [ -z "$PYTHON_PATH" ]; then
    echo "错误: 未找到python3"
    exit 1
fi
echo "找到Python路径: $PYTHON_PATH"
$PYTHON_PATH --version

# 2. 备份原服务文件
echo ""
echo "[2] 备份原服务文件..."
if [ -f /etc/systemd/system/flask-app.service ]; then
    cp /etc/systemd/system/flask-app.service /etc/systemd/system/flask-app.service.bak
    echo "已备份到: /etc/systemd/system/flask-app.service.bak"
fi

# 3. 更新服务文件中的Python路径
echo ""
echo "[3] 更新服务文件..."
if [ -f /etc/systemd/system/flask-app.service ]; then
    # 更新ExecStart行
    sed -i "s|ExecStart=.*python3|ExecStart=$PYTHON_PATH|" /etc/systemd/system/flask-app.service
    # 更新PATH环境变量（移除不存在的路径）
    sed -i 's|Environment="PATH=.*"|Environment="PATH=/usr/local/bin:/usr/bin:/bin"|' /etc/systemd/system/flask-app.service
    echo "已更新服务文件"
    echo "新的ExecStart:"
    grep "ExecStart=" /etc/systemd/system/flask-app.service
else
    echo "警告: 服务文件不存在，将创建新文件..."
    # 创建新的服务文件
    cat > /etc/systemd/system/flask-app.service << EOF
[Unit]
Description=Flask Web Application - 超智引擎
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/www/html
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
Environment="MODEL_PROVIDER=tongyi"
Environment="API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1"
Environment="MODEL_NAME=qwen3-30b-a3b-instruct-2507"
Environment="DASHSCOPE_API_KEY=sk-a05fb9f14d734998a8d0a7af05503058"
ExecStart=$PYTHON_PATH /var/www/html/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF
    echo "已创建新服务文件"
fi

# 4. 检查Python依赖
echo ""
echo "[4] 检查Python依赖..."
$PYTHON_PATH -c "import flask" 2>&1 || {
    echo "Flask未安装，尝试安装..."
    $PYTHON_PATH -m pip install flask flask-cors --quiet
}

$PYTHON_PATH -c "import flask_cors" 2>&1 || {
    echo "flask-cors未安装，尝试安装..."
    $PYTHON_PATH -m pip install flask-cors --quiet
}

# 5. 检查应用文件语法
echo ""
echo "[5] 检查应用文件语法..."
$PYTHON_PATH -m py_compile /var/www/html/app.py 2>&1 && echo "✓ app.py语法正确" || {
    echo "✗ app.py有语法错误"
    exit 1
}

$PYTHON_PATH -m py_compile /var/www/html/agent.py 2>&1 && echo "✓ agent.py语法正确" || {
    echo "✗ agent.py有语法错误"
    exit 1
}

# 6. 重新加载systemd
echo ""
echo "[6] 重新加载systemd配置..."
systemctl daemon-reload

# 7. 停止旧服务
echo ""
echo "[7] 停止旧服务..."
systemctl stop flask-app.service
sleep 2

# 8. 启动新服务
echo ""
echo "[8] 启动服务..."
systemctl start flask-app.service
sleep 3

# 9. 检查服务状态
echo ""
echo "[9] 检查服务状态..."
systemctl status flask-app.service --no-pager -l | head -30

# 10. 检查端口
echo ""
echo "[10] 检查端口5000..."
sleep 2
if netstat -tlnp 2>/dev/null | grep -q ":5000"; then
    echo "✓ 端口5000正在监听"
elif ss -tlnp 2>/dev/null | grep -q ":5000"; then
    echo "✓ 端口5000正在监听"
else
    echo "✗ 端口5000未监听"
    echo "查看错误日志："
    journalctl -u flask-app.service -n 30 --no-pager
fi

# 11. 测试本地连接
echo ""
echo "[11] 测试本地连接..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    echo "✓ Flask应用响应正常 (HTTP $HTTP_CODE)"
else
    echo "✗ Flask应用无响应 (HTTP $HTTP_CODE)"
    echo "查看详细日志："
    journalctl -u flask-app.service -n 50 --no-pager | tail -30
fi

# 12. 重新加载nginx
echo ""
echo "[12] 重新加载nginx..."
nginx -t && systemctl reload nginx && echo "✓ nginx已重新加载" || {
    echo "✗ nginx重新加载失败"
    nginx -t
}

echo ""
echo "=========================================="
echo "完成"
echo "=========================================="
echo ""
echo "如果仍有问题，请查看日志："
echo "  journalctl -u flask-app.service -f"
echo ""

