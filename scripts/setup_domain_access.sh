#!/bin/bash
# 配置域名访问脚本（不影响现有网站）

set -e

echo "=========================================="
echo "  配置域名访问（不影响现有网站）"
echo "=========================================="
echo ""

DOMAIN="chaozhiyinqing.top"
APP_PORT=5001  # 新应用端口（可修改）

# 获取脚本目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 1. 检查 Nginx 是否安装
echo "步骤 1: 检查 Nginx..."
if ! command -v nginx &> /dev/null; then
    echo "⚠️  Nginx 未安装，正在安装..."
    if command -v yum &> /dev/null; then
        yum install -y nginx
    elif command -v apt-get &> /dev/null; then
        apt-get update
        apt-get install -y nginx
    else
        echo "❌ 无法自动安装 Nginx，请手动安装"
        exit 1
    fi
    echo "✅ Nginx 已安装"
else
    echo "✅ Nginx 已安装"
    nginx -v
fi
echo ""

# 2. 检查现有 Nginx 配置
echo "步骤 2: 检查现有 Nginx 配置..."
if [ -f /etc/nginx/nginx.conf ]; then
    echo "✅ 找到 Nginx 主配置文件: /etc/nginx/nginx.conf"
fi

# 查找现有站点配置
if [ -d /etc/nginx/sites-available ]; then
    echo "✅ 找到 sites-available 目录"
    echo "现有配置:"
    ls -la /etc/nginx/sites-available/ 2>/dev/null | head -10
elif [ -d /etc/nginx/conf.d ]; then
    echo "✅ 找到 conf.d 目录"
    echo "现有配置:"
    ls -la /etc/nginx/conf.d/ 2>/dev/null | head -10
fi
echo ""

# 3. 选择配置方式
echo "步骤 3: 选择访问方式"
echo "1. 使用子域名: app.chaozhiyinqing.top (推荐)"
echo "2. 使用路径: chaozhiyinqing.top/app"
echo ""
read -p "请选择 (1/2) [默认: 1]: " ACCESS_METHOD
ACCESS_METHOD=${ACCESS_METHOD:-1}

# 4. 选择应用端口
echo ""
read -p "请输入应用运行端口 [默认: 5001]: " INPUT_PORT
APP_PORT=${INPUT_PORT:-5001}

# 检查端口是否被占用
if command -v netstat &> /dev/null; then
    if netstat -tlnp 2>/dev/null | grep -q ":$APP_PORT "; then
        echo "⚠️  警告: 端口 $APP_PORT 已被占用"
        read -p "是否继续? (y/n): " CONTINUE
        if [ "$CONTINUE" != "y" ]; then
            exit 1
        fi
    fi
fi

# 5. 创建 Nginx 配置
echo ""
echo "步骤 4: 创建 Nginx 配置..."

if [ "$ACCESS_METHOD" = "1" ]; then
    # 子域名方式
    SERVER_NAME="app.$DOMAIN"
    CONFIG_FILE="/etc/nginx/sites-available/app-$DOMAIN"
    if [ ! -d /etc/nginx/sites-available ]; then
        CONFIG_FILE="/etc/nginx/conf.d/app-$DOMAIN.conf"
    fi
    
    cat > "/tmp/app-$DOMAIN.conf" << EOF
# 新应用配置 - 子域名方式
# 不影响现有网站配置

server {
    listen 80;
    server_name $SERVER_NAME;

    # 日志
    access_log /var/log/nginx/app-$DOMAIN-access.log;
    error_log /var/log/nginx/app-$DOMAIN-error.log;

    # 代理到 Flask 应用
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

    # 静态文件缓存（可选）
    location /static/ {
        alias $SCRIPT_DIR/static/;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }
}
EOF
    echo "✅ 配置方式: 子域名 ($SERVER_NAME)"
else
    # 路径方式
    CONFIG_FILE="/etc/nginx/sites-available/app-$DOMAIN-path"
    if [ ! -d /etc/nginx/sites-available ]; then
        CONFIG_FILE="/etc/nginx/conf.d/app-$DOMAIN-path.conf"
    fi
    
    cat > "/tmp/app-$DOMAIN-path.conf" << EOF
# 新应用配置 - 路径方式
# 添加到现有 server 块的 location 配置

# 如果使用 sites-available，需要添加到现有配置文件中
# 如果使用 conf.d，创建独立文件

# 在现有 server 块中添加以下 location：
location /app {
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
    
    # 移除 /app 前缀（如果需要）
    # rewrite ^/app(.*) \$1 break;
}
EOF
    echo "✅ 配置方式: 路径 (/app)"
fi

# 6. 安装配置
if [ "$EUID" -eq 0 ]; then
if [ "$ACCESS_METHOD" = "1" ]; then
        # 子域名方式：创建独立配置文件
        cp "/tmp/app-$DOMAIN.conf" "$CONFIG_FILE"
    
        # 创建符号链接（如果使用 sites-available）
        if [ -d /etc/nginx/sites-enabled ] && [ ! -L "/etc/nginx/sites-enabled/app-$DOMAIN" ]; then
            ln -s "$CONFIG_FILE" "/etc/nginx/sites-enabled/app-$DOMAIN"
    fi
    
        echo "✅ 配置文件已创建: $CONFIG_FILE"
    else
        # 路径方式：提示手动添加
        echo "⚠️  路径方式需要手动添加到现有配置"
        echo "配置文件已保存到: /tmp/app-$DOMAIN-path.conf"
        echo "请手动将 location /app 块添加到现有 server 配置中"
        echo ""
        echo "编辑现有配置:"
        if [ -f /etc/nginx/sites-available/$DOMAIN ]; then
            echo "  sudo nano /etc/nginx/sites-available/$DOMAIN"
        elif [ -f /etc/nginx/conf.d/$DOMAIN.conf ]; then
            echo "  sudo nano /etc/nginx/conf.d/$DOMAIN.conf"
    else
            echo "  sudo nano /etc/nginx/sites-available/default"
        fi
    fi
else
    echo "⚠️  需要 root 权限安装配置"
    echo "配置文件已保存到: /tmp/"
    echo "请使用 sudo 复制配置文件"
fi

# 7. 测试并重载 Nginx
if [ "$EUID" -eq 0 ] && [ "$ACCESS_METHOD" = "1" ]; then
    echo ""
    echo "步骤 5: 测试 Nginx 配置..."
    if nginx -t; then
        echo "✅ Nginx 配置测试通过"
        echo ""
        read -p "是否立即重载 Nginx? (y/n) [默认: y]: " RELOAD
        RELOAD=${RELOAD:-y}
        if [ "$RELOAD" = "y" ]; then
    systemctl reload nginx
    echo "✅ Nginx 已重载"
        fi
else
        echo "❌ Nginx 配置测试失败，请检查配置"
        exit 1
    fi
fi

# 8. 创建启动脚本
echo ""
echo "步骤 6: 创建应用启动脚本..."
START_SCRIPT="start_app_port_${APP_PORT}.sh"
cat > "$START_SCRIPT" << EOF
#!/bin/bash
# 启动 Flask 应用（端口 $APP_PORT）

cd "$SCRIPT_DIR"

# 停止可能正在运行的进程
pkill -f "python.*app.py.*port=$APP_PORT" 2>/dev/null || true
sleep 1

# 后台运行
nohup python3 app.py --port $APP_PORT > app_${APP_PORT}.log 2>&1 &

PID=\$!
sleep 2

if ps -p \$PID > /dev/null; then
    echo "✅ Flask 应用已启动"
    echo "   进程ID: \$PID"
    echo "   端口: $APP_PORT"
    echo "   日志: $SCRIPT_DIR/app_${APP_PORT}.log"
    if [ "$ACCESS_METHOD" = "1" ]; then
        echo "   访问地址: http://app.$DOMAIN"
    else
        echo "   访问地址: http://$DOMAIN/app"
    fi
    echo "   本地测试: http://localhost:$APP_PORT"
else
    echo "❌ 应用启动失败，请查看日志:"
    echo "   tail -f $SCRIPT_DIR/app_${APP_PORT}.log"
    exit 1
fi
EOF

chmod +x "$START_SCRIPT"
echo "✅ 启动脚本已创建: $START_SCRIPT"

# 9. DNS 配置提示
echo ""
echo "=========================================="
echo "  配置完成"
echo "=========================================="
echo ""
if [ "$ACCESS_METHOD" = "1" ]; then
    echo "📋 DNS 配置（如果使用子域名）:"
    echo "   在域名管理后台添加 A 记录："
    echo "   类型: A"
    echo "   主机: app"
    echo "   值: $(hostname -I | awk '{print $1}')"
    echo "   TTL: 600"
    echo ""
    echo "   或使用 CNAME："
    echo "   类型: CNAME"
    echo "   主机: app"
    echo "   值: $DOMAIN"
    echo ""
fi

echo "🚀 启动应用:"
echo "   ./$START_SCRIPT"
echo ""
echo "📝 常用命令:"
echo "   查看日志: tail -f app_${APP_PORT}.log"
echo "   停止服务: pkill -f 'python.*app.py.*port=$APP_PORT'"
echo "   查看状态: ps aux | grep 'python.*app.py'"
echo "   测试 Nginx: sudo nginx -t"
echo "   重载 Nginx: sudo systemctl reload nginx"
echo ""
