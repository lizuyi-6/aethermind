#!/bin/bash
# 安装系统级依赖（用于编译 Python 包）

set -e

echo "=========================================="
echo "  安装系统级依赖"
echo "=========================================="
echo ""

# 检测系统类型
if [ -f /etc/redhat-release ]; then
    # CentOS/RHEL
    echo "检测到 CentOS/RHEL 系统"
    echo "安装开发工具和库..."
    yum groupinstall -y "Development Tools" || true
    yum install -y python3-devel libxml2-devel libxslt-devel libffi-devel openssl-devel
    echo "✅ 系统依赖安装完成"
elif [ -f /etc/debian_version ]; then
    # Debian/Ubuntu
    echo "检测到 Debian/Ubuntu 系统"
    echo "更新包列表..."
    apt-get update
    echo "安装开发工具和库..."
    apt-get install -y build-essential python3-dev libxml2-dev libxslt1-dev libffi-dev libssl-dev
    echo "✅ 系统依赖安装完成"
else
    echo "⚠️  无法自动检测系统类型，请手动安装以下依赖："
    echo "   - libxml2-dev / libxml2-devel"
    echo "   - libxslt1-dev / libxslt-devel"
    echo "   - python3-dev / python3-devel"
    echo "   - build-essential / Development Tools"
    exit 1
fi

echo ""
echo "=========================================="
echo "  系统依赖安装完成"
echo "=========================================="

