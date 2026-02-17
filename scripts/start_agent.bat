@echo off
chcp 65001 >nul
title 超智引擎智能体
color 0A

echo ========================================
echo    超智引擎智能体 - 启动脚本
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

REM 检查是否在项目目录
if not exist "agent.py" (
    echo [错误] 未找到agent.py文件，请确保在项目根目录运行此脚本
    echo.
    pause
    exit /b 1
)

echo [✓] 项目文件检查通过
echo.

REM 检查虚拟环境
if exist "venv\Scripts\activate.bat" (
    echo [信息] 检测到虚拟环境，正在激活...
    call venv\Scripts\activate.bat
    echo [✓] 虚拟环境已激活
    echo.
)

REM 检查依赖是否安装
echo [信息] 正在检查依赖包...
python -c "import openai" >nul 2>&1
if errorlevel 1 (
    echo [警告] 检测到缺少依赖包，正在安装...
    echo.
    pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [错误] 依赖安装失败，请检查网络连接或手动运行: pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo.
    echo [✓] 依赖安装完成
    echo.
) else (
    echo [✓] 依赖检查通过
    echo.
)

REM 检查配置文件
if not exist ".env" (
    if exist ".env.example" (
        echo [提示] 未找到.env配置文件
        echo [提示] 您可以复制.env.example为.env并填入您的API密钥
        echo.
    ) else (
        echo [提示] 请确保已配置API密钥（通过环境变量或.env文件）
        echo.
    )
)

REM 启动程序
echo ========================================
echo    正在启动智能体...
echo ========================================
echo.

python agent.py

REM 如果程序异常退出
if errorlevel 1 (
    echo.
    echo [错误] 程序异常退出，错误代码: %errorlevel%
    echo.
    pause
)

