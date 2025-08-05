@echo off
title 智能AI工具平台
echo.
echo ========================================
echo    智能AI工具平台启动脚本
echo ========================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.7+
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [信息] Python检查通过
echo.

REM 检查依赖包
echo [信息] 检查依赖包...
pip list | findstr "Flask" >nul 2>&1
if %errorlevel% neq 0 (
    echo [信息] 正在安装依赖包...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [错误] 依赖包安装失败
        pause
        exit /b 1
    )
)

echo [信息] 依赖包检查完成
echo.

REM 创建必要目录
if not exist "data" mkdir data
if not exist "config" mkdir config

echo [信息] 正在启动智能AI工具平台...
echo [信息] 启动完成后请访问: http://localhost:5000
echo [信息] 配置页面: http://localhost:5000/config
echo [信息] 按 Ctrl+C 停止服务器
echo.

REM 启动应用
python start.py

pause