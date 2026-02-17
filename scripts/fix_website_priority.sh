#!/bin/bash
# 修复网站优先级，确保主域名指向原有网站

set -e

echo "=========================================="
echo "  修复网站优先级配置"
echo "=========================================="
echo ""

# 1. 检查 default 配置
echo "步骤 1: 检查 default 配置..."
DEFAULT_CONFIG="/etc/nginx/sites-available/default"
DEFAULT_ENABLED="/etc/nginx/sites-enabled/default"

if [ -L "$DEFAULT_ENABLED" ]; then
    echo "⚠️  发现 default 配置已启用，可能覆盖主域名"
    echo "   建议禁用或修改 default 配置"
    echo ""
    
    # 检查 default 是否使用 default_server
    if grep -q "default_server" "$DEFAULT_CONFIG"; then
        echo "❌ default 配置使用了 default_server，会捕获所有未匹配的请求"
        echo "   这可能导致主域名被 default 配置处理"
        echo ""
        
        read -p "是否禁用 default 配置? (y/n) [默认: y]: " DISABLE_DEFAULT
        DISABLE_DEFAULT=${DISABLE_DEFAULT:-y}
        
        if [ "$DISABLE_DEFAULT" = "y" ]; then
            rm -f "$DEFAULT_ENABLED"
            echo "✅ default 配置已禁用"
        fi
    fi
else
    echo "✅ default 配置未启用"
fi
echo ""

# 2. 确保主域名配置优先级最高
echo "步骤 2: 确保主域名配置正确..."
MAIN_CONFIG="/etc/nginx/sites-available/chaozhiyinqing.top"

if [ -f "$MAIN_CONFIG" ]; then
    # 检查是否使用 default_server
    if ! grep -q "default_server" "$MAIN_CONFIG"; then
        echo "⚠️  主域名配置未使用 default_server"
        echo "   添加 default_server 以确保优先级..."
        
        # 备份
        cp "$MAIN_CONFIG" "$MAIN_CONFIG.backup"
        
        # 添加 default_server
        sed -i 's/listen 80;/listen 80 default_server;/' "$MAIN_CONFIG"
        
        echo "✅ 已添加 default_server"
    else
        echo "✅ 主域名配置已使用 default_server"
    fi
    
    # 确保配置已启用
    if [ ! -L "/etc/nginx/sites-enabled/chaozhiyinqing.top" ]; then
        ln -s "$MAIN_CONFIG" "/etc/nginx/sites-enabled/chaozhiyinqing.top"
        echo "✅ 主域名配置已启用"
    fi
else
    echo "❌ 主域名配置不存在"
    exit 1
fi
echo ""

# 3. 检查新应用配置
echo "步骤 3: 检查新应用配置..."
APP_CONFIG="/etc/nginx/sites-available/app-chaozhiyinqing.top"

if [ -f "$APP_CONFIG" ]; then
    # 确保新应用只使用子域名
    if grep -q "server_name.*chaozhiyinqing.top" "$APP_CONFIG" && ! grep -q "server_name.*app.chaozhiyinqing.top" "$APP_CONFIG"; then
        echo "❌ 新应用配置可能包含主域名，需要修复"
        echo "   新应用应该只使用: app.chaozhiyinqing.top"
    else
        echo "✅ 新应用配置正确（使用子域名）"
    fi
    
    # 确保不使用 default_server
    if grep -q "default_server" "$APP_CONFIG"; then
        echo "⚠️  新应用配置使用了 default_server，需要移除"
        cp "$APP_CONFIG" "$APP_CONFIG.backup"
        sed -i 's/listen 80 default_server;/listen 80;/' "$APP_CONFIG"
        echo "✅ 已移除新应用配置的 default_server"
    fi
else
    echo "⚠️  新应用配置不存在"
fi
echo ""

# 4. 查找原有网站文件
echo "步骤 4: 查找原有网站文件..."
echo "----------------------------------------"

# 常见网站目录
WEB_ROOTS=(
    "/var/www/html"
    "/var/www/chaozhiyinqing.top"
    "/var/www/chaozhiyinqing"
    "/home/www"
    "/usr/share/nginx/html"
)

FOUND_ROOT=""
for root in "${WEB_ROOTS[@]}"; do
    if [ -d "$root" ] && [ "$(find "$root" -maxdepth 1 -type f \( -name '*.html' -o -name '*.php' -o -name 'index.*' \) 2>/dev/null | wc -l)" -gt 0 ]; then
        echo "✅ 找到网站文件: $root"
        FOUND_ROOT="$root"
        ls -la "$root" | head -10
        break
    fi
done

if [ -z "$FOUND_ROOT" ]; then
    echo "⚠️  未找到原有网站文件"
    echo "   请手动指定网站根目录"
    echo ""
    read -p "请输入原有网站的根目录路径: " MANUAL_ROOT
    if [ -d "$MANUAL_ROOT" ]; then
        FOUND_ROOT="$MANUAL_ROOT"
        echo "✅ 使用指定目录: $FOUND_ROOT"
    else
        echo "⚠️  目录不存在，使用默认: /var/www/html"
        FOUND_ROOT="/var/www/html"
    fi
fi

# 5. 更新主域名配置的根目录
echo ""
echo "步骤 5: 更新主域名配置..."
CURRENT_ROOT=$(grep "root " "$MAIN_CONFIG" | head -1 | awk '{print $2}' | sed 's/;//')

if [ "$CURRENT_ROOT" != "$FOUND_ROOT" ]; then
    echo "   当前根目录: $CURRENT_ROOT"
    echo "   更新为: $FOUND_ROOT"
    
    cp "$MAIN_CONFIG" "$MAIN_CONFIG.backup2"
    sed -i "s|root $CURRENT_ROOT;|root $FOUND_ROOT;|" "$MAIN_CONFIG"
    echo "✅ 根目录已更新"
else
    echo "✅ 根目录配置正确: $FOUND_ROOT"
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
    exit 1
fi

echo ""
echo "=========================================="
echo "  修复完成"
echo "=========================================="
echo ""
echo "配置摘要:"
echo "  主网站域名: chaozhiyinqing.top"
echo "  网站根目录: $FOUND_ROOT"
echo "  新应用域名: app.chaozhiyinqing.top"
echo ""
echo "测试访问:"
echo "  curl -H 'Host: chaozhiyinqing.top' http://localhost"
echo "  curl -H 'Host: app.chaozhiyinqing.top' http://localhost"
echo ""

