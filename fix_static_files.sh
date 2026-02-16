#!/bin/bash
# 修复静态文件访问问题

set -e

echo "=========================================="
echo "  修复静态文件访问问题"
echo "=========================================="
echo ""

APP_PORT=5001
PROJECT_DIR="/root/test_2"

# 1. 检查并修复静态文件权限
echo "步骤 1: 修复静态文件权限..."
chmod -R 755 "$PROJECT_DIR/static" 2>/dev/null || true
chmod -R 755 "$PROJECT_DIR/uploads" 2>/dev/null || true
chmod 755 "$PROJECT_DIR" 2>/dev/null || true
echo "✅ 静态文件权限已修复"
echo ""

# 2. 检查子域名配置
echo "步骤 2: 检查子域名配置..."
APP_CONFIG="/etc/nginx/sites-available/app-chaozhiyinqing.top"

if [ -f "$APP_CONFIG" ]; then
    echo "✅ 子域名配置存在"
    echo ""
    echo "当前配置:"
    cat "$APP_CONFIG"
    echo ""
    
    # 备份配置
    cp "$APP_CONFIG" "$APP_CONFIG.backup"
    
    # 修复配置
    cat > "$APP_CONFIG" << EOF
# 子域名配置 - app.chaozhiyinqing.top (超智引擎项目)
server {
    listen 80;
    server_name app.chaozhiyinqing.top;

    access_log /var/log/nginx/app-chaozhiyinqing.top-access.log;
    error_log /var/log/nginx/app-chaozhiyinqing.top-error.log;

    # 静态文件直接服务（提高性能，避免权限问题）
    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        
        # 允许访问
        allow all;
    }

    # 上传文件
    location /uploads/ {
        alias $PROJECT_DIR/uploads/;
        allow all;
    }

    # 代理到超智引擎 Flask 应用
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
}
EOF
    
    echo "✅ 子域名配置已更新"
    
    # 启用配置
    if [ ! -L "/etc/nginx/sites-enabled/app-chaozhiyinqing.top" ]; then
        ln -s "$APP_CONFIG" "/etc/nginx/sites-enabled/app-chaozhiyinqing.top"
        echo "✅ 子域名配置已启用"
    fi
else
    echo "⚠️  子域名配置不存在，创建新配置..."
    
    cat > "$APP_CONFIG" << EOF
# 子域名配置 - app.chaozhiyinqing.top (超智引擎项目)
server {
    listen 80;
    server_name app.chaozhiyinqing.top;

    access_log /var/log/nginx/app-chaozhiyinqing.top-access.log;
    error_log /var/log/nginx/app-chaozhiyinqing.top-error.log;

    # 静态文件直接服务
    location /static/ {
        alias $PROJECT_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
        allow all;
    }

    # 上传文件
    location /uploads/ {
        alias $PROJECT_DIR/uploads/;
        allow all;
    }

    # 代理到 Flask 应用
    location / {
        proxy_pass http://localhost:$APP_PORT;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
EOF
    
    ln -s "$APP_CONFIG" "/etc/nginx/sites-enabled/app-chaozhiyinqing.top"
    echo "✅ 子域名配置已创建并启用"
fi
echo ""

# 3. 检查主域名配置的静态文件设置
echo "步骤 3: 检查主域名配置..."
MAIN_CONFIG="/etc/nginx/sites-available/chaozhiyinqing.top"

if [ -f "$MAIN_CONFIG" ]; then
    if ! grep -q "location /static/" "$MAIN_CONFIG"; then
        echo "⚠️  主域名配置缺少静态文件配置，正在添加..."
        
        # 备份
        cp "$MAIN_CONFIG" "$MAIN_CONFIG.backup"
        
        # 在 location / 之前插入静态文件配置
        sed -i '/location \/ {/i\    # 静态文件直接服务\n    location /static/ {\n        alias '"$PROJECT_DIR"'/static/;\n        expires 30d;\n        add_header Cache-Control "public, immutable";\n        allow all;\n    }\n\n    # 上传文件\n    location /uploads/ {\n        alias '"$PROJECT_DIR"'/uploads/;\n        allow all;\n    }\n' "$MAIN_CONFIG"
        
        echo "✅ 主域名配置已更新"
    else
        echo "✅ 主域名配置已包含静态文件配置"
    fi
fi
echo ""

# 4. 测试配置
echo "步骤 4: 测试 Nginx 配置..."
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
    exit 1
fi

# 5. 验证静态文件访问
echo ""
echo "步骤 5: 验证静态文件访问..."
sleep 1

# 测试子域名
echo "测试子域名静态文件访问:"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H 'Host: app.chaozhiyinqing.top' http://localhost/static/style_new.css 2>/dev/null || echo "000")
if [ "$STATUS" = "200" ]; then
    echo "✅ 子域名静态文件访问正常"
else
    echo "⚠️  子域名静态文件访问返回: $STATUS"
fi

# 测试主域名
echo "测试主域名静态文件访问:"
STATUS=$(curl -s -o /dev/null -w "%{http_code}" -H 'Host: chaozhiyinqing.top' http://localhost/static/style_new.css 2>/dev/null || echo "000")
if [ "$STATUS" = "200" ]; then
    echo "✅ 主域名静态文件访问正常"
else
    echo "⚠️  主域名静态文件访问返回: $STATUS"
fi

echo ""
echo "=========================================="
echo "  修复完成"
echo "=========================================="
echo ""
echo "请清除浏览器缓存后重新访问:"
echo "  http://app.chaozhiyinqing.top"
echo "  http://chaozhiyinqing.top"
echo ""

