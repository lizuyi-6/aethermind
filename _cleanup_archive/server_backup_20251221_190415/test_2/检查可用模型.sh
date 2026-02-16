#!/bin/bash
# 检查API服务器上可用的模型列表

echo "=========================================="
echo "  检查API服务器上的可用模型"
echo "=========================================="
echo ""

API_URL="http://60.10.230.156:1025/v1"
# 如果API在同一服务器上，尝试使用localhost
if [ -f "/var/www/html/app.py" ]; then
    API_URL="http://localhost:1025/v1"
fi

echo "API地址: $API_URL"
echo ""

# 尝试获取模型列表
echo "正在获取模型列表..."
echo ""

# 方法1: 尝试使用/models端点
response=$(curl -s "$API_URL/models" 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$response" ]; then
    echo "✅ 成功连接到API"
    echo ""
    echo "可用模型列表:"
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
else
    echo "⚠️  无法通过/models端点获取模型列表"
    echo ""
    echo "尝试其他方法..."
    echo ""
    
    # 方法2: 尝试直接调用chat completions测试常见模型名
    echo "测试常见模型名称..."
    
    models_to_test=(
        "qwen3-32b"
        "qwen3-32b-thinking"
        "qwen3-32b"
        "qwen-32b"
        "qwen-vl-32b"
        "qwen3-vl-32b"
    )
    
    for model in "${models_to_test[@]}"; do
        echo -n "测试模型: $model ... "
        test_response=$(curl -s -X POST "$API_URL/chat/completions" \
            -H "Content-Type: application/json" \
            -d "{\"model\": \"$model\", \"messages\": [{\"role\": \"user\", \"content\": \"test\"}], \"max_tokens\": 5}" \
            2>/dev/null)
        
        if echo "$test_response" | grep -q "Model not found\|422"; then
            echo "❌ 不存在"
        elif echo "$test_response" | grep -q "error"; then
            echo "⚠️  可能有错误（但模型可能存在）"
        else
            echo "✅ 存在"
        fi
    done
fi

echo ""
echo "=========================================="
echo "  检查完成"
echo "=========================================="
echo ""
echo "如果看到模型名称，请使用正确的模型名称更新配置"
echo ""

