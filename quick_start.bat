@echo off
chcp 65001 >nul
echo 🚀 股票模拟交易回测系统 - 快速启动
echo =========================================

REM 检查Python环境
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python 未安装，请先安装Python
    pause
    exit /b 1
)

REM 检查必要的Python包
echo 📦 检查Python依赖...
python -c "import pandas, numpy, matplotlib, seaborn" >nul 2>&1
if %errorlevel% neq 0 (
    echo ⚠️  缺少必要的Python包，正在安装...
    pip install pandas numpy matplotlib seaborn
)

REM 创建必要的目录
echo 📁 创建必要的目录...
if not exist "data" mkdir data
if not exist "results" mkdir results
if not exist "visualizations" mkdir visualizations

REM 运行测试
echo 🧪 运行系统测试...
python run_tests.py

if %errorlevel% equ 0 (
    echo ✅ 测试通过！
    
    REM 运行主程序
    echo 🏃 运行主回测程序...
    python main_backtest.py
    
    echo 📊 生成分析报告...
    python results\analysis.py
    
    echo 🎉 系统运行完成！
    echo 📁 结果文件：
    echo    - results\backtest_report.csv
    echo    - results\visualizations\
    echo    - results\performance_report.md
) else (
    echo ❌ 测试失败，请检查系统配置
    pause
    exit /b 1
)

pause