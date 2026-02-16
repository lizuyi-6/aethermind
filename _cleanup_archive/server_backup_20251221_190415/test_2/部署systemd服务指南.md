# Flask应用后台运行指南

## 方法一：使用 systemd 服务（推荐）⭐

这是最推荐的方法，可以自动启动、自动重启，并提供日志管理。

### 1. 上传服务文件到服务器

在本地执行：
```bash
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 flask-app.service root@60.10.230.156:/etc/systemd/system/
```

### 2. 在服务器上执行以下命令

```bash
# SSH连接到服务器
ssh -i ~/.ssh/KeyPair-6418.pem -p 2950 root@60.10.230.156

# 重新加载systemd配置
systemctl daemon-reload

# 启用服务（开机自启）
systemctl enable flask-app.service

# 启动服务
systemctl start flask-app.service

# 查看服务状态
systemctl status flask-app.service

# 查看日志
journalctl -u flask-app.service -f
```

### 3. 常用管理命令

```bash
# 启动服务
systemctl start flask-app.service

# 停止服务
systemctl stop flask-app.service

# 重启服务
systemctl restart flask-app.service

# 查看状态
systemctl status flask-app.service

# 查看日志（实时）
journalctl -u flask-app.service -f

# 查看最近100行日志
journalctl -u flask-app.service -n 100

# 禁用开机自启
systemctl disable flask-app.service
```

### 4. 修改服务配置

如果需要修改服务配置：
```bash
# 编辑服务文件
nano /etc/systemd/system/flask-app.service

# 修改后重新加载并重启
systemctl daemon-reload
systemctl restart flask-app.service
```

---

## 方法二：使用 nohup（简单快速）

### 1. 上传脚本到服务器

在本地执行：
```bash
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 start_flask_nohup.sh root@60.10.230.156:/var/www/html/
```

### 2. 在服务器上执行

```bash
# SSH连接到服务器
ssh -i ~/.ssh/KeyPair-6418.pem -p 2950 root@60.10.230.156

# 进入项目目录
cd /var/www/html

# 给脚本添加执行权限
chmod +x start_flask_nohup.sh

# 运行脚本
./start_flask_nohup.sh
```

### 3. 管理命令

```bash
# 查看日志
tail -f /var/www/html/flask_app.log

# 停止服务
pkill -f "python3.*app.py"

# 查看进程
ps aux | grep "python3.*app.py"
```

---

## 方法三：使用 screen（可以重新连接）

### 1. 上传脚本到服务器

在本地执行：
```bash
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 start_flask_screen.sh root@60.10.230.156:/var/www/html/
```

### 2. 在服务器上执行

```bash
# SSH连接到服务器
ssh -i ~/.ssh/KeyPair-6418.pem -p 2950 root@60.10.230.156

# 进入项目目录
cd /var/www/html

# 给脚本添加执行权限
chmod +x start_flask_screen.sh

# 运行脚本
./start_flask_screen.sh
```

### 3. 管理命令

```bash
# 查看所有screen会话
screen -list

# 连接到Flask应用的screen会话
screen -r flask_app

# 在screen中按 Ctrl+A 然后按 D 可以断开（不停止服务）

# 停止服务
screen -S flask_app -X quit
```

---

## 推荐方案对比

| 方法 | 优点 | 缺点 | 推荐度 |
|------|------|------|--------|
| **systemd** | 自动启动、自动重启、日志管理、系统级管理 | 配置稍复杂 | ⭐⭐⭐⭐⭐ |
| **nohup** | 简单快速、无需配置 | 需要手动管理、无自动重启 | ⭐⭐⭐ |
| **screen** | 可以重新连接查看输出 | 需要手动管理、无自动重启 | ⭐⭐⭐ |

---

## 当前运行的服务检查

如果已经有Flask应用在运行，先停止它：

```bash
# 查找Flask进程
ps aux | grep "python3.*app.py"

# 停止所有Flask进程
pkill -f "python3.*app.py"

# 或者使用systemctl（如果已配置）
systemctl stop flask-app.service
```

---

## 快速部署脚本（Windows）

创建一个批处理文件 `deploy_service.bat`：

```batch
@echo off
echo 正在上传systemd服务文件...
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 flask-app.service root@60.10.230.156:/etc/systemd/system/

echo.
echo 请在服务器上执行以下命令：
echo.
echo systemctl daemon-reload
echo systemctl enable flask-app.service
echo systemctl start flask-app.service
echo systemctl status flask-app.service
echo.
pause
```




















