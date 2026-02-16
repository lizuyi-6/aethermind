#!/bin/bash

# ==========================================
# 服务器完整备份脚本
# ==========================================
# 功能：备份Flask应用的所有重要文件和配置
# 使用方法：./服务器备份脚本.sh
# ==========================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 配置变量
BACKUP_BASE_DIR="/root/backups"
APP_DIR="/var/www/html"
BACKUP_DATE=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_BASE_DIR}/backup_${BACKUP_DATE}"
BACKUP_ARCHIVE="${BACKUP_BASE_DIR}/backup_${BACKUP_DATE}.tar.gz"

echo -e "${GREEN}=========================================="
echo "服务器完整备份脚本"
echo "==========================================${NC}"
echo ""
echo "备份时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "备份目录: ${BACKUP_DIR}"
echo "压缩文件: ${BACKUP_ARCHIVE}"
echo ""

# 1. 创建备份目录
echo -e "${YELLOW}[1] 创建备份目录...${NC}"
mkdir -p "${BACKUP_DIR}"
mkdir -p "${BACKUP_DIR}/app"           # 应用代码
mkdir -p "${BACKUP_DIR}/config"        # 配置文件
mkdir -p "${BACKUP_DIR}/data"           # 数据文件
mkdir -p "${BACKUP_DIR}/system"        # 系统配置
mkdir -p "${BACKUP_DIR}/uploads"        # 上传文件
mkdir -p "${BACKUP_DIR}/reports"       # 生成的报告
echo "✓ 备份目录创建完成"
echo ""

# 2. 备份应用代码
echo -e "${YELLOW}[2] 备份应用代码...${NC}"
cd "${APP_DIR}"

# Python文件
cp -r *.py "${BACKUP_DIR}/app/" 2>/dev/null || true
echo "  ✓ Python文件"

# 模板文件
if [ -d "templates" ]; then
    cp -r templates "${BACKUP_DIR}/app/" 2>/dev/null || true
    echo "  ✓ 模板文件"
fi

# 静态资源
if [ -d "static" ]; then
    cp -r static "${BACKUP_DIR}/app/" 2>/dev/null || true
    echo "  ✓ 静态资源"
fi

# 小程序代码
if [ -d "miniprogram" ]; then
    cp -r miniprogram "${BACKUP_DIR}/app/" 2>/dev/null || true
    echo "  ✓ 小程序代码"
fi

# 其他重要文件
cp requirements.txt "${BACKUP_DIR}/app/" 2>/dev/null || true
cp README.md "${BACKUP_DIR}/app/" 2>/dev/null || true
echo "✓ 应用代码备份完成"
echo ""

# 3. 备份配置文件
echo -e "${YELLOW}[3] 备份配置文件...${NC}"

# 应用配置
if [ -f "${APP_DIR}/config.py" ]; then
    cp "${APP_DIR}/config.py" "${BACKUP_DIR}/config/" 2>/dev/null || true
    echo "  ✓ config.py"
fi

# 系统提示词
if [ -f "${APP_DIR}/system_prompt.txt" ]; then
    cp "${APP_DIR}/system_prompt.txt" "${BACKUP_DIR}/config/" 2>/dev/null || true
    echo "  ✓ system_prompt.txt"
fi

if [ -f "${APP_DIR}/system_prompt_enhanced.txt" ]; then
    cp "${APP_DIR}/system_prompt_enhanced.txt" "${BACKUP_DIR}/config/" 2>/dev/null || true
    echo "  ✓ system_prompt_enhanced.txt"
fi

# 环境变量文件（如果存在）
if [ -f "${APP_DIR}/.env" ]; then
    cp "${APP_DIR}/.env" "${BACKUP_DIR}/config/" 2>/dev/null || true
    echo "  ✓ .env"
fi

# 模板文件（如果存在）
if [ -f "${APP_DIR}/可行性研究报告模板.md" ]; then
    cp "${APP_DIR}/可行性研究报告模板.md" "${BACKUP_DIR}/config/" 2>/dev/null || true
    echo "  ✓ 可行性研究报告模板.md"
fi

echo "✓ 配置文件备份完成"
echo ""

# 4. 备份数据文件
echo -e "${YELLOW}[4] 备份数据文件...${NC}"

# 兑换码文件（可能在多个位置）
if [ -f "${APP_DIR}/generated_codes.json" ]; then
    cp "${APP_DIR}/generated_codes.json" "${BACKUP_DIR}/data/" 2>/dev/null || true
    echo "  ✓ generated_codes.json (应用目录)"
fi

# 查找其他可能位置的兑换码文件
find "${APP_DIR}" -name "generated_codes.json" -type f 2>/dev/null | while read file; do
    if [ "$file" != "${APP_DIR}/generated_codes.json" ]; then
        cp "$file" "${BACKUP_DIR}/data/generated_codes_$(basename $(dirname $file)).json" 2>/dev/null || true
        echo "  ✓ generated_codes.json ($(dirname $file))"
    fi
done

# 用户数据（如果有）
if [ -d "${APP_DIR}/data" ]; then
    cp -r "${APP_DIR}/data" "${BACKUP_DIR}/data/user_data" 2>/dev/null || true
    echo "  ✓ 用户数据目录"
fi

echo "✓ 数据文件备份完成"
echo ""

# 5. 备份系统配置
echo -e "${YELLOW}[5] 备份系统配置...${NC}"

# systemd服务文件
if [ -f "/etc/systemd/system/flask-app.service" ]; then
    cp "/etc/systemd/system/flask-app.service" "${BACKUP_DIR}/system/" 2>/dev/null || true
    echo "  ✓ flask-app.service"
fi

# nginx配置
if [ -f "/etc/nginx/sites-available/default" ]; then
    cp "/etc/nginx/sites-available/default" "${BACKUP_DIR}/system/nginx-default" 2>/dev/null || true
    echo "  ✓ nginx default配置"
fi

if [ -f "/etc/nginx/sites-enabled/default" ]; then
    cp "/etc/nginx/sites-enabled/default" "${BACKUP_DIR}/system/nginx-enabled" 2>/dev/null || true
    echo "  ✓ nginx enabled配置"
fi

# nginx主配置
if [ -f "/etc/nginx/nginx.conf" ]; then
    cp "/etc/nginx/nginx.conf" "${BACKUP_DIR}/system/nginx.conf" 2>/dev/null || true
    echo "  ✓ nginx.conf"
fi

# Python路径信息
which python3 > "${BACKUP_DIR}/system/python3_path.txt" 2>/dev/null || true
python3 --version > "${BACKUP_DIR}/system/python3_version.txt" 2>/dev/null || true
echo "  ✓ Python环境信息"

# 系统信息
uname -a > "${BACKUP_DIR}/system/system_info.txt" 2>/dev/null || true
echo "  ✓ 系统信息"

echo "✓ 系统配置备份完成"
echo ""

# 6. 备份上传文件
echo -e "${YELLOW}[6] 备份上传文件...${NC}"
if [ -d "${APP_DIR}/uploads" ]; then
    # 只备份非空目录
    if [ "$(ls -A ${APP_DIR}/uploads 2>/dev/null)" ]; then
        cp -r "${APP_DIR}/uploads" "${BACKUP_DIR}/uploads" 2>/dev/null || true
        UPLOAD_COUNT=$(find "${APP_DIR}/uploads" -type f 2>/dev/null | wc -l)
        echo "  ✓ 上传文件 (${UPLOAD_COUNT} 个文件)"
    else
        echo "  - 上传目录为空，跳过"
    fi
else
    echo "  - 上传目录不存在，跳过"
fi
echo ""

# 7. 备份生成的报告
echo -e "${YELLOW}[7] 备份生成的报告...${NC}"
REPORT_COUNT=0
if ls "${APP_DIR}"/*.md 1> /dev/null 2>&1; then
    for report in "${APP_DIR}"/*.md; do
        # 排除README等文档文件
        if [[ ! "$(basename $report)" =~ ^(README|部署|配置|指南|说明|清单) ]]; then
            cp "$report" "${BACKUP_DIR}/reports/" 2>/dev/null || true
            REPORT_COUNT=$((REPORT_COUNT + 1))
        fi
    done
    echo "  ✓ 报告文件 (${REPORT_COUNT} 个文件)"
else
    echo "  - 未找到报告文件"
fi
echo ""

# 8. 创建备份清单
echo -e "${YELLOW}[8] 创建备份清单...${NC}"
cat > "${BACKUP_DIR}/backup_info.txt" << EOF
========================================
备份信息
========================================
备份时间: $(date '+%Y-%m-%d %H:%M:%S')
服务器: $(hostname)
IP地址: $(hostname -I | awk '{print $1}')
备份目录: ${BACKUP_DIR}

文件统计:
EOF

echo "应用代码:" >> "${BACKUP_DIR}/backup_info.txt"
find "${BACKUP_DIR}/app" -type f 2>/dev/null | wc -l | xargs echo "  - 文件数:" >> "${BACKUP_DIR}/backup_info.txt"

echo "配置文件:" >> "${BACKUP_DIR}/backup_info.txt"
find "${BACKUP_DIR}/config" -type f 2>/dev/null | wc -l | xargs echo "  - 文件数:" >> "${BACKUP_DIR}/backup_info.txt"

echo "数据文件:" >> "${BACKUP_DIR}/backup_info.txt"
find "${BACKUP_DIR}/data" -type f 2>/dev/null | wc -l | xargs echo "  - 文件数:" >> "${BACKUP_DIR}/backup_info.txt"

echo "系统配置:" >> "${BACKUP_DIR}/backup_info.txt"
find "${BACKUP_DIR}/system" -type f 2>/dev/null | wc -l | xargs echo "  - 文件数:" >> "${BACKUP_DIR}/backup_info.txt"

echo "上传文件:" >> "${BACKUP_DIR}/backup_info.txt"
find "${BACKUP_DIR}/uploads" -type f 2>/dev/null | wc -l | xargs echo "  - 文件数:" >> "${BACKUP_DIR}/backup_info.txt"

echo "报告文件:" >> "${BACKUP_DIR}/backup_info.txt"
find "${BACKUP_DIR}/reports" -type f 2>/dev/null | wc -l | xargs echo "  - 文件数:" >> "${BACKUP_DIR}/backup_info.txt"

echo "✓ 备份清单创建完成"
echo ""

# 9. 压缩备份
echo -e "${YELLOW}[9] 压缩备份文件...${NC}"
cd "${BACKUP_BASE_DIR}"
tar -czf "${BACKUP_ARCHIVE}" "backup_${BACKUP_DATE}" 2>/dev/null || {
    echo -e "${RED}✗ 压缩失败，但备份文件已保存在: ${BACKUP_DIR}${NC}"
    exit 1
}

# 计算文件大小
ARCHIVE_SIZE=$(du -h "${BACKUP_ARCHIVE}" | cut -f1)
echo "✓ 压缩完成: ${BACKUP_ARCHIVE}"
echo "  文件大小: ${ARCHIVE_SIZE}"
echo ""

# 10. 清理旧备份（保留最近5个）
echo -e "${YELLOW}[10] 清理旧备份（保留最近5个）...${NC}"
cd "${BACKUP_BASE_DIR}"
BACKUP_COUNT=$(ls -1 backup_*.tar.gz 2>/dev/null | wc -l)
if [ "$BACKUP_COUNT" -gt 5 ]; then
    ls -1t backup_*.tar.gz 2>/dev/null | tail -n +6 | while read old_backup; do
        rm -f "$old_backup"
        echo "  删除旧备份: $old_backup"
    done
    echo "✓ 已清理旧备份"
else
    echo "  当前备份数量: ${BACKUP_COUNT}，无需清理"
fi
echo ""

# 11. 显示备份摘要
echo -e "${GREEN}=========================================="
echo "备份完成！"
echo "==========================================${NC}"
echo ""
echo "备份位置:"
echo "  - 压缩文件: ${BACKUP_ARCHIVE}"
echo "  - 备份目录: ${BACKUP_DIR}"
echo "  - 文件大小: ${ARCHIVE_SIZE}"
echo ""
echo "备份内容:"
cat "${BACKUP_DIR}/backup_info.txt" | tail -n +10
echo ""
echo "下载备份到本地:"
echo "  scp -i \"你的密钥.pem\" -P 2950 root@60.10.230.156:${BACKUP_ARCHIVE} ./"
echo ""
echo "查看备份内容:"
echo "  tar -tzf ${BACKUP_ARCHIVE} | head -20"
echo ""

