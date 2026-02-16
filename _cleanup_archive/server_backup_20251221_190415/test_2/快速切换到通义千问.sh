#!/bin/bash
# 快速切换到通义千问配置

echo "=========================================="
echo "  快速切换到通义千问配置"
echo "=========================================="
echo ""

SERVICE_FILE="/etc/systemd/system/flask-app.service"

if [ ! -f "$SERVICE_FILE" ]; then
    echo "❌ 服务文件不存在: $SERVICE_FILE"
    echo "请先安装服务或手动配置"
    exit 1
fi

echo "[1/4] 备份服务配置文件..."
sudo cp "$SERVICE_FILE" "${SERVICE_FILE}.backup.$(date +%Y%m%d_%H%M%S)"
echo "✅ 备份完成"
echo ""

echo "[2/4] 更新服务配置..."

# 移除旧的 custom 相关环境变量（如果存在）
sudo sed -i '/Environment="MODEL_PROVIDER=custom"/d' "$SERVICE_FILE"
sudo sed -i '/Environment="API_BASE_URL=http:\/\/60.10.230.156:1025\/v1"/d' "$SERVICE_FILE"
sudo sed -i '/Environment="MODEL_NAME=qwen3-32b"/d' "$SERVICE_FILE"
sudo sed -i '/Environment="CUSTOM_API_KEY=/d' "$SERVICE_FILE"

# 检查并更新 MODEL_PROVIDER
if grep -q 'Environment="MODEL_PROVIDER=' "$SERVICE_FILE"; then
    sudo sed -i 's/Environment="MODEL_PROVIDER=.*"/Environment="MODEL_PROVIDER=tongyi"/' "$SERVICE_FILE"
else
    # 在 PATH 环境变量后添加
    sudo sed -i '/Environment="PATH=/a Environment="MODEL_PROVIDER=tongyi"' "$SERVICE_FILE"
fi

# 检查并更新 API_BASE_URL
if grep -q 'Environment="API_BASE_URL=' "$SERVICE_FILE"; then
    sudo sed -i 's|Environment="API_BASE_URL=.*"|Environment="API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1"|' "$SERVICE_FILE"
else
    sudo sed -i '/Environment="MODEL_PROVIDER=/a Environment="API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1"' "$SERVICE_FILE"
fi

# 检查并更新 MODEL_NAME
if grep -q 'Environment="MODEL_NAME=' "$SERVICE_FILE"; then
    sudo sed -i 's/Environment="MODEL_NAME=.*"/Environment="MODEL_NAME=qwen3-30b-a3b-instruct-2507"/' "$SERVICE_FILE"
else
    sudo sed -i '/Environment="API_BASE_URL=/a Environment="MODEL_NAME=qwen3-30b-a3b-instruct-2507"' "$SERVICE_FILE"
fi

# 检查并更新 DASHSCOPE_API_KEY
if grep -q 'Environment="DASHSCOPE_API_KEY=' "$SERVICE_FILE"; then
    sudo sed -i 's|Environment="DASHSCOPE_API_KEY=.*"|Environment="DASHSCOPE_API_KEY=sk-a05fb9f14d734998a8d0a7af05503058"|' "$SERVICE_FILE"
else
    sudo sed -i '/Environment="MODEL_NAME=/a Environment="DASHSCOPE_API_KEY=sk-a05fb9f14d734998a8d0a7af05503058"' "$SERVICE_FILE"
fi

echo "✅ 服务配置已更新"
echo ""

echo "[3/4] 创建/更新 .env 文件..."
cd /var/www/html
cat > .env << 'EOF'
# 模型提供商
MODEL_PROVIDER=tongyi

# 通义千问 API 密钥
DASHSCOPE_API_KEY=sk-a05fb9f14d734998a8d0a7af05503058

# API 基础 URL
API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 模型名称
MODEL_NAME=qwen3-30b-a3b-instruct-2507

# 可选参数
TEMPERATURE=0.7
MAX_TOKENS=32000
EOF
echo "✅ .env 文件已创建/更新"
echo ""

echo "[4/4] 重新加载并重启服务..."
sudo systemctl daemon-reload
sudo systemctl restart flask-app.service

echo ""
echo "等待服务启动..."
sleep 3

# 检查服务状态
if sudo systemctl is-active --quiet flask-app.service; then
    echo "✅ 服务已重启并运行中"
else
    echo "⚠️  服务可能未正常启动，请检查日志:"
    echo "   sudo journalctl -u flask-app.service -n 50"
fi
echo ""

echo "=========================================="
echo "  配置完成"
echo "=========================================="
echo ""
echo "验证配置："
echo "  curl http://localhost:5000/api/config"
echo ""
echo "当前配置应该显示："
echo "  - provider: tongyi"
echo "  - model_name: qwen3-30b-a3b-instruct-2507"
echo ""

