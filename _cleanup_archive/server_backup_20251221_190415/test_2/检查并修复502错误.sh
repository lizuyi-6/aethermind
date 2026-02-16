#!/bin/bash

echo "=========================================="
echo "检查并修复502 Bad Gateway错误"
echo "=========================================="

# 1. 检查Flask应用服务状态
echo ""
echo "[1] 检查Flask应用服务状态..."
systemctl status flask-app.service --no-pager -l

# 2. 检查Flask应用是否在运行
echo ""
echo "[2] 检查Flask应用进程..."
ps aux | grep -E "python.*app.py|flask" | grep -v grep

# 3. 检查端口占用（Flask默认5000端口）
echo ""
echo "[3] 检查端口占用情况..."
netstat -tlnp | grep -E ":5000|:80|:443" || ss -tlnp | grep -E ":5000|:80|:443"

# 4. 检查nginx配置
echo ""
echo "[4] 检查nginx配置..."
if [ -f /etc/nginx/sites-available/default ]; then
    echo "--- /etc/nginx/sites-available/default ---"
    cat /etc/nginx/sites-available/default | grep -A 20 "location\|proxy_pass\|upstream"
fi

if [ -f /etc/nginx/sites-enabled/default ]; then
    echo "--- /etc/nginx/sites-enabled/default ---"
    cat /etc/nginx/sites-enabled/default | grep -A 20 "location\|proxy_pass\|upstream"
fi

# 5. 检查nginx错误日志
echo ""
echo "[5] 检查nginx错误日志（最近20行）..."
if [ -f /var/log/nginx/error.log ]; then
    tail -20 /var/log/nginx/error.log
else
    echo "错误日志文件不存在: /var/log/nginx/error.log"
fi

# 6. 检查Flask应用日志
echo ""
echo "[6] 检查Flask应用日志（最近30行）..."
journalctl -u flask-app.service -n 30 --no-pager

# 7. 测试Flask应用是否响应
echo ""
echo "[7] 测试Flask应用本地连接..."
curl -s -o /dev/null -w "HTTP状态码: %{http_code}\n" http://localhost:5000/ || echo "无法连接到localhost:5000"

# 8. 检查Python路径
echo ""
echo "[8] 检查Python路径..."
which python3
/usr/local/python3.11/bin/python3 --version 2>/dev/null || echo "Python路径不存在"

# 9. 检查应用文件
echo ""
echo "[9] 检查应用文件..."
ls -lh /var/www/html/app.py

# 10. 尝试重启服务
echo ""
echo "[10] 尝试重启Flask应用服务..."
systemctl restart flask-app.service
sleep 3
systemctl status flask-app.service --no-pager -l

# 11. 重新加载nginx
echo ""
echo "[11] 重新加载nginx配置..."
nginx -t && systemctl reload nginx || echo "nginx配置测试失败"

echo ""
echo "=========================================="
echo "检查完成"
echo "=========================================="
echo ""
echo "如果问题仍然存在，请检查："
echo "1. Flask应用是否正常启动（查看上面的服务状态）"
echo "2. Flask应用监听的端口是否正确（应该是5000）"
echo "3. nginx配置中的proxy_pass地址是否正确（应该是http://127.0.0.1:5000）"
echo "4. 防火墙是否允许5000端口"
echo ""

