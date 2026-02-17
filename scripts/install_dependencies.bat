@echo off
chcp 65001 >nul
title 安装依赖包
color 0B

echo ========================================
echo    AetherMind智能体 - 依赖安装脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未检测到Python，请先安装Python 3.7或更高版本
    echo.
    echo 下载地址: https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

echo [✓] Python已安装
python --version
echo.

REM 检查requirements.txt是否存在
if not exist "requirements.txt" (
    echo [错误] 未找到requirements.txt文件
    echo.
    pause
    exit /b 1
)

REM 升级pip
echo [信息] 正在升级pip...
python -m pip install --upgrade pip
echo.

REM 安装依赖
echo [信息] 正在安装依赖包...
echo.
pip install -r requirements.txt

if errorlevel 1 (
    echo.
    echo [错误] 依赖安装失败
    echo.
    pause
    exit /b 1
) else (
    echo.
    echo ========================================
    echo    [✓] 依赖安装完成！
    echo ========================================
    echo.
    echo 您现在可以运行 start_agent.bat 启动智能体
    echo.
)

pause

