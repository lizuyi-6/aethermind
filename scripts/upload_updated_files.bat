@echo off
chcp 65001 >nul
echo 正在上传更新后的文件到服务器...
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

echo [1/3] 上传 system_prompt.txt...
scp -i "%KEY_FILE%" -P %PORT% system_prompt.txt %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 system_prompt.txt 失败
    pause
    exit /b 1
)

echo [2/3] 上传 agent.py...
scp -i "%KEY_FILE%" -P %PORT% agent.py %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 agent.py 失败
    pause
    exit /b 1
)

echo [3/3] 上传 README.md...
scp -i "%KEY_FILE%" -P %PORT% README.md %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [警告] 上传 README.md 失败（可选文件）
)

echo.
echo ========================================
echo 上传完成！
echo ========================================
echo.
echo 已上传以下文件：
echo   - system_prompt.txt
echo   - agent.py
echo   - README.md
echo.
echo 文件已上传到：%SERVER%:%REMOTE_DIR%/
echo.
echo 如果服务正在运行，需要重启服务使更改生效：
echo   sudo systemctl restart flask-app.service
echo.
pause

