#!/bin/bash
# 切换到通义千问配置脚本（包含API Key）

cd /var/www/html

echo "=========================================="
echo "  切换到通义千问配置"
echo "=========================================="
echo ""

# 配置信息
MODEL_PROVIDER="tongyi"
DASHSCOPE_API_KEY="sk-a05fb9f14d734998a8d0a7af05503058"
API_BASE_URL="https://dashscope.aliyuncs.com/compatible-mode/v1"
MODEL_NAME="qwen3-30b-a3b-instruct-2507"
TEMPERATURE="0.7"
MAX_TOKENS="32000"

# 创建 .env 文件
cat > .env << EOF
# 模型提供商
MODEL_PROVIDER=${MODEL_PROVIDER}

# 通义千问 API 密钥
DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}

# API 基础 URL
API_BASE_URL=${API_BASE_URL}

# 模型名称
MODEL_NAME=${MODEL_NAME}

# 可选参数
TEMPERATURE=${TEMPERATURE}
MAX_TOKENS=${MAX_TOKENS}
EOF

echo "✅ 配置已更新到 .env 文件"
echo ""
echo "📋 当前配置:"
echo "  - 模型提供商: ${MODEL_PROVIDER}"
echo "  - API URL: ${API_BASE_URL}"
echo "  - 模型名称: ${MODEL_NAME}"
echo "  - Temperature: ${TEMPERATURE}"
echo "  - Max Tokens: ${MAX_TOKENS}"
echo ""

# 更新 systemd 服务配置
SERVICE_FILE="/etc/systemd/system/flask-app.service"
if [ -f "$SERVICE_FILE" ]; then
    echo "🔄 更新 systemd 服务配置..."
    
    # 检查并更新 MODEL_PROVIDER
    if grep -q "Environment=\"MODEL_PROVIDER=" "$SERVICE_FILE"; then
        sudo sed -i 's/Environment="MODEL_PROVIDER=.*"/Environment="MODEL_PROVIDER=tongyi"/' "$SERVICE_FILE"
    else
        sudo sed -i '/Environment="PATH=/a Environment="MODEL_PROVIDER=tongyi"' "$SERVICE_FILE"
    fi
    
    # 检查并更新 DASHSCOPE_API_KEY
    if grep -q "Environment=\"DASHSCOPE_API_KEY=" "$SERVICE_FILE"; then
        sudo sed -i "s|Environment=\"DASHSCOPE_API_KEY=.*\"|Environment=\"DASHSCOPE_API_KEY=${DASHSCOPE_API_KEY}\"|" "$SERVICE_FILE"
    else
        sudo sed -i '/Environment="MODEL_PROVIDER=/a Environment="DASHSCOPE_API_KEY='"${DASHSCOPE_API_KEY}"'"' "$SERVICE_FILE"
    fi
    
    # 检查并更新 API_BASE_URL
    if grep -q "Environment=\"API_BASE_URL=" "$SERVICE_FILE"; then
        sudo sed -i "s|Environment=\"API_BASE_URL=.*\"|Environment=\"API_BASE_URL=${API_BASE_URL}\"|" "$SERVICE_FILE"
    else
        sudo sed -i '/Environment="DASHSCOPE_API_KEY=/a Environment="API_BASE_URL='"${API_BASE_URL}"'"' "$SERVICE_FILE"
    fi
    
    # 检查并更新 MODEL_NAME
    if grep -q "Environment=\"MODEL_NAME=" "$SERVICE_FILE"; then
        sudo sed -i "s|Environment=\"MODEL_NAME=.*\"|Environment=\"MODEL_NAME=${MODEL_NAME}\"|" "$SERVICE_FILE"
    else
        sudo sed -i '/Environment="API_BASE_URL=/a Environment="MODEL_NAME='"${MODEL_NAME}"'"' "$SERVICE_FILE"
    fi
    
    echo "✅ 服务配置已更新"
    echo ""
    
    # 重新加载并重启服务
    echo "🔄 重新加载 systemd 配置..."
    sudo systemctl daemon-reload
    
    echo "🔄 重启服务..."
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
else
    echo "⚠️  服务文件不存在，跳过服务配置更新"
    echo "   如需后台运行，请先安装服务: ./install_service.sh"
    echo ""
fi

echo "=========================================="
echo "  配置完成"
echo "=========================================="
echo ""
echo "验证配置："
echo "  curl http://localhost:5000/api/config"
echo ""

