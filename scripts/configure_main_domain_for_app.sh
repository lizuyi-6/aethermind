#!/bin/bash
# 配置主域名指向AetherMind项目，保持 gaoyuzhan.top 不变

set -e

echo "=========================================="
echo "  配置主域名指向AetherMind项目"
echo "=========================================="
echo ""

DOMAIN="chaozhiyinqing.top"
APP_PORT=5001
BACKUP_DIR="/root/nginx_backup_$(date +%Y%m%d_%H%M%S)"

# 1. 备份当前配置
echo "步骤 1: 备份当前配置..."
mkdir -p "$BACKUP_DIR"
cp -r /etc/nginx/sites-available/* "$BACKUP_DIR/" 2>/dev/null || true
echo "✅ 配置已备份到: $BACKUP_DIR"
echo ""

# 2. 检查 gaoyuzhan.top 配置
echo "步骤 2: 检查 gaoyuzhan.top 配置..."
BLOG_CONFIG="/etc/nginx/sites-available/blog"
if [ -f "$BLOG_CONFIG" ]; then
    echo "✅ gaoyuzhan.top 配置存在"
    echo "配置内容:"
    cat "$BLOG_CONFIG"
    echo ""
    echo "✅ gaoyuzhan.top 配置将保持不变"
else
    echo "⚠️  gaoyuzhan.top 配置不存在"
fi
echo ""

# 3. 修改主域名配置指向AetherMind
echo "步骤 3: 修改主域名配置..."
MAIN_CONFIG="/etc/nginx/sites-available/$DOMAIN"

# 备份原配置
cp "$MAIN_CONFIG" "$MAIN_CONFIG.backup"

# 创建新配置（指向 Flask 应用）
cat > "$MAIN_CONFIG" << EOF
# 主域名配置 - $DOMAIN (AetherMind项目)
server {
    listen 80 default_server;
    server_name $DOMAIN www.$DOMAIN;

    access_log /var/log/nginx/$DOMAIN-access.log;
    error_log /var/log/nginx/$DOMAIN-error.log;

    # 代理到AetherMind Flask 应用
    location / {
        proxy_pass http://localhost:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        # WebSocket 支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # 静态文件直接服务（提高性能）
    location /static/ {
        alias /root/test_2/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # 上传文件
    location /uploads/ {
        alias /root/test_2/uploads/;
    }
}
EOF

echo "✅ 主域名配置已更新"
echo ""

# 4. 检查并处理 app.chaozhiyinqing.top 配置
echo "步骤 4: 检查子域名配置..."
APP_SUBDOMAIN_CONFIG="/etc/nginx/sites-available/app-chaozhiyinqing.top"
if [ -f "$APP_SUBDOMAIN_CONFIG" ]; then
    echo "⚠️  发现 app.chaozhiyinqing.top 配置"
    echo "   由于主域名已指向应用，子域名配置可以："
    echo "   1. 保留（两个域名都指向同一应用）"
    echo "   2. 禁用（只使用主域名）"
    echo ""
    read -p "是否保留 app.chaozhiyinqing.top 配置? (y/n) [默认: n]: " KEEP_SUBDOMAIN
    KEEP_SUBDOMAIN=${KEEP_SUBDOMAIN:-n}
    
    if [ "$KEEP_SUBDOMAIN" != "y" ]; then
        # 禁用子域名配置
        if [ -L "/etc/nginx/sites-enabled/app-chaozhiyinqing.top" ]; then
            rm -f "/etc/nginx/sites-enabled/app-chaozhiyinqing.top"
            echo "✅ app.chaozhiyinqing.top 配置已禁用"
        fi
    else
        echo "✅ app.chaozhiyinqing.top 配置将保留"
    fi
else
    echo "✅ 未找到子域名配置"
fi
echo ""

# 5. 确保配置已启用
echo "步骤 5: 确保配置已启用..."
if [ ! -L "/etc/nginx/sites-enabled/$DOMAIN" ]; then
    ln -s "$MAIN_CONFIG" "/etc/nginx/sites-enabled/$DOMAIN"
    echo "✅ 主域名配置已启用"
else
    echo "✅ 主域名配置已启用"
fi
echo ""

# 6. 测试配置
echo "步骤 6: 测试 Nginx 配置..."
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
    echo "恢复备份配置..."
    cp "$MAIN_CONFIG.backup" "$MAIN_CONFIG"
    exit 1
fi

# 7. 验证应用是否运行
echo ""
echo "步骤 7: 验证应用运行状态..."
if pgrep -f "python.*app.py.*port=$APP_PORT" > /dev/null; then
    PID=$(pgrep -f "python.*app.py.*port=$APP_PORT" | head -1)
    echo "✅ 应用正在运行 (PID: $PID)"
else
    echo "⚠️  应用未运行"
    echo "   启动应用:"
    echo "   cd /root/test_2"
    echo "   nohup python3 app.py --port $APP_PORT > app_${APP_PORT}.log 2>&1 &"
fi
echo ""

echo "=========================================="
echo "  配置完成"
echo "=========================================="
echo ""
echo "配置摘要:"
echo "  主域名: http://$DOMAIN -> AetherMind项目 (端口 $APP_PORT)"
echo "  Blog: http://gaoyuzhan.top -> 保持不变"
if [ "$KEEP_SUBDOMAIN" = "y" ]; then
    echo "  子域名: http://app.$DOMAIN -> AetherMind项目 (端口 $APP_PORT)"
fi
echo ""
echo "测试访问:"
echo "  curl -I http://localhost"
echo "  curl -I http://$DOMAIN"
echo ""
echo "备份位置: $BACKUP_DIR"
echo ""

