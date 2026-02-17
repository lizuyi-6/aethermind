#!/bin/bash
# PDF功能修复脚本 - Ubuntu服务器
# 此脚本将安装PDF转换所需的系统依赖

echo "========================================="
echo "PDF功能修复脚本"
echo "========================================="

# 检查是否为root用户
if [ "$EUID" -ne 0 ]; then
    echo "请使用sudo权限运行此脚本："
    echo "sudo bash fix_pdf_issues.sh"
    exit 1
fi

echo ""
echo "[1/5] 更新包列表..."
apt-get update

echo ""
echo "[2/5] 安装WeasyPrint系统依赖..."
# WeasyPrint需要以下系统库
apt-get install -y \
    python3-pip \
    python3-cffi \
    python3-brotli \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    build-essential \
    python3-dev \
    libxml2-dev \
    libxslt1-dev \
    zlib1g-dev

echo ""
echo "[3/5] 安装中文字体支持..."
# 安装中文字体，确保PDF中文显示正常
apt-get install -y \
    fonts-noto-cjk \
    fonts-wqy-microhei \
    fonts-wqy-zenhei \
    ttf-wqy-microhei \
    ttf-wqy-zenhei

echo ""
echo "[4/5] 创建并设置reports目录权限..."
# 创建reports目录（如果不存在）
mkdir -p /home/ubuntu/test_2/reports || mkdir -p reports

# 设置目录权限
if [ -d "/home/ubuntu/test_2/reports" ]; then
    chmod 755 /home/ubuntu/test_2/reports
    chown -R ubuntu:ubuntu /home/ubuntu/test_2/reports
    echo "✓ reports目录权限已设置（/home/ubuntu/test_2/reports）"
elif [ -d "reports" ]; then
    chmod 755 reports
    echo "✓ reports目录权限已设置（./reports）"
fi

echo ""
echo "[5/5] 重新安装Python PDF相关库..."
# 切换到项目目录（如果可能）
if [ -d "/home/ubuntu/test_2" ]; then
    cd /home/ubuntu/test_2
fi

# 使用pip安装（或重新安装）Python包
pip3 install --upgrade pip
pip3 install --upgrade weasyprint markdown reportlab PyPDF2

echo ""
echo "========================================="
echo "✅ PDF依赖安装完成！"
echo "========================================="
echo ""
echo "接下来的步骤："
echo "1. 重启Flask应用"
echo "   sudo systemctl restart flask-app"
echo ""
echo "2. 查看应用日志以确认PDF功能是否正常"
echo "   journalctl -u flask-app -f"
echo ""
echo "3. 测试PDF生成功能"
echo ""
echo "如果仍有问题，请检查："
echo "- 应用日志中的错误信息"
echo "- reports目录是否可写"
echo "- Python包是否正确安装"
echo ""
