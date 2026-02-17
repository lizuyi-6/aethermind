@echo off
chcp 65001 >nul
echo ========================================
echo Flask应用后台服务部署脚本
echo ========================================
echo.

echo [1/3] 正在上传systemd服务文件...
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 flask-app.service root@60.10.230.156:/etc/systemd/system/
if %errorlevel% neq 0 (
    echo ❌ 上传失败！
    pause
    exit /b 1
)
echo ✅ 上传成功！

echo.
echo [2/3] 正在上传nohup启动脚本...
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 start_flask_nohup.sh root@60.10.230.156:/var/www/html/
if %errorlevel% neq 0 (
    echo ⚠️  nohup脚本上传失败（可选）
) else (
    echo ✅ nohup脚本上传成功！
)

echo.
echo [3/3] 正在上传screen启动脚本...
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 start_flask_screen.sh root@60.10.230.156:/var/www/html/
if %errorlevel% neq 0 (
    echo ⚠️  screen脚本上传失败（可选）
) else (
    echo ✅ screen脚本上传成功！
)

echo.
echo ========================================
echo 部署完成！
echo ========================================
echo.
echo 请在服务器上执行以下命令来启动服务：
echo.
echo 【方法一：systemd（推荐）】
echo   systemctl daemon-reload
echo   systemctl enable flask-app.service
echo   systemctl start flask-app.service
echo   systemctl status flask-app.service
echo.
echo 【方法二：nohup（简单）】
echo   cd /var/www/html
echo   chmod +x start_flask_nohup.sh
echo   ./start_flask_nohup.sh
echo.
echo 【方法三：screen（可重连）】
echo   cd /var/www/html
echo   chmod +x start_flask_screen.sh
echo   ./start_flask_screen.sh
echo.
pause




















