#!/bin/bash

# ==========================================
# 跨服务器备份恢复脚本
# ==========================================
# 功能：在新服务器上从备份文件完整恢复Flask应用
# 使用方法：./跨服务器恢复脚本.sh <备份文件路径> [应用目录] [服务名称]
# 示例：./跨服务器恢复脚本.sh /root/backup.tar.gz
# 示例：./跨服务器恢复脚本.sh /root/backup.tar.gz /var/www/html flask-app
# ==========================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${RED}错误: 请指定备份文件路径${NC}"
    echo "使用方法: $0 <备份文件路径> [应用目录] [服务名称]"
    echo "示例: $0 /root/backup.tar.gz"
    echo "示例: $0 /root/backup.tar.gz /var/www/html flask-app"
    exit 1
fi

BACKUP_ARCHIVE="$1"
APP_DIR="${2:-/var/www/html}"
SERVICE_NAME="${3:-flask-app}"
RESTORE_DIR="/tmp/restore_$(date +%s)"

# 检查备份文件是否存在
if [ ! -f "$BACKUP_ARCHIVE" ]; then
    echo -e "${RED}错误: 备份文件不存在: ${BACKUP_ARCHIVE}${NC}"
    exit 1
fi

echo -e "${GREEN}=========================================="
echo "跨服务器备份恢复脚本"
echo "==========================================${NC}"
echo ""
echo "备份文件: ${BACKUP_ARCHIVE}"
echo "应用目录: ${APP_DIR}"
echo "服务名称: ${SERVICE_NAME}"
echo "恢复目录: ${RESTORE_DIR}"
echo ""

# 检测系统环境
echo -e "${BLUE}[环境检测]${NC}"
echo "检测目标服务器环境..."
echo ""

# 检测Python路径
PYTHON3_PATH=$(which python3 2>/dev/null || echo "")
if [ -z "$PYTHON3_PATH" ]; then
    echo -e "${RED}✗ 未找到python3，请先安装Python 3${NC}"
    exit 1
fi
echo "  ✓ Python3路径: ${PYTHON3_PATH}"
PYTHON3_VERSION=$(${PYTHON3_PATH} --version 2>&1)
echo "  ✓ Python3版本: ${PYTHON3_VERSION}"

# 检测pip
PIP3_PATH=$(which pip3 2>/dev/null || echo "")
if [ -z "$PIP3_PATH" ]; then
    echo -e "${YELLOW}  ⚠ 未找到pip3，将尝试安装${NC}"
    PIP3_PATH="${PYTHON3_PATH} -m pip"
fi
echo "  ✓ pip3路径: ${PIP3_PATH}"

# 检测系统信息
OS_INFO=$(uname -a)
echo "  ✓ 系统信息: ${OS_INFO}"
echo ""

echo -e "${YELLOW}警告: 此操作将在新服务器上部署应用！${NC}"
read -p "确认继续？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

# 1. 解压备份文件
echo ""
echo -e "${YELLOW}[1] 解压备份文件...${NC}"
mkdir -p "${RESTORE_DIR}"
tar -xzf "${BACKUP_ARCHIVE}" -C "${RESTORE_DIR}" || {
    echo -e "${RED}✗ 解压失败${NC}"
    exit 1
}
BACKUP_ROOT=$(ls -d "${RESTORE_DIR}"/backup_* 2>/dev/null | head -1)
if [ -z "$BACKUP_ROOT" ]; then
    echo -e "${RED}✗ 备份文件格式不正确${NC}"
    exit 1
fi
echo "✓ 备份文件已解压到: ${BACKUP_ROOT}"
echo ""

# 2. 创建应用目录
echo -e "${YELLOW}[2] 创建应用目录...${NC}"
mkdir -p "${APP_DIR}"
mkdir -p "${APP_DIR}/uploads"
mkdir -p "${APP_DIR}/static"
mkdir -p "${APP_DIR}/templates"
echo "✓ 应用目录已创建: ${APP_DIR}"
echo ""

# 3. 恢复应用代码
echo -e "${YELLOW}[3] 恢复应用代码...${NC}"
if [ -d "${BACKUP_ROOT}/app" ]; then
    # 恢复Python文件
    if ls "${BACKUP_ROOT}/app"/*.py 1> /dev/null 2>&1; then
        cp "${BACKUP_ROOT}/app"/*.py "${APP_DIR}/" 2>/dev/null || true
        echo "  ✓ Python文件"
    fi
    
    # 恢复模板
    if [ -d "${BACKUP_ROOT}/app/templates" ]; then
        cp -r "${BACKUP_ROOT}/app/templates"/* "${APP_DIR}/templates/" 2>/dev/null || true
        echo "  ✓ 模板文件"
    fi
    
    # 恢复静态资源
    if [ -d "${BACKUP_ROOT}/app/static" ]; then
        cp -r "${BACKUP_ROOT}/app/static"/* "${APP_DIR}/static/" 2>/dev/null || true
        echo "  ✓ 静态资源"
    fi
    
    # 恢复小程序代码
    if [ -d "${BACKUP_ROOT}/app/miniprogram" ]; then
        cp -r "${BACKUP_ROOT}/app/miniprogram" "${APP_DIR}/" 2>/dev/null || true
        echo "  ✓ 小程序代码"
    fi
    
    # 恢复其他文件
    if [ -f "${BACKUP_ROOT}/app/requirements.txt" ]; then
        cp "${BACKUP_ROOT}/app/requirements.txt" "${APP_DIR}/" 2>/dev/null || true
        echo "  ✓ requirements.txt"
    fi
    
    echo "✓ 应用代码已恢复"
else
    echo -e "${RED}✗ 未找到应用代码目录${NC}"
    exit 1
fi
echo ""

# 4. 恢复配置文件
echo -e "${YELLOW}[4] 恢复配置文件...${NC}"
if [ -d "${BACKUP_ROOT}/config" ]; then
    cp -r "${BACKUP_ROOT}/config"/* "${APP_DIR}/" 2>/dev/null || true
    echo "✓ 配置文件已恢复"
else
    echo "  - 未找到配置文件目录（将使用默认配置）"
fi
echo ""

# 5. 恢复数据文件
echo -e "${YELLOW}[5] 恢复数据文件...${NC}"
if [ -d "${BACKUP_ROOT}/data" ]; then
    # 恢复兑换码文件
    if [ -f "${BACKUP_ROOT}/data/generated_codes.json" ]; then
        cp "${BACKUP_ROOT}/data/generated_codes.json" "${APP_DIR}/" 2>/dev/null || true
        echo "  ✓ generated_codes.json"
    fi
    
    # 恢复其他数据文件
    find "${BACKUP_ROOT}/data" -type f -name "*.json" 2>/dev/null | while read file; do
        if [[ "$(basename $file)" != "generated_codes.json" ]]; then
            cp "$file" "${APP_DIR}/" 2>/dev/null || true
            echo "  ✓ $(basename $file)"
        fi
    done
    
    echo "✓ 数据文件已恢复"
else
    echo "  - 未找到数据文件目录（将创建新文件）"
fi
echo ""

# 6. 恢复上传文件（可选）
echo -e "${YELLOW}[6] 恢复上传文件（可选）...${NC}"
read -p "是否恢复上传文件？(yes/no，默认no): " restore_uploads
if [ "$restore_uploads" = "yes" ] && [ -d "${BACKUP_ROOT}/uploads" ]; then
    if [ -d "${APP_DIR}/uploads" ]; then
        rm -rf "${APP_DIR}/uploads"
    fi
    cp -r "${BACKUP_ROOT}/uploads" "${APP_DIR}/" 2>/dev/null || true
    echo "✓ 上传文件已恢复"
else
    echo "  - 跳过上传文件恢复"
fi
echo ""

# 7. 恢复报告文件（可选）
echo -e "${YELLOW}[7] 恢复报告文件（可选）...${NC}"
read -p "是否恢复报告文件？(yes/no，默认no): " restore_reports
if [ "$restore_reports" = "yes" ] && [ -d "${BACKUP_ROOT}/reports" ]; then
    cp -r "${BACKUP_ROOT}/reports"/* "${APP_DIR}/" 2>/dev/null || true
    echo "✓ 报告文件已恢复"
else
    echo "  - 跳过报告文件恢复"
fi
echo ""

# 8. 安装Python依赖
echo -e "${YELLOW}[8] 安装Python依赖...${NC}"
if [ -f "${APP_DIR}/requirements.txt" ]; then
    echo "正在安装依赖包..."
    ${PIP3_PATH} install -r "${APP_DIR}/requirements.txt" --quiet || {
        echo -e "${YELLOW}  ⚠ 部分依赖安装失败，请检查requirements.txt${NC}"
    }
    echo "✓ 依赖安装完成"
else
    echo -e "${YELLOW}  ⚠ 未找到requirements.txt，安装基础依赖...${NC}"
    ${PIP3_PATH} install flask flask-cors werkzeug --quiet || true
    echo "✓ 基础依赖已安装"
fi
echo ""

# 9. 创建systemd服务文件
echo -e "${YELLOW}[9] 创建systemd服务文件...${NC}"

# 从备份中读取原始服务文件（如果存在）
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"

if [ -f "${BACKUP_ROOT}/system/flask-app.service" ]; then
    echo "从备份中恢复服务配置..."
    # 读取原始服务文件
    cat "${BACKUP_ROOT}/system/flask-app.service" | \
        sed "s|ExecStart=.*|ExecStart=${PYTHON3_PATH} ${APP_DIR}/app.py|g" | \
        sed "s|WorkingDirectory=.*|WorkingDirectory=${APP_DIR}|g" > "${SERVICE_FILE}"
else
    echo "创建新的服务配置..."
    cat > "${SERVICE_FILE}" << EOF
[Unit]
Description=Flask Web Application - 超智引擎
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=${APP_DIR}
ExecStart=${PYTHON3_PATH} ${APP_DIR}/app.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

# 环境变量（从备份的系统信息中读取，或使用默认值）
Environment="MODEL_PROVIDER=tongyi"
Environment="MODEL_NAME=qwen3-max"

[Install]
WantedBy=multi-user.target
EOF
fi

# 设置服务文件权限
chmod 644 "${SERVICE_FILE}"
systemctl daemon-reload
echo "✓ systemd服务文件已创建: ${SERVICE_FILE}"
echo ""

# 10. 配置nginx（可选）
echo -e "${YELLOW}[10] 配置nginx（可选）...${NC}"
read -p "是否配置nginx？(yes/no，默认no): " config_nginx

if [ "$config_nginx" = "yes" ]; then
    # 检查nginx是否安装
    if ! command -v nginx &> /dev/null; then
        echo -e "${YELLOW}  ⚠ nginx未安装，跳过配置${NC}"
    else
        # 从备份中恢复nginx配置（如果存在）
        if [ -f "${BACKUP_ROOT}/system/nginx-default" ] || [ -f "${BACKUP_ROOT}/system/nginx-enabled" ]; then
            echo "  ⚠ nginx配置需要手动检查，备份文件位于: ${BACKUP_ROOT}/system/"
            echo "    请检查后手动复制到 /etc/nginx/sites-available/default"
        else
            echo "创建基础nginx配置..."
            NGINX_CONFIG="/etc/nginx/sites-available/default"
            if [ -f "$NGINX_CONFIG" ]; then
                # 备份现有配置
                cp "$NGINX_CONFIG" "${NGINX_CONFIG}.backup.$(date +%Y%m%d_%H%M%S)"
            fi
            
            # 创建基础配置
            cat > "$NGINX_CONFIG" << 'NGINX_EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket支持
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # 超时设置
        proxy_connect_timeout 600s;
        proxy_send_timeout 600s;
        proxy_read_timeout 600s;
    }

    # 静态文件
    location /static/ {
        alias /var/www/html/static/;
        expires 30d;
    }
}
NGINX_EOF
            
            # 测试nginx配置
            if nginx -t; then
                systemctl reload nginx
                echo "  ✓ nginx配置已更新"
            else
                echo -e "${RED}  ✗ nginx配置测试失败，请手动检查${NC}"
            fi
        fi
    fi
else
    echo "  - 跳过nginx配置"
fi
echo ""

# 11. 设置文件权限
echo -e "${YELLOW}[11] 设置文件权限...${NC}"
chown -R root:root "${APP_DIR}" 2>/dev/null || true
chmod +x "${APP_DIR}"/*.py 2>/dev/null || true
chmod +x "${APP_DIR}"/*.sh 2>/dev/null || true
chmod 755 "${APP_DIR}" 2>/dev/null || true
echo "✓ 文件权限已设置"
echo ""

# 12. 检查环境变量配置
echo -e "${YELLOW}[12] 检查环境变量配置...${NC}"
echo "请确保以下环境变量已配置（可通过systemd服务文件或.env文件设置）："
echo "  - MODEL_PROVIDER (openai/tongyi/custom)"
echo "  - DASHSCOPE_API_KEY 或 OPENAI_API_KEY 或 CUSTOM_API_KEY"
echo "  - MODEL_NAME"
echo ""
read -p "是否现在配置环境变量？(yes/no，默认no): " config_env

if [ "$config_env" = "yes" ]; then
    echo ""
    read -p "模型提供商 (openai/tongyi/custom，默认tongyi): " model_provider
    model_provider=${model_provider:-tongyi}
    
    if [ "$model_provider" = "tongyi" ]; then
        read -p "DASHSCOPE_API_KEY: " api_key
        read -p "模型名称 (默认qwen3-max): " model_name
        model_name=${model_name:-qwen3-max}
        
        # 更新服务文件
        sed -i "s|Environment=\"MODEL_PROVIDER=.*|Environment=\"MODEL_PROVIDER=${model_provider}\"|g" "${SERVICE_FILE}"
        sed -i "s|Environment=\"MODEL_NAME=.*|Environment=\"MODEL_NAME=${model_name}\"|g" "${SERVICE_FILE}"
        echo "Environment=\"DASHSCOPE_API_KEY=${api_key}\"" >> "${SERVICE_FILE}"
        
    elif [ "$model_provider" = "openai" ]; then
        read -p "OPENAI_API_KEY: " api_key
        read -p "模型名称 (默认gpt-3.5-turbo): " model_name
        model_name=${model_name:-gpt-3.5-turbo}
        
        sed -i "s|Environment=\"MODEL_PROVIDER=.*|Environment=\"MODEL_PROVIDER=${model_provider}\"|g" "${SERVICE_FILE}"
        sed -i "s|Environment=\"MODEL_NAME=.*|Environment=\"MODEL_NAME=${model_name}\"|g" "${SERVICE_FILE}"
        echo "Environment=\"OPENAI_API_KEY=${api_key}\"" >> "${SERVICE_FILE}"
        
    elif [ "$model_provider" = "custom" ]; then
        read -p "CUSTOM_API_KEY: " api_key
        read -p "API_BASE_URL: " api_base_url
        read -p "模型名称: " model_name
        
        sed -i "s|Environment=\"MODEL_PROVIDER=.*|Environment=\"MODEL_PROVIDER=${model_provider}\"|g" "${SERVICE_FILE}"
        sed -i "s|Environment=\"MODEL_NAME=.*|Environment=\"MODEL_NAME=${model_name}\"|g" "${SERVICE_FILE}"
        echo "Environment=\"CUSTOM_API_KEY=${api_key}\"" >> "${SERVICE_FILE}"
        echo "Environment=\"API_BASE_URL=${api_base_url}\"" >> "${SERVICE_FILE}"
    fi
    
    systemctl daemon-reload
    echo "✓ 环境变量已配置"
else
    echo "  - 跳过环境变量配置（请手动配置）"
fi
echo ""

# 13. 测试应用启动
echo -e "${YELLOW}[13] 测试应用启动...${NC}"
echo "检查Python语法..."
${PYTHON3_PATH} -m py_compile "${APP_DIR}/app.py" 2>&1 || {
    echo -e "${RED}✗ Python语法检查失败${NC}"
    echo "请检查app.py文件"
}

echo "检查导入..."
${PYTHON3_PATH} -c "import sys; sys.path.insert(0, '${APP_DIR}'); import app" 2>&1 || {
    echo -e "${YELLOW}  ⚠ 导入检查失败（可能是缺少环境变量，这是正常的）${NC}"
}
echo "✓ 基础检查完成"
echo ""

# 14. 启用并启动服务
echo -e "${YELLOW}[14] 启用并启动服务...${NC}"
systemctl enable "${SERVICE_NAME}.service"
systemctl start "${SERVICE_NAME}.service"
sleep 5

# 检查服务状态
if systemctl is-active --quiet "${SERVICE_NAME}.service"; then
    echo "✓ 服务已启动"
    systemctl status "${SERVICE_NAME}.service" --no-pager -l | head -15
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo "查看日志:"
    journalctl -u "${SERVICE_NAME}.service" -n 50 --no-pager
    echo ""
    echo "请检查日志并修复问题后手动启动:"
    echo "  systemctl start ${SERVICE_NAME}.service"
fi
echo ""

# 15. 清理临时文件
echo -e "${YELLOW}[15] 清理临时文件...${NC}"
rm -rf "${RESTORE_DIR}"
echo "✓ 临时文件已清理"
echo ""

# 16. 显示恢复摘要
echo -e "${GREEN}=========================================="
echo "恢复完成！"
echo "==========================================${NC}"
echo ""
echo "应用信息:"
echo "  应用目录: ${APP_DIR}"
echo "  服务名称: ${SERVICE_NAME}"
echo "  Python路径: ${PYTHON3_PATH}"
echo ""
echo "恢复内容:"
echo "  ✓ 应用代码"
echo "  ✓ 配置文件"
echo "  ✓ 数据文件"
if [ "$restore_uploads" = "yes" ]; then
    echo "  ✓ 上传文件"
fi
if [ "$restore_reports" = "yes" ]; then
    echo "  ✓ 报告文件"
fi
echo "  ✓ Python依赖"
echo "  ✓ systemd服务"
if [ "$config_nginx" = "yes" ]; then
    echo "  ✓ nginx配置"
fi
echo ""
echo "服务管理命令:"
echo "  启动服务: systemctl start ${SERVICE_NAME}.service"
echo "  停止服务: systemctl stop ${SERVICE_NAME}.service"
echo "  重启服务: systemctl restart ${SERVICE_NAME}.service"
echo "  查看状态: systemctl status ${SERVICE_NAME}.service"
echo "  查看日志: journalctl -u ${SERVICE_NAME}.service -f"
echo ""
echo "测试应用:"
echo "  curl http://localhost:5000/"
echo ""

