#!/bin/bash
# 切换到通义千问 - 已配置API密钥

cd /var/www/html

echo "=========================================="
echo "  切换到通义千问配置"
echo "=========================================="
echo ""

# 创建 .env 文件
cat > .env << 'EOF'
# 模型提供商
MODEL_PROVIDER=tongyi

# 通义千问 API 密钥
DASHSCOPE_API_KEY=sk-a05fb9f14d734998a8d0a7af05503058

# 模型名称
MODEL_NAME=qwen3-max

# 可选参数
TEMPERATURE=0.7
MAX_TOKENS=32000
EOF

echo "✅ 配置已更新"
echo ""

# 验证配置
echo "📋 当前配置:"
cat .env | grep -v "API_KEY" | grep -v "^#"
echo ""

# 停止当前 Flask
echo "🛑 停止当前 Flask 进程..."
pkill -f "python3 app.py" || true
sleep 2

# 启动 Flask
echo "🚀 启动 Flask 应用..."
echo ""
python3 app.py

