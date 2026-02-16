@echo off
chcp 65001 >nul
echo 正在上传后台运行文件到服务器...
echo.

scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 flask-app.service root@60.10.230.156:/var/www/html/
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 install_service.sh root@60.10.230.156:/var/www/html/
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 check_service.sh root@60.10.230.156:/var/www/html/
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 start_flask_screen.sh root@60.10.230.156:/var/www/html/
scp -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -P 2950 start_flask_nohup.sh root@60.10.230.156:/var/www/html/

echo.
echo 设置执行权限...
ssh -i "C:\Users\Abraham\Downloads\KeyPair-6418.pem" -p 2950 root@60.10.230.156 "cd /var/www/html && chmod +x install_service.sh check_service.sh start_flask_screen.sh start_flask_nohup.sh"

echo.
echo 上传完成！
echo 现在可以在服务器上运行: sudo ./install_service.sh
pause

