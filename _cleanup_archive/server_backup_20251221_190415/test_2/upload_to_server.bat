@echo off
chcp 65001 >nul
echo ========================================
echo 上传项目到超智引擎服务器
echo ========================================
echo.

set SERVER_IP=60.10.230.136
set SERVER_PORT=3910
set SERVER_USER=root
set KEY_FILE=@KeyPair-6e51.pem
set REMOTE_PATH=/root/test_2

echo 服务器信息:
echo IP: %SERVER_IP%
echo 端口: %SERVER_PORT%
echo 用户: %SERVER_USER%
echo 密钥: %KEY_FILE%
echo 目标路径: %REMOTE_PATH%
echo.

REM 检查密钥文件
if not exist "%KEY_FILE%" (
    echo [错误] 找不到密钥文件: %KEY_FILE%
    echo 请确保密钥文件在当前目录
    pause
    exit /b 1
)

echo 开始上传项目...
echo.

REM 使用 scp 上传（需要 OpenSSH 客户端）
scp -P %SERVER_PORT% -i "%KEY_FILE%" -r -o StrictHostKeyChecking=no . %SERVER_USER%@%SERVER_IP%:%REMOTE_PATH%

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================
    echo 上传成功！
    echo ========================================
    echo 项目已上传到服务器: %REMOTE_PATH%
) else (
    echo.
    echo ========================================
    echo 上传失败！
    echo ========================================
    echo 错误代码: %ERRORLEVEL%
    echo.
    echo 提示:
    echo 1. 确保已安装 OpenSSH 客户端
    echo 2. 检查密钥文件路径是否正确
    echo 3. 检查网络连接和服务器状态
)

pause

