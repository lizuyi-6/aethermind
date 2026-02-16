#!/bin/bash
# 使用screen在后台运行Flask应用（SSH断开后可以重新连接）

cd /var/www/html

# 检查是否已有screen会话
if screen -list | grep -q "flask_app"; then
    echo "Flask应用已在screen会话中运行"
    echo "重新连接: screen -r flask_app"
    exit 0
fi

# 创建新的screen会话并启动Flask应用
screen -dmS flask_app /usr/local/python3.11/bin/python3 app.py

echo "Flask应用已在screen会话中启动"
echo ""
echo "查看会话: screen -list"
echo "连接会话: screen -r flask_app"
echo "断开会话: 在screen中按 Ctrl+A 然后按 D"
echo "停止服务: screen -S flask_app -X quit"




















