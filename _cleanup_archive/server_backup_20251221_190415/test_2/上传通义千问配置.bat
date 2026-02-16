@echo off
chcp 65001 >nul
echo ==========================================
echo   上传通义千问配置到服务器
echo ==========================================
echo.

set PEM_FILE=C:\Users\Abraham\Downloads\KeyPair-6418.pem
set SERVER=root@60.10.230.156
set PORT=2950

echo 正在上传配置文件到服务器...
echo.

REM 上传配置文件
scp -i "%PEM_FILE%" -P %PORT% config.py %SERVER%:/var/www/html/
scp -i "%PEM_FILE%" -P %PORT% flask-app.service %SERVER%:/var/www/html/
scp -i "%PEM_FILE%" -P %PORT% "切换到通义千问_配置.sh" %SERVER%:/var/www/html/

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ 上传成功！
    echo.
    echo 下一步操作：
    echo 1. SSH 连接到服务器: ssh -i "%PEM_FILE%" -p %PORT% %SERVER%
    echo 2. 执行: chmod +x /var/www/html/切换到通义千问_配置.sh
    echo 3. 执行: /var/www/html/切换到通义千问_配置.sh
    echo.
    echo 或者直接执行配置脚本（会自动重启服务）：
    echo   cd /var/www/html
    echo   chmod +x 切换到通义千问_配置.sh
    echo   ./切换到通义千问_配置.sh
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

