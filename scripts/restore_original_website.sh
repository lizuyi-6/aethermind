#!/bin/bash
# 恢复原有网站并确保新应用不影响

set -e

echo "=========================================="
echo "  恢复原有网站配置"
echo "=========================================="
echo ""

# 1. 检查 Nginx 配置
echo "步骤 1: 检查 Nginx 配置..."
echo "----------------------------------------"

# 查找所有配置文件
if [ -d /etc/nginx/sites-available ]; then
    echo "现有配置文件:"
    ls -la /etc/nginx/sites-available/
    echo ""
    
    echo "已启用的配置:"
    ls -la /etc/nginx/sites-enabled/ 2>/dev/null || echo "sites-enabled 目录不存在"
    echo ""
fi

# 2. 检查主域名配置
echo "步骤 2: 检查主域名配置..."
MAIN_DOMAIN="chaozhiyinqing.top"
MAIN_CONFIG=""

# 查找主域名配置
if [ -f /etc/nginx/sites-available/$MAIN_DOMAIN ]; then
    MAIN_CONFIG="/etc/nginx/sites-available/$MAIN_DOMAIN"
elif [ -f /etc/nginx/sites-available/default ]; then
    MAIN_CONFIG="/etc/nginx/sites-available/default"
elif [ -f /etc/nginx/conf.d/$MAIN_DOMAIN.conf ]; then
    MAIN_CONFIG="/etc/nginx/conf.d/$MAIN_DOMAIN.conf"
elif [ -f /etc/nginx/conf.d/default.conf ]; then
    MAIN_CONFIG="/etc/nginx/conf.d/default.conf"
fi

if [ -n "$MAIN_CONFIG" ] && [ -f "$MAIN_CONFIG" ]; then
    echo "✅ 找到主配置: $MAIN_CONFIG"
    echo ""
    echo "配置内容预览:"
    head -30 "$MAIN_CONFIG"
    echo ""
    
    # 检查是否有 server_name 配置
    if grep -q "server_name.*$MAIN_DOMAIN" "$MAIN_CONFIG"; then
        echo "✅ 主域名配置存在"
    else
        echo "⚠️  主域名配置可能不完整"
    fi
else
    echo "❌ 未找到主域名配置"
    echo "   需要创建或恢复配置"
fi
echo ""

# 3. 检查原有网站服务
echo "步骤 3: 检查原有网站服务..."
echo "----------------------------------------"

# 检查常见端口
PORTS=(80 443 5000 8000 8080)
for port in "${PORTS[@]}"; do
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        echo "端口 $port 正在监听:"
        netstat -tlnp 2>/dev/null | grep ":$port "
    fi
done
echo ""

# 检查运行中的服务
echo "运行中的 Web 服务:"
ps aux | grep -E "nginx|apache|httpd|python.*app|node|php" | grep -v grep | head -10
echo ""

# 4. 备份当前配置
echo "步骤 4: 备份当前配置..."
BACKUP_DIR="/root/nginx_backup_$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

if [ -d /etc/nginx/sites-available ]; then
    cp -r /etc/nginx/sites-available/* "$BACKUP_DIR/" 2>/dev/null || true
fi
if [ -d /etc/nginx/conf.d ]; then
    cp -r /etc/nginx/conf.d/* "$BACKUP_DIR/" 2>/dev/null || true
fi
if [ -f /etc/nginx/nginx.conf ]; then
    cp /etc/nginx/nginx.conf "$BACKUP_DIR/nginx.conf.backup"
fi

echo "✅ 配置已备份到: $BACKUP_DIR"
echo ""

# 5. 检查并修复配置
echo "步骤 5: 检查配置问题..."
echo "----------------------------------------"

# 检查是否有重复的 server_name
if [ -n "$MAIN_CONFIG" ] && [ -f "$MAIN_CONFIG" ]; then
    SERVER_COUNT=$(grep -c "server_name.*$MAIN_DOMAIN" "$MAIN_CONFIG" 2>/dev/null || echo "0")
    if [ "$SERVER_COUNT" -gt 1 ]; then
        echo "⚠️  发现多个 server_name 配置，可能导致冲突"
    fi
fi

# 检查新应用配置是否影响主域名
APP_CONFIG="/etc/nginx/sites-available/app-chaozhiyinqing.top"
if [ -f "$APP_CONFIG" ]; then
    if grep -q "server_name.*$MAIN_DOMAIN" "$APP_CONFIG"; then
        echo "❌ 新应用配置中包含了主域名，这会导致冲突！"
        echo "   需要修复配置"
    else
        echo "✅ 新应用配置使用子域名，不会影响主域名"
    fi
fi
echo ""

# 6. 测试 Nginx 配置
echo "步骤 6: 测试 Nginx 配置..."
if nginx -t 2>&1 | grep -q "successful"; then
    echo "✅ Nginx 配置语法正确"
else
    echo "❌ Nginx 配置有错误:"
    nginx -t 2>&1 | grep -i error
fi
echo ""

# 7. 生成修复建议
echo "=========================================="
echo "  修复建议"
echo "=========================================="
echo ""

if [ -z "$MAIN_CONFIG" ] || [ ! -f "$MAIN_CONFIG" ]; then
    echo "1. 需要创建主域名配置"
    echo "   创建文件: /etc/nginx/sites-available/$MAIN_DOMAIN"
    echo ""
    echo "   基本配置模板:"
    cat << 'EOF'
server {
    listen 80;
    server_name chaozhiyinqing.top www.chaozhiyinqing.top;

    root /var/www/html;  # 修改为您的网站根目录
    index index.html index.htm index.php;

    location / {
        try_files $uri $uri/ =404;
    }

    # 如果使用 PHP
    # location ~ \.php$ {
    #     fastcgi_pass unix:/var/run/php/php-fpm.sock;
    #     fastcgi_index index.php;
    #     include fastcgi_params;
    # }
}
EOF
    echo ""
fi

echo "2. 确保主域名配置已启用"
if [ -d /etc/nginx/sites-enabled ]; then
    if [ ! -L "/etc/nginx/sites-enabled/$MAIN_DOMAIN" ] && [ -f "/etc/nginx/sites-available/$MAIN_DOMAIN" ]; then
        echo "   创建符号链接:"
        echo "   sudo ln -s /etc/nginx/sites-available/$MAIN_DOMAIN /etc/nginx/sites-enabled/"
    fi
fi
echo ""

echo "3. 确保新应用配置使用子域名（不冲突）"
echo "   新应用应使用: app.chaozhiyinqing.top"
echo "   主网站应使用: chaozhiyinqing.top"
echo ""

echo "4. 重载 Nginx"
echo "   sudo nginx -t"
echo "   sudo systemctl reload nginx"
echo ""

echo "备份位置: $BACKUP_DIR"
echo ""

