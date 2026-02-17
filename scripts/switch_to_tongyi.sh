#!/bin/bash
# 切换到通义千问的脚本

cd /var/www/html

echo "=========================================="
echo "  切换到通义千问配置"
echo "=========================================="
echo ""

# 读取 API 密钥
read -p "请输入通义千问 API 密钥 (DASHSCOPE_API_KEY): " api_key

if [ -z "$api_key" ]; then
    echo "错误: API 密钥不能为空"
    exit 1
fi

# 创建 .env 文件
cat > .env << EOF
# 模型提供商
MODEL_PROVIDER=tongyi

# 通义千问 API 密钥
DASHSCOPE_API_KEY=${api_key}

# 模型名称
MODEL_NAME=qwen3-max

# 可选参数
TEMPERATURE=0.7
MAX_TOKENS=32000
EOF

echo ""
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

