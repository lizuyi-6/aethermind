#!/bin/bash
# 测试API连接并查看可用模型

echo "=========================================="
echo "  测试API连接和查看可用模型"
echo "=========================================="
echo ""

# 当前配置的API地址
API_URL="http://60.10.230.156:1025/v1"
# 如果API在同一服务器上，尝试使用localhost
if [ -f "/var/www/html/app.py" ]; then
    API_URL="http://localhost:1025/v1"
fi

echo "测试API地址: $API_URL"
echo ""

# 方法1: 尝试获取模型列表
echo "[1/3] 尝试获取模型列表..."
echo "命令: curl $API_URL/models"
echo ""
response=$(curl -s "$API_URL/models" 2>/dev/null)

if [ $? -eq 0 ] && [ -n "$response" ]; then
    echo "✅ 成功！返回内容："
    echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
    echo ""
else
    echo "❌ 失败或返回空"
    echo ""
fi

# 方法2: 测试当前配置的模型
echo "[2/3] 测试当前配置的模型: qwen3-32b"
echo "命令: curl -X POST $API_URL/chat/completions ..."
echo ""
test_response=$(curl -s -X POST "$API_URL/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
        "model": "qwen3-32b",
        "messages": [{"role": "user", "content": "test"}],
        "max_tokens": 5
    }' 2>/dev/null)

if echo "$test_response" | grep -q "Model not found\|422"; then
    echo "❌ 模型不存在"
    echo "错误信息:"
    echo "$test_response" | python3 -m json.tool 2>/dev/null || echo "$test_response"
elif echo "$test_response" | grep -q "error"; then
    echo "⚠️  有错误（但可能不是模型名称问题）"
    echo "响应:"
    echo "$test_response" | python3 -m json.tool 2>/dev/null || echo "$test_response"
else
    echo "✅ 模型存在！"
    echo "响应:"
    echo "$test_response" | python3 -m json.tool 2>/dev/null || echo "$test_response"
fi
echo ""

# 方法3: 测试常见模型名称
echo "[3/3] 测试常见模型名称..."
models_to_test=(
    "qwen3-32b"
    "qwen3-32b-thinking"
    "qwen-32b"
    "qwen-vl-32b"
    "qwen3-vl-32b"
    "qwen3-vl-32b-thinking"
    "qwen-32b-thinking"
)

for model in "${models_to_test[@]}"; do
    echo -n "测试: $model ... "
    test_resp=$(curl -s -X POST "$API_URL/chat/completions" \
        -H "Content-Type: application/json" \
        -d "{\"model\": \"$model\", \"messages\": [{\"role\": \"user\", \"content\": \"test\"}], \"max_tokens\": 5}" \
        2>/dev/null)
    
    if echo "$test_resp" | grep -q "Model not found\|422"; then
        echo "❌"
    elif echo "$test_resp" | grep -q "\"content\"" || echo "$test_resp" | grep -q "choices"; then
        echo "✅ 存在！"
    else
        echo "⚠️  "
    fi
done

echo ""
echo "=========================================="
echo "  测试完成"
echo "=========================================="
echo ""
echo "如果看到某个模型名称显示 ✅，请使用该模型名称更新配置"
echo ""

