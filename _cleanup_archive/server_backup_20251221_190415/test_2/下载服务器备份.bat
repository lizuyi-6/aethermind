@echo off
chcp 65001 >nul
echo ==========================================
echo 下载服务器备份脚本
echo ==========================================
echo.

REM 配置变量
set "SSH_KEY=C:\Users\Abraham\Downloads\KeyPair-6418.pem"
set "SSH_PORT=2950"
set "SERVER_USER=root"
set "SERVER_HOST=60.10.230.156"
set "BACKUP_DIR=/root/backups"
set "LOCAL_DOWNLOAD_DIR=%~dp0服务器备份"

echo [1] 创建本地下载目录...
if not exist "%LOCAL_DOWNLOAD_DIR%" mkdir "%LOCAL_DOWNLOAD_DIR%"
echo ✓ 目录创建完成
echo.

echo [2] 连接到服务器，查找最新备份...
echo.

REM 获取最新的备份文件名
for /f "tokens=*" %%i in ('ssh -i "%SSH_KEY%" -p %SSH_PORT% %SERVER_USER%@%SERVER_HOST% "ls -t %BACKUP_DIR%/backup_*.tar.gz 2^>nul | head -1"') do set LATEST_BACKUP=%%i

if "%LATEST_BACKUP%"=="" (
    echo ✗ 未找到备份文件
    echo.
    echo 请先在服务器上运行备份脚本：
    echo   ssh -i "%SSH_KEY%" -p %SSH_PORT% %SERVER_USER%@%SERVER_HOST%
    echo   cd /var/www/html
    echo   ./服务器备份脚本.sh
    pause
    exit /b 1
)

echo 找到最新备份: %LATEST_BACKUP%
echo.

REM 提取文件名
for %%F in ("%LATEST_BACKUP%") do set BACKUP_FILENAME=%%~nxF

echo [3] 下载备份文件...
echo 目标文件: %BACKUP_FILENAME%
echo 保存位置: %LOCAL_DOWNLOAD_DIR%\%BACKUP_FILENAME%
echo.

scp -i "%SSH_KEY%" -P %SSH_PORT% %SERVER_USER%@%SERVER_HOST%:%LATEST_BACKUP% "%LOCAL_DOWNLOAD_DIR%\%BACKUP_FILENAME%"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==========================================
    echo 下载完成！
    echo ==========================================
    echo.
    echo 备份文件已保存到:
    echo   %LOCAL_DOWNLOAD_DIR%\%BACKUP_FILENAME%
    echo.
    
    REM 显示文件大小
    for %%A in ("%LOCAL_DOWNLOAD_DIR%\%BACKUP_FILENAME%") do (
        set SIZE=%%~zA
        set /a SIZE_MB=!SIZE!/1024/1024
        echo 文件大小: !SIZE_MB! MB
    )
    echo.
    
    echo 解压备份文件:
    echo   tar -xzf "%LOCAL_DOWNLOAD_DIR%\%BACKUP_FILENAME%"
    echo.
) else (
    echo.
    echo ✗ 下载失败
    echo 请检查网络连接和SSH密钥
    echo.
)

pause

