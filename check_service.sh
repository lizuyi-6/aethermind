#!/bin/bash
# 服务状态检查脚本
# 用于检查Flask服务是否正常运行

echo "=========================================="
echo "  Flask服务状态检查"
echo "=========================================="
echo ""

# 检查systemd服务
echo "📋 1. 检查systemd服务状态"
if systemctl is-active --quiet flask-app.service 2>/dev/null; then
    echo "   ✅ systemd服务: 运行中"
    systemctl status flask-app.service --no-pager -l | head -n 5
else
    echo "   ❌ systemd服务: 未运行或未安装"
fi
echo ""

# 检查进程
echo "📋 2. 检查进程"
PROCESSES=$(ps aux | grep "[p]ython3.*app.py" | wc -l)
if [ "$PROCESSES" -gt 0 ]; then
    echo "   ✅ 找到 $PROCESSES 个相关进程:"
    ps aux | grep "[p]ython3.*app.py" | awk '{print "      PID:", $2, "| CPU:", $3"% | MEM:", $4"% | 命令:", $11, $12, $13}'
else
    echo "   ❌ 未找到运行中的进程"
fi
echo ""

# 检查端口
echo "📋 3. 检查端口5000"
if command -v netstat >/dev/null 2>&1; then
    PORT_CHECK=$(netstat -tlnp 2>/dev/null | grep ":5000 " || true)
elif command -v ss >/dev/null 2>&1; then
    PORT_CHECK=$(ss -tlnp 2>/dev/null | grep ":5000 " || true)
else
    PORT_CHECK=""
fi

if [ -n "$PORT_CHECK" ]; then
    echo "   ✅ 端口5000正在监听:"
    echo "      $PORT_CHECK"
else
    echo "   ❌ 端口5000未监听"
fi
echo ""

# 检查HTTP访问
echo "📋 4. 检查HTTP访问"
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:5000 2>/dev/null || echo "000")
if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
    echo "   ✅ HTTP访问正常 (状态码: $HTTP_CODE)"
elif [ "$HTTP_CODE" = "000" ]; then
    echo "   ❌ HTTP访问失败 (无法连接)"
else
    echo "   ⚠️  HTTP访问异常 (状态码: $HTTP_CODE)"
fi
echo ""

# 检查日志（最近10行）
echo "📋 5. 最近日志 (systemd)"
if systemctl list-units | grep -q flask-app.service; then
    echo "   最近10行日志:"
    journalctl -u flask-app.service -n 10 --no-pager 2>/dev/null | tail -n 10 || echo "   无法读取日志"
else
    echo "   服务未安装，无法查看systemd日志"
fi
echo ""

# 检查nohup日志
if [ -f "/var/www/html/flask_app.log" ]; then
    echo "📋 6. nohup日志 (最后5行)"
    tail -n 5 /var/www/html/flask_app.log 2>/dev/null || echo "   无法读取日志"
    echo ""
fi

# 检查screen会话
if command -v screen >/dev/null 2>&1; then
    echo "📋 7. 检查screen会话"
    SCREEN_SESSIONS=$(screen -list 2>/dev/null | grep flask_app || true)
    if [ -n "$SCREEN_SESSIONS" ]; then
        echo "   ✅ 找到screen会话:"
        echo "      $SCREEN_SESSIONS"
        echo "   连接命令: screen -r flask_app"
    else
        echo "   ℹ️  未找到screen会话"
    fi
    echo ""
fi

# 总结
echo "=========================================="
echo "  检查完成"
echo "=========================================="
echo ""

# 判断整体状态
if systemctl is-active --quiet flask-app.service 2>/dev/null || [ "$PROCESSES" -gt 0 ]; then
    if [ "$HTTP_CODE" = "200" ] || [ "$HTTP_CODE" = "302" ] || [ "$HTTP_CODE" = "301" ]; then
        echo "✅ 服务运行正常"
        exit 0
    else
        echo "⚠️  服务进程存在，但HTTP访问异常"
        exit 1
    fi
else
    echo "❌ 服务未运行"
    echo ""
    echo "启动建议:"
    echo "  systemd方式: sudo systemctl start flask-app.service"
    echo "  nohup方式: ./start_flask_nohup.sh"
    echo "  screen方式: ./start_flask_screen.sh"
    exit 1
fi

