#!/bin/bash
# 修复原有网站配置

set -e

echo "=========================================="
echo "  修复原有网站配置"
echo "=========================================="
echo ""

DOMAIN="chaozhiyinqing.top"
BACKUP_DIR="/root/nginx_backup_$(date +%Y%m%d_%H%M%S)"

# 1. 备份当前配置
echo "步骤 1: 备份当前配置..."
mkdir -p "$BACKUP_DIR"
cp -r /etc/nginx/sites-available/* "$BACKUP_DIR/" 2>/dev/null || true
cp -r /etc/nginx/conf.d/* "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ 配置已备份到: $BACKUP_DIR"
echo ""

# 2. 检查主域名配置是否存在
echo "步骤 2: 检查主域名配置..."
MAIN_CONFIG="/etc/nginx/sites-available/$DOMAIN"

if [ ! -f "$MAIN_CONFIG" ]; then
    echo "❌ 主域名配置不存在，需要创建"
    echo ""
    
    # 查找网站根目录
    WEB_ROOT=""
    if [ -d "/var/www/html" ]; then
        WEB_ROOT="/var/www/html"
    elif [ -d "/var/www/$DOMAIN" ]; then
        WEB_ROOT="/var/www/$DOMAIN"
    elif [ -d "/var/www" ]; then
        WEB_ROOT="/var/www"
    else
        WEB_ROOT="/var/www/html"
        mkdir -p "$WEB_ROOT"
    fi
    
    echo "检测到的网站根目录: $WEB_ROOT"
    echo ""
    
    # 创建主域名配置
    echo "步骤 3: 创建主域名配置..."
    cat > "$MAIN_CONFIG" << EOF
# 主域名配置 - $DOMAIN
server {
    listen 80;
    server_name $DOMAIN www.$DOMAIN;

    root $WEB_ROOT;
    index index.html index.htm index.php;

    access_log /var/log/nginx/$DOMAIN-access.log;
    error_log /var/log/nginx/$DOMAIN-error.log;

    location / {
        try_files \$uri \$uri/ =404;
    }

    # PHP 支持（如果使用）
    # location ~ \.php$ {
    #     fastcgi_pass unix:/var/run/php/php-fpm.sock;
    #     fastcgi_index index.php;
    #     include fastcgi_params;
    #     fastcgi_param SCRIPT_FILENAME \$document_root\$fastcgi_script_name;
    # }

    # 静态文件缓存
    location ~* \.(jpg|jpeg|png|gif|ico|css|js)$ {
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF
    
    echo "✅ 主域名配置已创建: $MAIN_CONFIG"
    echo ""
    
    # 启用配置
    if [ -d /etc/nginx/sites-enabled ]; then
        if [ ! -L "/etc/nginx/sites-enabled/$DOMAIN" ]; then
            ln -s "$MAIN_CONFIG" "/etc/nginx/sites-enabled/$DOMAIN"
            echo "✅ 配置已启用"
        fi
    fi
else
    echo "✅ 主域名配置已存在: $MAIN_CONFIG"
    echo ""
    echo "配置内容:"
    head -20 "$MAIN_CONFIG"
    echo ""
fi

# 3. 验证配置不冲突
echo "步骤 4: 验证配置..."
echo "----------------------------------------"

# 检查是否有重复的 server_name
CONFLICTS=$(grep -r "server_name.*$DOMAIN" /etc/nginx/sites-available/ 2>/dev/null | grep -v "app.$DOMAIN" | wc -l)
if [ "$CONFLICTS" -gt 1 ]; then
    echo "⚠️  发现多个主域名配置，可能冲突"
    grep -r "server_name.*$DOMAIN" /etc/nginx/sites-available/ 2>/dev/null | grep -v "app.$DOMAIN"
else
    echo "✅ 配置无冲突"
fi
echo ""

# 4. 测试 Nginx 配置
echo "步骤 5: 测试 Nginx 配置..."
if nginx -t 2>&1 | grep -q "successful"; then
    echo "✅ Nginx 配置测试通过"
    echo ""
    read -p "是否立即重载 Nginx? (y/n) [默认: y]: " RELOAD
    RELOAD=${RELOAD:-y}
    if [ "$RELOAD" = "y" ]; then
        systemctl reload nginx
        echo "✅ Nginx 已重载"
    fi
else
    echo "❌ Nginx 配置测试失败:"
    nginx -t 2>&1 | grep -i error
    echo ""
    echo "请检查配置后重试"
    exit 1
fi

echo ""
echo "=========================================="
echo "  修复完成"
echo "=========================================="
echo ""
echo "主域名配置: $MAIN_CONFIG"
echo "网站根目录: $WEB_ROOT"
echo "访问地址: http://$DOMAIN"
echo ""
echo "新应用访问: http://app.$DOMAIN"
echo ""
echo "备份位置: $BACKUP_DIR"
echo ""
echo "如果网站仍无法访问，请检查:"
echo "1. 网站文件是否在 $WEB_ROOT 目录"
echo "2. 文件权限是否正确"
echo "3. DNS 是否正确解析到服务器"

