#!/bin/bash
# 更新模型配置为 qwen3-32b

echo "=========================================="
echo "  更新模型配置为 qwen3-32b"
echo "=========================================="
echo ""

# 检查服务文件是否存在
SERVICE_FILE="/etc/systemd/system/flask-app.service"

if [ -f "$SERVICE_FILE" ]; then
    echo "[1/3] 更新 systemd 服务配置..."
    
    # 检查是否已经有 MODEL_NAME 环境变量
    if grep -q "Environment=\"MODEL_NAME=" "$SERVICE_FILE"; then
        # 更新现有的 MODEL_NAME
        sudo sed -i 's/Environment="MODEL_NAME=.*"/Environment="MODEL_NAME=qwen3-32b"/' "$SERVICE_FILE"
        echo "✅ 已更新现有的 MODEL_NAME 环境变量"
    else
        # 检查是否有注释掉的 MODEL_NAME
        if grep -q "# Environment=\"MODEL_NAME=" "$SERVICE_FILE"; then
            # 取消注释并更新
            sudo sed -i 's/# Environment="MODEL_NAME=.*"/Environment="MODEL_NAME=qwen3-32b"/' "$SERVICE_FILE"
            echo "✅ 已取消注释并设置 MODEL_NAME=qwen3-32b"
        else
            # 添加新的环境变量（在 Environment="PATH= 之后）
            sudo sed -i '/Environment="PATH=/a Environment="MODEL_NAME=qwen3-32b"' "$SERVICE_FILE"
            echo "✅ 已添加 MODEL_NAME=qwen3-32b 环境变量"
        fi
    fi
    
    echo ""
    echo "当前服务配置中的 MODEL_NAME:"
    grep "MODEL_NAME" "$SERVICE_FILE" || echo "未找到 MODEL_NAME 配置"
    echo ""
else
    echo "⚠️  服务文件不存在: $SERVICE_FILE"
    echo "请先安装服务或手动配置环境变量"
    echo ""
fi

# 检查环境文件
ENV_FILE="/etc/flask-app.env"
if [ -f "$ENV_FILE" ]; then
    echo "[2/3] 更新环境文件..."
    if grep -q "MODEL_NAME=" "$ENV_FILE"; then
        sudo sed -i 's/MODEL_NAME=.*/MODEL_NAME=qwen3-32b/' "$ENV_FILE"
        echo "✅ 已更新环境文件中的 MODEL_NAME"
    else
        echo "MODEL_NAME=qwen3-32b" | sudo tee -a "$ENV_FILE" > /dev/null
        echo "✅ 已添加 MODEL_NAME 到环境文件"
    fi
    echo ""
else
    echo "[2/3] 环境文件不存在，跳过"
    echo ""
fi

# 重新加载并重启服务
if [ -f "$SERVICE_FILE" ]; then
    echo "[3/3] 重新加载并重启服务..."
    sudo systemctl daemon-reload
    sudo systemctl restart flask-app.service
    
    echo ""
    echo "等待服务启动..."
    sleep 3
    
    # 检查服务状态
    if sudo systemctl is-active --quiet flask-app.service; then
        echo "✅ 服务已重启"
    else
        echo "⚠️  服务可能未正常启动，请检查日志:"
        echo "   sudo journalctl -u flask-app.service -n 50"
    fi
    echo ""
fi

echo "=========================================="
echo "  配置更新完成"
echo "=========================================="
echo ""
echo "验证配置："
echo "  curl http://localhost:5000/api/config"
echo ""

