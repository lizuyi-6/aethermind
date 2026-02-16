#!/bin/bash

echo "=========================================="
echo "快速修复502 Bad Gateway错误"
echo "=========================================="

# 1. 停止服务
echo ""
echo "[1] 停止Flask应用服务..."
systemctl stop flask-app.service

# 2. 等待2秒
sleep 2

# 3. 检查并修复Python路径
echo ""
echo "[2] 检查Python路径..."
PYTHON_PATH="/usr/local/python3.11/bin/python3"
if [ ! -f "$PYTHON_PATH" ]; then
    echo "Python路径不存在，尝试查找其他Python..."
    PYTHON_PATH=$(which python3)
    echo "使用Python路径: $PYTHON_PATH"
fi

# 4. 检查应用文件
echo ""
echo "[3] 检查应用文件..."
if [ ! -f "/var/www/html/app.py" ]; then
    echo "错误: app.py文件不存在！"
    exit 1
fi

# 5. 测试Python能否运行
echo ""
echo "[4] 测试Python..."
$PYTHON_PATH --version || {
    echo "错误: Python无法运行！"
    exit 1
}

# 6. 检查依赖
echo ""
echo "[5] 检查关键依赖..."
$PYTHON_PATH -c "import flask" 2>&1 || {
    echo "警告: Flask未安装，尝试安装..."
    $PYTHON_PATH -m pip install flask flask-cors --quiet
}

# 7. 更新systemd服务文件（如果需要）
echo ""
echo "[6] 更新systemd服务文件..."
if [ -f "/etc/systemd/system/flask-app.service" ]; then
    # 确保Python路径正确
    sed -i "s|ExecStart=.*|ExecStart=$PYTHON_PATH /var/www/html/app.py|" /etc/systemd/system/flask-app.service
    echo "已更新服务文件中的Python路径"
fi

# 8. 重新加载systemd
echo ""
echo "[7] 重新加载systemd配置..."
systemctl daemon-reload

# 9. 启动服务
echo ""
echo "[8] 启动Flask应用服务..."
systemctl start flask-app.service

# 10. 等待服务启动
echo ""
echo "[9] 等待服务启动（5秒）..."
sleep 5

# 11. 检查服务状态
echo ""
echo "[10] 检查服务状态..."
systemctl status flask-app.service --no-pager -l | head -20

# 12. 检查端口
echo ""
echo "[11] 检查端口5000..."
if netstat -tlnp 2>/dev/null | grep -q ":5000"; then
    echo "✓ 端口5000正在监听"
elif ss -tlnp 2>/dev/null | grep -q ":5000"; then
    echo "✓ 端口5000正在监听"
else
    echo "✗ 端口5000未监听，服务可能未正常启动"
    echo "查看详细日志："
    journalctl -u flask-app.service -n 50 --no-pager
fi

# 13. 测试本地连接
echo ""
echo "[12] 测试本地连接..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/ 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    echo "✓ Flask应用响应正常 (HTTP $HTTP_CODE)"
else
    echo "✗ Flask应用无响应 (HTTP $HTTP_CODE)"
    echo "查看错误日志："
    journalctl -u flask-app.service -n 30 --no-pager | tail -20
fi

# 14. 重新加载nginx
echo ""
echo "[13] 重新加载nginx..."
nginx -t && systemctl reload nginx && echo "✓ nginx已重新加载" || echo "✗ nginx重新加载失败"

echo ""
echo "=========================================="
echo "修复完成"
echo "=========================================="
echo ""
echo "如果问题仍然存在，请运行："
echo "  ./检查并修复502错误.sh"
echo ""
echo "查看服务日志："
echo "  journalctl -u flask-app.service -f"
echo ""

