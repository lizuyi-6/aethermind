#!/bin/bash
# 检查服务器上正在运行的服务

echo "=========================================="
echo "  检查服务器上运行的服务"
echo "=========================================="
echo ""

# 检查常用端口
echo "📋 检查常用端口占用情况:"
echo ""

PORTS=(80 443 5000 8000 8080 3000 9000)
for port in "${PORTS[@]}"; do
    if command -v netstat &> /dev/null; then
        result=$(netstat -tlnp 2>/dev/null | grep ":$port " || true)
    elif command -v ss &> /dev/null; then
        result=$(ss -tlnp 2>/dev/null | grep ":$port " || true)
    else
        result=$(lsof -i:$port 2>/dev/null || true)
    fi
    
    if [ -n "$result" ]; then
        echo "  ⚠️  端口 $port 已被占用:"
        echo "$result" | head -1
    else
        echo "  ✅ 端口 $port 可用"
    fi
done

echo ""
echo "=========================================="
echo "  检查运行中的 Web 服务"
echo "=========================================="
echo ""

# 检查 nginx
if systemctl is-active --quiet nginx 2>/dev/null || pgrep -x nginx > /dev/null; then
    echo "  ✅ Nginx 正在运行"
    if [ -f /etc/nginx/nginx.conf ]; then
        echo "    配置文件: /etc/nginx/nginx.conf"
        echo "    检查虚拟主机配置:"
        find /etc/nginx -name "*.conf" -type f 2>/dev/null | head -5
    fi
else
    echo "  ❌ Nginx 未运行"
fi

echo ""

# 检查 Apache
if systemctl is-active --quiet httpd 2>/dev/null || systemctl is-active --quiet apache2 2>/dev/null || pgrep -x httpd > /dev/null || pgrep -x apache2 > /dev/null; then
    echo "  ✅ Apache 正在运行"
else
    echo "  ❌ Apache 未运行"
fi

echo ""

# 检查 Python Web 服务
echo "检查 Python Web 服务:"
ps aux | grep -E "python.*app\.py|python.*flask|python.*django|gunicorn|uwsgi" | grep -v grep || echo "  未发现 Python Web 服务"

echo ""
echo "=========================================="
echo "  检查完成"
echo "=========================================="

