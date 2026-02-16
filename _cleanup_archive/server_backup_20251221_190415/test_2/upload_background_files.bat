@echo off
chcp 65001 >nul
echo ========================================
echo 上传后台运行相关文件到服务器
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
if not exist "flask-app.service" (
    echo [错误] 找不到 flask-app.service 文件
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

echo [1/7] 上传 systemd 服务文件...
scp -i "%KEY_FILE%" -P %PORT% flask-app.service %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 flask-app.service 失败
    pause
    exit /b 1
)

echo [2/7] 上传服务安装脚本...
scp -i "%KEY_FILE%" -P %PORT% install_service.sh %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 install_service.sh 失败
    pause
    exit /b 1
)

echo [3/7] 上传服务检查脚本...
scp -i "%KEY_FILE%" -P %PORT% check_service.sh %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 check_service.sh 失败
    pause
    exit /b 1
)

echo [4/7] 上传 screen 启动脚本...
scp -i "%KEY_FILE%" -P %PORT% start_flask_screen.sh %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 start_flask_screen.sh 失败
    pause
    exit /b 1
)

echo [5/7] 上传 nohup 启动脚本...
scp -i "%KEY_FILE%" -P %PORT% start_flask_nohup.sh %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 start_flask_nohup.sh 失败
    pause
    exit /b 1
)

echo [6/7] 上传使用指南...
scp -i "%KEY_FILE%" -P %PORT% "服务器后台运行指南.md" %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [警告] 上传指南文件失败（可选文件）
)

scp -i "%KEY_FILE%" -P %PORT% "服务器后台运行快速参考.md" %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [警告] 上传快速参考文件失败（可选文件）
)

echo [7/7] 设置脚本执行权限...
ssh -i "%KEY_FILE%" -p %PORT% %SERVER% "cd %REMOTE_DIR% && chmod +x install_service.sh check_service.sh start_flask_screen.sh start_flask_nohup.sh 2>/dev/null"

echo.
echo ========================================
echo 上传完成！
echo ========================================
echo.
echo 文件已上传到：%SERVER%:%REMOTE_DIR%/
echo.
echo 下一步操作（在服务器上执行）：
echo   1. cd /var/www/html
echo   2. sudo ./install_service.sh
echo   3. ./check_service.sh
echo.
echo 或使用其他方式：
echo   - nohup方式: ./start_flask_nohup.sh
echo   - screen方式: ./start_flask_screen.sh
echo.
pause

