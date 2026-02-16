#!/bin/bash

# 上传 Index 文件到服务器脚本
# 使用您的 SSH 配置

echo "========================================"
echo "上传 Index 文件到服务器"
echo "========================================"
echo ""

# 配置信息
KEY_FILE="~/.ssh/KeyPair-6418.pem"
PORT="2950"
SERVER="root@60.10.230.156"
REMOTE_DIR="/var/www/html"

# 检查文件是否存在
if [ ! -f "index_static.html" ]; then
    echo "[错误] 找不到 index_static.html 文件"
    echo "请确保在项目根目录运行此脚本"
    exit 1
fi

if [ ! -d "static" ]; then
    echo "[错误] 找不到 static 目录"
    echo "请确保在项目根目录运行此脚本"
    exit 1
fi

# 上传 index.html
echo "[1/3] 上传 index.html..."
scp -i $KEY_FILE -P $PORT index_static.html $SERVER:$REMOTE_DIR/index.html
if [ $? -ne 0 ]; then
    echo "[错误] 上传 index.html 失败"
    echo "请检查："
    echo "  1. SSH密钥文件路径是否正确"
    echo "  2. 服务器地址和端口是否正确"
    echo "  3. 网络连接是否正常"
    exit 1
fi

# 上传 static 目录
echo "[2/3] 上传 static 目录..."
scp -i $KEY_FILE -P $PORT -r static $SERVER:$REMOTE_DIR/
if [ $? -ne 0 ]; then
    echo "[错误] 上传 static 目录失败"
    exit 1
fi

# 设置文件权限
echo "[3/3] 设置文件权限..."
ssh -i $KEY_FILE -p $PORT $SERVER "chmod 644 $REMOTE_DIR/index.html && chmod -R 755 $REMOTE_DIR/static/"

echo ""
echo "========================================"
echo "上传完成！"
echo "========================================"
echo ""
echo "文件已上传到：$SERVER:$REMOTE_DIR/"
echo ""
echo "请访问您的域名查看效果"
echo ""

