#!/bin/bash

echo "=========================================="
echo "更新模型为 qwen3-max"
echo "=========================================="

SERVICE_FILE="/etc/systemd/system/flask-app.service"

# 1. 备份服务文件
echo ""
echo "[1] 备份服务文件..."
if [ -f "$SERVICE_FILE" ]; then
    cp "$SERVICE_FILE" "$SERVICE_FILE.bak.$(date +%Y%m%d_%H%M%S)"
    echo "✓ 已备份到: $SERVICE_FILE.bak.$(date +%Y%m%d_%H%M%S)"
fi

# 2. 更新服务文件中的模型名称
echo ""
echo "[2] 更新服务文件中的模型名称..."
if [ -f "$SERVICE_FILE" ]; then
    if grep -q 'Environment="MODEL_NAME=' "$SERVICE_FILE"; then
        sed -i 's/Environment="MODEL_NAME=.*"/Environment="MODEL_NAME=qwen3-max"/' "$SERVICE_FILE"
        echo "✓ 已更新 MODEL_NAME 为 qwen3-max"
    else
        echo "✗ 未找到 MODEL_NAME 配置"
    fi
else
    echo "✗ 服务文件不存在: $SERVICE_FILE"
    exit 1
fi

# 3. 显示更新后的配置
echo ""
echo "[3] 更新后的配置："
grep "MODEL_NAME\|MODEL_PROVIDER\|API_BASE_URL" "$SERVICE_FILE" | grep -v "^#"

# 4. 重新加载systemd
echo ""
echo "[4] 重新加载systemd配置..."
systemctl daemon-reload
echo "✓ systemd配置已重新加载"

# 5. 重启服务
echo ""
echo "[5] 重启Flask应用服务..."
systemctl restart flask-app.service
sleep 3

# 6. 检查服务状态
echo ""
echo "[6] 检查服务状态..."
systemctl status flask-app.service --no-pager -l | head -20

# 7. 验证配置
echo ""
echo "[7] 验证配置..."
sleep 2
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000/api/config 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ]; then
    echo "✓ 服务响应正常，获取配置信息："
    curl -s http://localhost:5000/api/config | python3 -m json.tool 2>/dev/null || curl -s http://localhost:5000/api/config
else
    echo "✗ 服务无响应 (HTTP $HTTP_CODE)"
    echo "查看日志："
    journalctl -u flask-app.service -n 20 --no-pager
fi

echo ""
echo "=========================================="
echo "完成"
echo "=========================================="
echo ""
echo "模型已更新为: qwen3-max"
echo "其他配置保持不变"
echo ""

