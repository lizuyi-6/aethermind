@echo off
chcp 65001 >nul
echo ========================================
echo 启动智能体Web服务
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python
    pause
    exit /b 1
)

echo [信息] 检测到Python环境
python --version

echo.
echo [信息] 检查依赖包...
python -c "import flask" >nul 2>&1
if errorlevel 1 (
    echo [信息] 正在安装Flask依赖...
    pip install flask flask-cors
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

echo.
echo [信息] 启动Web服务...
echo [信息] 访问地址: http://localhost:5000
echo [信息] 按 Ctrl+C 停止服务
echo.
echo ========================================
echo.

python app.py

pause

