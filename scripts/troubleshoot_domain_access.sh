#!/bin/bash
# 域名访问问题排查脚本

echo "=========================================="
echo "  域名访问问题排查"
echo "=========================================="
echo ""

DOMAIN="app.chaozhiyinqing.top"
APP_PORT=5001

# 1. 检查 DNS 解析
echo "步骤 1: 检查 DNS 解析"
echo "----------------------------------------"
if command -v nslookup &> /dev/null; then
    echo "nslookup 结果:"
    nslookup $DOMAIN 2>&1 | grep -A 2 "Name:" || nslookup $DOMAIN
elif command -v dig &> /dev/null; then
    echo "dig 结果:"
    dig +short $DOMAIN
else
    echo "⚠️  未找到 nslookup 或 dig 命令"
fi

# 检查是否解析到正确 IP
SERVER_IP=$(hostname -I | awk '{print $1}')
DNS_IP=$(nslookup $DOMAIN 2>/dev/null | grep -A 1 "Name:" | tail -1 | awk '{print $2}' || dig +short $DOMAIN 2>/dev/null | head -1)

if [ -n "$DNS_IP" ]; then
    if [ "$DNS_IP" = "$SERVER_IP" ]; then
        echo "✅ DNS 解析正确: $DOMAIN -> $DNS_IP"
    else
        echo "⚠️  DNS 解析可能不正确:"
        echo "   域名解析到: $DNS_IP"
        echo "   服务器 IP: $SERVER_IP"
        echo "   请检查 DNS 配置"
    fi
else
    echo "❌ DNS 未解析或未生效"
    echo "   请检查域名管理后台的 DNS 配置"
    echo "   需要添加 A 记录: app -> $SERVER_IP"
fi
echo ""

# 2. 检查应用是否运行
echo "步骤 2: 检查应用运行状态"
echo "----------------------------------------"
if pgrep -f "python.*app.py.*port=$APP_PORT" > /dev/null; then
    PID=$(pgrep -f "python.*app.py.*port=$APP_PORT" | head -1)
    echo "✅ 应用正在运行"
    echo "   进程ID: $PID"
    ps aux | grep "$PID" | grep -v grep
else
    echo "❌ 应用未运行"
    echo "   请启动应用:"
    echo "   cd /root/test_2"
    echo "   nohup python3 app.py --port $APP_PORT > app_${APP_PORT}.log 2>&1 &"
fi
echo ""

# 3. 检查端口监听
echo "步骤 3: 检查端口监听"
echo "----------------------------------------"
if command -v netstat &> /dev/null; then
    PORT_CHECK=$(netstat -tlnp 2>/dev/null | grep ":$APP_PORT ")
elif command -v ss &> /dev/null; then
    PORT_CHECK=$(ss -tlnp 2>/dev/null | grep ":$APP_PORT ")
else
    PORT_CHECK=$(lsof -i:$APP_PORT 2>/dev/null)
fi

if [ -n "$PORT_CHECK" ]; then
    echo "✅ 端口 $APP_PORT 正在监听:"
    echo "$PORT_CHECK"
else
    echo "❌ 端口 $APP_PORT 未监听"
    echo "   应用可能未启动或启动失败"
fi
echo ""

# 4. 检查本地访问
echo "步骤 4: 测试本地访问"
echo "----------------------------------------"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:$APP_PORT 2>/dev/null | grep -q "200\|301\|302"; then
    echo "✅ 本地访问正常"
    curl -I http://localhost:$APP_PORT 2>/dev/null | head -3
else
    echo "❌ 本地访问失败"
    echo "   尝试访问: curl http://localhost:$APP_PORT"
    RESPONSE=$(curl -s http://localhost:$APP_PORT 2>&1 | head -5)
    if [ -n "$RESPONSE" ]; then
        echo "   响应: $RESPONSE"
    fi
fi
echo ""

# 5. 检查 Nginx 配置
echo "步骤 5: 检查 Nginx 配置"
echo "----------------------------------------"
if command -v nginx &> /dev/null; then
    if systemctl is-active --quiet nginx 2>/dev/null || pgrep -x nginx > /dev/null; then
        echo "✅ Nginx 正在运行"
        
        # 检查配置
        if nginx -t 2>&1 | grep -q "successful"; then
            echo "✅ Nginx 配置正确"
        else
            echo "❌ Nginx 配置有错误:"
            nginx -t 2>&1 | grep -i error
        fi
        
        # 检查是否有相关配置
        if grep -r "$DOMAIN" /etc/nginx/ 2>/dev/null | grep -v "#" > /dev/null; then
            echo "✅ 找到域名配置"
            echo "   配置位置:"
            grep -r "$DOMAIN" /etc/nginx/ 2>/dev/null | grep -v "#" | head -3
        else
            echo "❌ 未找到域名配置"
            echo "   需要创建 Nginx 配置"
        fi
    else
        echo "❌ Nginx 未运行"
        echo "   启动 Nginx: sudo systemctl start nginx"
    fi
else
    echo "⚠️  Nginx 未安装"
fi
echo ""

# 6. 检查防火墙
echo "步骤 6: 检查防火墙"
echo "----------------------------------------"
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(ufw status 2>/dev/null | grep "Status:" | awk '{print $2}')
    if [ "$UFW_STATUS" = "active" ]; then
        echo "⚠️  UFW 防火墙已启用"
        if ufw status | grep -q "80/tcp"; then
            echo "✅ 端口 80 已开放"
        else
            echo "❌ 端口 80 未开放"
            echo "   开放端口: sudo ufw allow 80/tcp"
        fi
    else
        echo "✅ UFW 防火墙未启用或已关闭"
    fi
elif command -v firewall-cmd &> /dev/null; then
    if systemctl is-active --quiet firewalld 2>/dev/null; then
        echo "⚠️  Firewalld 防火墙已启用"
        if firewall-cmd --list-ports 2>/dev/null | grep -q "80/tcp"; then
            echo "✅ 端口 80 已开放"
        else
            echo "❌ 端口 80 未开放"
            echo "   开放端口: sudo firewall-cmd --permanent --add-service=http"
            echo "   sudo firewall-cmd --reload"
        fi
    else
        echo "✅ Firewalld 防火墙未启用"
    fi
else
    echo "ℹ️  未检测到防火墙或防火墙已关闭"
fi
echo ""

# 7. 检查应用日志
echo "步骤 7: 检查应用日志"
echo "----------------------------------------"
LOG_FILE="/root/test_2/app_${APP_PORT}.log"
if [ -f "$LOG_FILE" ]; then
    echo "📋 最近的日志（最后 10 行）:"
    tail -10 "$LOG_FILE"
else
    echo "⚠️  日志文件不存在: $LOG_FILE"
fi
echo ""

# 8. 检查 Nginx 日志
echo "步骤 8: 检查 Nginx 日志"
echo "----------------------------------------"
NGINX_ERROR_LOG="/var/log/nginx/error.log"
NGINX_ACCESS_LOG="/var/log/nginx/app-chaozhiyinqing-top-access.log"

if [ -f "$NGINX_ERROR_LOG" ]; then
    echo "📋 Nginx 错误日志（最近相关错误）:"
    grep -i "$DOMAIN\|$APP_PORT" "$NGINX_ERROR_LOG" 2>/dev/null | tail -5 || echo "   无相关错误"
fi

if [ -f "$NGINX_ACCESS_LOG" ]; then
    echo "📋 Nginx 访问日志（最近访问）:"
    tail -5 "$NGINX_ACCESS_LOG" 2>/dev/null || echo "   无访问记录"
fi
echo ""

# 9. 生成诊断报告
echo "=========================================="
echo "  诊断总结"
echo "=========================================="
echo ""

ISSUES=0

# DNS 检查
if [ -z "$DNS_IP" ] || [ "$DNS_IP" != "$SERVER_IP" ]; then
    echo "❌ DNS 配置问题"
    ISSUES=$((ISSUES + 1))
fi

# 应用检查
if ! pgrep -f "python.*app.py.*port=$APP_PORT" > /dev/null; then
    echo "❌ 应用未运行"
    ISSUES=$((ISSUES + 1))
fi

# 端口检查
if [ -z "$PORT_CHECK" ]; then
    echo "❌ 端口未监听"
    ISSUES=$((ISSUES + 1))
fi

# Nginx 检查
if ! command -v nginx &> /dev/null || ! systemctl is-active --quiet nginx 2>/dev/null; then
    echo "❌ Nginx 未运行"
    ISSUES=$((ISSUES + 1))
fi

if [ $ISSUES -eq 0 ]; then
    echo "✅ 所有检查通过"
    echo ""
    echo "如果仍无法访问，请检查:"
    echo "1. DNS 传播是否完成（可能需要等待几分钟到几小时）"
    echo "2. 浏览器缓存（尝试清除缓存或使用无痕模式）"
    echo "3. 使用不同网络测试（如手机热点）"
else
    echo "发现 $ISSUES 个问题，请根据上述检查结果进行修复"
fi

echo ""
echo "快速修复命令:"
echo "1. 启动应用: cd /root/test_2 && nohup python3 app.py --port $APP_PORT > app_${APP_PORT}.log 2>&1 &"
echo "2. 检查 Nginx: sudo nginx -t && sudo systemctl reload nginx"
echo "3. 测试本地: curl http://localhost:$APP_PORT"

