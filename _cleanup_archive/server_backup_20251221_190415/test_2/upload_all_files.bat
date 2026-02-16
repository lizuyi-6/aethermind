@echo off
chcp 65001 >nul
echo ========================================
echo 上传所有文件到服务器
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
if not exist "app.py" (
    echo [错误] 找不到 app.py 文件
    echo 请确保在项目根目录运行此脚本
    pause
    exit /b 1
)

echo [1/7] 上传核心 Python 文件...
scp -i "%KEY_FILE%" -P %PORT% app.py %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 app.py 失败
    pause
    exit /b 1
)

scp -i "%KEY_FILE%" -P %PORT% agent.py %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 agent.py 失败
    pause
    exit /b 1
)

scp -i "%KEY_FILE%" -P %PORT% config.py %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 config.py 失败
    pause
    exit /b 1
)

scp -i "%KEY_FILE%" -P %PORT% file_processor.py %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 file_processor.py 失败
    pause
    exit /b 1
)

echo [2/7] 上传 requirements.txt...
scp -i "%KEY_FILE%" -P %PORT% requirements.txt %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 requirements.txt 失败
    pause
    exit /b 1
)

echo [3/7] 上传 templates 目录...
scp -i "%KEY_FILE%" -P %PORT% -r templates %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 templates 目录失败
    pause
    exit /b 1
)

echo [4/7] 上传 static 目录...
scp -i "%KEY_FILE%" -P %PORT% -r static %SERVER%:%REMOTE_DIR%/
if errorlevel 1 (
    echo [错误] 上传 static 目录失败
    pause
    exit /b 1
)

echo [5/7] 上传配置文件...
if exist "system_prompt.txt" (
    scp -i "%KEY_FILE%" -P %PORT% system_prompt.txt %SERVER%:%REMOTE_DIR%/
)
if exist "system_prompt_enhanced.txt" (
    scp -i "%KEY_FILE%" -P %PORT% system_prompt_enhanced.txt %SERVER%:%REMOTE_DIR%/
)

echo [6/7] 在服务器上创建 uploads 目录...
ssh -i "%KEY_FILE%" -p %PORT% %SERVER% "mkdir -p %REMOTE_DIR%/uploads && chmod 755 %REMOTE_DIR%/uploads"

echo [7/7] 设置文件权限...
ssh -i "%KEY_FILE%" -p %PORT% %SERVER% "cd %REMOTE_DIR% && chmod 644 *.py *.txt 2>/dev/null; chmod -R 755 templates/ static/ 2>/dev/null"

echo.
echo ========================================
echo 上传完成！
echo ========================================
echo.
echo 文件已上传到：%SERVER%:%REMOTE_DIR%/
echo.
echo 下一步操作（在服务器上执行）：
echo   1. cd /var/www/html
echo   2. python3 -m pip install -r requirements.txt
echo   3. python3 app.py
echo.
pause

