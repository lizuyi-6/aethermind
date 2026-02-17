@echo off
chcp 65001 >nul
echo ========================================
echo 上传模板文件到服务器
echo ========================================
echo.

REM 配置信息
set KEY_FILE=C:\Users\Abraham\Downloads\KeyPair-6418.pem
set PORT=2950
set SERVER=root@60.10.230.156
set REMOTE_DIR=/var/www/html

REM 检查密钥文件是否存在
if not exist "%KEY_FILE%" (
    echo [错误] 找不到密钥文件: %KEY_FILE%
    echo 请检查文件路径是否正确
    pause
    exit /b 1
)

REM 检查是否在项目目录
if not exist "templates" (
    echo [错误] 找不到 templates 目录
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

echo [1/2] 上传 templates 目录...
scp -i "%KEY_FILE%" -P %PORT% -r templates %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 templates 目录失败
    pause
    exit /b 1
)

echo [2/2] 设置文件权限...
ssh -i "%KEY_FILE%" -p %PORT% %SERVER% "chmod -R 755 %REMOTE_DIR%/templates/"

echo.
echo ========================================
echo 上传完成！
echo ========================================
echo.
echo 已上传以下文件：
echo   - templates/index.html
echo   - templates/index_new.html
echo   - templates/ 目录下的其他文件
echo.
echo 文件已上传到：%SERVER%:%REMOTE_DIR%/templates/
echo.
echo 如果服务正在运行，需要重启服务使更改生效：
echo   sudo systemctl restart flask-app.service
echo   或者
echo   screen -r flask_app
echo   然后按 Ctrl+C 停止，再运行: python3 app.py
echo.
pause
