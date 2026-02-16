# 服务器 API 连接配置指南

## 📋 目录

1. [切换到通义千问](#切换到通义千问) ⭐ **推荐**
2. [使用自定义大模型](#使用自定义大模型)
3. [Connection error 问题解决](#connection-error-问题解决)

---

## 🚀 切换到通义千问

### 快速切换（一键执行）

在服务器上执行以下命令：

```bash
cd /var/www/html && \
cat > .env << 'EOF'
MODEL_PROVIDER=tongyi
DASHSCOPE_API_KEY=你的通义千问API密钥
MODEL_NAME=qwen3-max
EOF
&& \
pkill -f "python3 app.py" && \
python3 app.py
```

**重要**：将 `你的通义千问API密钥` 替换为你的实际 API 密钥。

### 详细步骤

#### 步骤 1：编辑 .env 文件

```bash
cd /var/www/html
nano .env
```

#### 步骤 2：配置通义千问

在 `.env` 文件中添加或修改以下内容：

```bash
# 使用通义千问
MODEL_PROVIDER=tongyi
DASHSCOPE_API_KEY=你的通义千问API密钥
MODEL_NAME=qwen3-max

# 可选参数
TEMPERATURE=0.7
MAX_TOKENS=32000
```

**配置说明**：
- `MODEL_PROVIDER=tongyi`：指定使用通义千问
- `DASHSCOPE_API_KEY`：你的通义千问 API 密钥（必需）
- `MODEL_NAME=qwen3-max`：默认模型，也可以使用 `qwen-plus`、`qwen-turbo` 等
- `API_BASE_URL`：不需要设置，系统会自动使用 `https://dashscope.aliyuncs.com/compatible-mode/v1`

#### 步骤 3：验证配置

```bash
# 检查环境变量
cat .env

# 测试 Python 能否读取配置
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('MODEL_PROVIDER:', os.getenv('MODEL_PROVIDER')); print('DASHSCOPE_API_KEY:', '已设置' if os.getenv('DASHSCOPE_API_KEY') else '未设置')"
```

#### 步骤 4：重启 Flask 应用

```bash
# 停止当前运行的 Flask
pkill -f "python3 app.py"

# 重新启动
cd /var/www/html
python3 app.py
```

### 通义千问模型选项

可用的模型名称：
- `qwen3-max`（默认，推荐）
- `qwen-plus`
- `qwen-turbo`
- `qwen-max`
- `qwen-turbo-max`

---

## 🔧 使用自定义大模型

## 🔴 Connection error 问题解决

错误信息：
```
错误: Connection error.
[错误] 续写API调用失败 (耗时 16.3秒): Connection error.
```

**原因**：Flask 应用无法连接到后端大模型 API。

---

## 🔧 解决方案

### 步骤 1：检查 API 服务是否运行

在服务器上执行：

```bash
# 检查 API 服务是否在运行
netstat -tlnp | grep 1025
# 或
ss -tlnp | grep 1025

# 测试 API 连接
curl http://localhost:1025/v1/models
# 或
curl http://60.10.230.156:1025/v1/models
```

### 步骤 2：配置环境变量（自定义大模型）

在服务器上创建或编辑 `.env` 文件：

```bash
cd /var/www/html
nano .env
```

添加以下内容：

```bash
# 使用自定义大模型
MODEL_PROVIDER=custom
API_BASE_URL=http://localhost:1025/v1
MODEL_NAME=qwen3-32b
CUSTOM_API_KEY=  # 如果API需要密钥，填写这里
```

**重要**：
- 如果 API 服务在同一台服务器上，使用 `http://localhost:1025/v1`
- 如果 API 服务在其他服务器上，使用 `http://60.10.230.156:1025/v1`

### 步骤 3：验证配置

```bash
# 检查环境变量
cat .env

# 测试 Python 能否读取配置
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('API_BASE_URL:', os.getenv('API_BASE_URL'))"
```

### 步骤 4：重启 Flask 应用

```bash
# 停止当前运行的 Flask
pkill -f "python3 app.py"

# 重新启动
cd /var/www/html
python3 app.py
```

---

## 🎯 快速配置脚本

在服务器上执行：

```bash
cd /var/www/html

# 创建 .env 文件
cat > .env << 'EOF'
MODEL_PROVIDER=custom
API_BASE_URL=http://localhost:1025/v1
MODEL_NAME=qwen3-32b
CUSTOM_API_KEY=
EOF

# 验证配置
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('配置:', os.getenv('MODEL_PROVIDER'), os.getenv('API_BASE_URL'))"
```

---

## 🔍 诊断步骤

### 1. 检查 API 服务

```bash
# 方法1：检查端口
netstat -tlnp | grep 1025

# 方法2：测试连接
curl -v http://localhost:1025/v1/models

# 方法3：检查进程
ps aux | grep -E '1025|api|model'
```

### 2. 检查网络连接

```bash
# 测试本地连接
curl http://localhost:1025/v1/models

# 测试外部IP连接
curl http://60.10.230.156:1025/v1/models

# 如果localhost可用但IP不可用，使用localhost
# 如果都不可用，检查API服务是否运行
```

### 3. 检查 Flask 配置

```bash
# 查看 Flask 日志
tail -f /var/www/html/app.log

# 或查看系统日志
journalctl -u flask-app -f
```

---

## ⚙️ 配置选项

### 选项 1：API 在同一台服务器上（推荐）

```bash
# .env 文件
MODEL_PROVIDER=custom
API_BASE_URL=http://localhost:1025/v1
MODEL_NAME=qwen3-32b
```

**优点**：
- 连接更快
- 不经过外部网络
- 更安全

### 选项 2：API 在其他服务器上

```bash
# .env 文件
MODEL_PROVIDER=custom
API_BASE_URL=http://60.10.230.156:1025/v1
MODEL_NAME=qwen3-32b
```

**注意**：确保防火墙允许访问。

---

## 🐛 常见问题

### Q1: 连接超时

**可能原因**：
- API 服务没有运行
- 防火墙阻止
- 网络问题

**解决方法**：
```bash
# 检查 API 服务
systemctl status your-api-service

# 检查防火墙
sudo ufw status
sudo firewall-cmd --list-all

# 测试连接
curl -v --max-time 10 http://localhost:1025/v1/models
```

### Q2: 使用 localhost 还是 IP？

**规则**：
- **同一台服务器**：使用 `http://localhost:1025/v1`
- **不同服务器**：使用 `http://60.10.230.156:1025/v1`

**判断方法**：
```bash
# 如果这个命令成功，使用 localhost
curl http://localhost:1025/v1/models

# 如果失败，检查 API 是否在其他服务器
```

### Q3: 如何测试 API 连接？

```bash
# 测试 API 是否可访问
curl http://localhost:1025/v1/models

# 测试完整调用（需要API密钥）
curl -X POST http://localhost:1025/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "model": "qwen3-32b",
    "messages": [{"role": "user", "content": "你好"}]
  }'
```

---

## 📝 完整配置示例

### .env 文件内容

```bash
# 模型提供商
MODEL_PROVIDER=custom

# API 地址（同一服务器使用 localhost，不同服务器使用 IP）
API_BASE_URL=http://localhost:1025/v1

# 模型名称
MODEL_NAME=qwen3-32b

# API 密钥（如果需要）
CUSTOM_API_KEY=your-api-key-here

# 可选参数
TEMPERATURE=0.9
MAX_TOKENS=16000
```

---

## ✅ 验证配置

配置完成后，测试：

```bash
# 1. 检查环境变量
python3 -c "from dotenv import load_dotenv; import os; load_dotenv(); print('MODEL_PROVIDER:', os.getenv('MODEL_PROVIDER')); print('API_BASE_URL:', os.getenv('API_BASE_URL'))"

# 2. 启动 Flask
cd /var/www/html
python3 app.py

# 3. 在另一个终端测试 API
curl http://localhost:5000/api/config
```

应该返回配置信息。

---

## 🚀 快速修复命令

如果 API 在同一台服务器上：

```bash
cd /var/www/html && \
cat > .env << 'EOF'
MODEL_PROVIDER=custom
API_BASE_URL=http://localhost:1025/v1
MODEL_NAME=qwen3-32b
CUSTOM_API_KEY=
EOF
&& \
pkill -f "python3 app.py" && \
python3 app.py
```

---

**最后更新**：2024-12-15

