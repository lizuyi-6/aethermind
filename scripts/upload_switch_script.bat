@echo off
chcp 65001 >nul
echo ==========================================
echo   上传切换到通义千问脚本到服务器
echo ==========================================
echo.

set PEM_FILE=C:\Users\Abraham\Downloads\KeyPair-6418.pem
set SERVER=root@60.10.230.156
set PORT=2950

echo 正在上传 switch_to_tongyi.sh 到服务器...
scp -i "%PEM_FILE%" -P %PORT% switch_to_tongyi.sh %SERVER%:/var/www/html/

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 上传成功！
    echo.
    echo 下一步操作：
    echo 1. SSH 连接到服务器
    echo 2. 执行: chmod +x /var/www/html/switch_to_tongyi.sh
    echo 3. 执行: /var/www/html/switch_to_tongyi.sh
    echo.
) else (
    echo.
    echo ❌ 上传失败，请检查：
    echo - SSH 密钥文件路径是否正确
    echo - 服务器地址和端口是否正确
    echo - 网络连接是否正常
    echo.
)

pause

