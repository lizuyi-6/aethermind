@echo off
chcp 65001 >nul
echo ==========================================
echo 上传备份到新服务器
echo ==========================================
echo.

REM 配置变量
set "SSH_KEY=C:\Users\Abraham\Downloads\KeyPair-6418.pem"
set "SSH_PORT=2950"
set "SERVER_USER=root"

echo [1] 输入目标服务器信息
echo.
set /p "SERVER_HOST=请输入新服务器IP地址: "
set /p "BACKUP_FILE=请输入备份文件路径（本地）: "

if not exist "%BACKUP_FILE%" (
    echo.
    echo ✗ 备份文件不存在: %BACKUP_FILE%
    pause
    exit /b 1
)

echo.
echo [2] 上传备份文件到新服务器...
echo 目标服务器: %SERVER_HOST%
echo 备份文件: %BACKUP_FILE%
echo.

REM 提取文件名
for %%F in ("%BACKUP_FILE%") do set BACKUP_FILENAME=%%~nxF

REM 上传备份文件
scp -i "%SSH_KEY%" -P %SSH_PORT% "%BACKUP_FILE%" %SERVER_USER%@%SERVER_HOST%:/root/

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✓ 备份文件已上传到: /root/%BACKUP_FILENAME%
    echo.
    echo [3] 上传恢复脚本...
    
    REM 上传恢复脚本
    scp -i "%SSH_KEY%" -P %SSH_PORT% 跨服务器恢复脚本.sh %SERVER_USER%@%SERVER_HOST%:/root/
    
    if %ERRORLEVEL% EQU 0 (
        echo ✓ 恢复脚本已上传
        echo.
        echo ==========================================
        echo 上传完成！
        echo ==========================================
        echo.
        echo 下一步操作:
        echo 1. SSH连接到新服务器:
        echo    ssh -i "%SSH_KEY%" -p %SSH_PORT% %SERVER_USER%@%SERVER_HOST%
        echo.
        echo 2. 运行恢复脚本:
        echo    cd /root
        echo    chmod +x 跨服务器恢复脚本.sh
        echo    ./跨服务器恢复脚本.sh /root/%BACKUP_FILENAME%
        echo.
        echo 或者使用自定义路径:
        echo    ./跨服务器恢复脚本.sh /root/%BACKUP_FILENAME% /var/www/html flask-app
        echo.
    ) else (
        echo.
        echo ✗ 恢复脚本上传失败
        echo 请手动上传: 跨服务器恢复脚本.sh
        echo.
    )
) else (
    echo.
    echo ✗ 备份文件上传失败
    echo 请检查网络连接和SSH密钥
    echo.
)

pause

