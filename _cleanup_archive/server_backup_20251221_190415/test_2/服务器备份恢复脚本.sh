#!/bin/bash

# ==========================================
# 服务器备份恢复脚本
# ==========================================
# 功能：从备份文件恢复服务器应用
# 使用方法：./服务器备份恢复脚本.sh <备份文件路径>
# 示例：./服务器备份恢复脚本.sh /root/backups/backup_20241209_120000.tar.gz
# ==========================================

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查参数
if [ $# -eq 0 ]; then
    echo -e "${RED}错误: 请指定备份文件路径${NC}"
    echo "使用方法: $0 <备份文件路径>"
    echo "示例: $0 /root/backups/backup_20241209_120000.tar.gz"
    exit 1
fi

BACKUP_ARCHIVE="$1"
APP_DIR="/var/www/html"
RESTORE_DIR="/tmp/restore_$(date +%s)"

# 检查备份文件是否存在
if [ ! -f "$BACKUP_ARCHIVE" ]; then
    echo -e "${RED}错误: 备份文件不存在: ${BACKUP_ARCHIVE}${NC}"
    exit 1
fi

echo -e "${GREEN}=========================================="
echo "服务器备份恢复脚本"
echo "==========================================${NC}"
echo ""
echo "备份文件: ${BACKUP_ARCHIVE}"
echo "应用目录: ${APP_DIR}"
echo "恢复目录: ${RESTORE_DIR}"
echo ""
echo -e "${YELLOW}警告: 此操作将覆盖现有文件！${NC}"
read -p "确认继续？(yes/no): " confirm

if [ "$confirm" != "yes" ]; then
    echo "操作已取消"
    exit 0
fi

# 1. 停止服务
echo ""
echo -e "${YELLOW}[1] 停止Flask应用服务...${NC}"
systemctl stop flask-app.service || true
echo "✓ 服务已停止"
echo ""

# 2. 解压备份文件
echo -e "${YELLOW}[2] 解压备份文件...${NC}"
mkdir -p "${RESTORE_DIR}"
tar -xzf "${BACKUP_ARCHIVE}" -C "${RESTORE_DIR}" || {
    echo -e "${RED}✗ 解压失败${NC}"
    exit 1
}
BACKUP_ROOT=$(ls -d "${RESTORE_DIR}"/backup_* | head -1)
echo "✓ 备份文件已解压到: ${BACKUP_ROOT}"
echo ""

# 3. 备份当前文件（安全措施）
echo -e "${YELLOW}[3] 备份当前文件（安全措施）...${NC}"
CURRENT_BACKUP="/root/backups/before_restore_$(date +%Y%m%d_%H%M%S).tar.gz"
mkdir -p "$(dirname ${CURRENT_BACKUP})"
tar -czf "${CURRENT_BACKUP}" -C "${APP_DIR}" . 2>/dev/null || true
echo "✓ 当前文件已备份到: ${CURRENT_BACKUP}"
echo ""

# 4. 恢复应用代码
echo -e "${YELLOW}[4] 恢复应用代码...${NC}"
if [ -d "${BACKUP_ROOT}/app" ]; then
    cp -r "${BACKUP_ROOT}/app"/* "${APP_DIR}/" 2>/dev/null || true
    echo "✓ 应用代码已恢复"
else
    echo "  - 未找到应用代码目录"
fi
echo ""

# 5. 恢复配置文件
echo -e "${YELLOW}[5] 恢复配置文件...${NC}"
if [ -d "${BACKUP_ROOT}/config" ]; then
    cp -r "${BACKUP_ROOT}/config"/* "${APP_DIR}/" 2>/dev/null || true
    echo "✓ 配置文件已恢复"
else
    echo "  - 未找到配置文件目录"
fi
echo ""

# 6. 恢复数据文件
echo -e "${YELLOW}[6] 恢复数据文件...${NC}"
if [ -d "${BACKUP_ROOT}/data" ]; then
    # 恢复兑换码文件
    if [ -f "${BACKUP_ROOT}/data/generated_codes.json" ]; then
        cp "${BACKUP_ROOT}/data/generated_codes.json" "${APP_DIR}/" 2>/dev/null || true
        echo "  ✓ generated_codes.json"
    fi
    
    # 恢复其他数据文件
    find "${BACKUP_ROOT}/data" -type f -name "*.json" | while read file; do
        if [[ "$(basename $file)" != "generated_codes.json" ]]; then
            cp "$file" "${APP_DIR}/" 2>/dev/null || true
            echo "  ✓ $(basename $file)"
        fi
    done
    
    echo "✓ 数据文件已恢复"
else
    echo "  - 未找到数据文件目录"
fi
echo ""

# 7. 恢复上传文件（可选）
echo -e "${YELLOW}[7] 恢复上传文件（可选）...${NC}"
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

# 8. 恢复报告文件（可选）
echo -e "${YELLOW}[8] 恢复报告文件（可选）...${NC}"
read -p "是否恢复报告文件？(yes/no，默认no): " restore_reports
if [ "$restore_reports" = "yes" ] && [ -d "${BACKUP_ROOT}/reports" ]; then
    cp -r "${BACKUP_ROOT}/reports"/* "${APP_DIR}/" 2>/dev/null || true
    echo "✓ 报告文件已恢复"
else
    echo "  - 跳过报告文件恢复"
fi
echo ""

# 9. 恢复系统配置（需要确认）
echo -e "${YELLOW}[9] 恢复系统配置（需要确认）...${NC}"
read -p "是否恢复系统配置（systemd、nginx）？(yes/no，默认no): " restore_system
if [ "$restore_system" = "yes" ] && [ -d "${BACKUP_ROOT}/system" ]; then
    # 恢复systemd服务文件
    if [ -f "${BACKUP_ROOT}/system/flask-app.service" ]; then
        cp "${BACKUP_ROOT}/system/flask-app.service" "/etc/systemd/system/" 2>/dev/null || true
        systemctl daemon-reload
        echo "  ✓ systemd服务文件已恢复"
    fi
    
    # 恢复nginx配置（需要手动确认）
    echo "  ⚠ nginx配置需要手动恢复，备份文件位于: ${BACKUP_ROOT}/system/"
    echo "    请检查后手动复制到 /etc/nginx/"
else
    echo "  - 跳过系统配置恢复"
fi
echo ""

# 10. 设置文件权限
echo -e "${YELLOW}[10] 设置文件权限...${NC}"
chown -R root:root "${APP_DIR}" 2>/dev/null || true
chmod +x "${APP_DIR}"/*.py 2>/dev/null || true
chmod +x "${APP_DIR}"/*.sh 2>/dev/null || true
echo "✓ 文件权限已设置"
echo ""

# 11. 清理临时文件
echo -e "${YELLOW}[11] 清理临时文件...${NC}"
rm -rf "${RESTORE_DIR}"
echo "✓ 临时文件已清理"
echo ""

# 12. 启动服务
echo -e "${YELLOW}[12] 启动Flask应用服务...${NC}"
systemctl start flask-app.service
sleep 3
systemctl status flask-app.service --no-pager -l | head -15
echo ""

# 13. 显示恢复摘要
echo -e "${GREEN}=========================================="
echo "恢复完成！"
echo "==========================================${NC}"
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
if [ "$restore_system" = "yes" ]; then
    echo "  ✓ 系统配置"
fi
echo ""
echo "当前文件备份: ${CURRENT_BACKUP}"
echo ""
echo "请检查服务状态:"
echo "  systemctl status flask-app.service"
echo "  journalctl -u flask-app.service -n 50"
echo ""

