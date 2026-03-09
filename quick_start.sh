#!/bin/bash

# 股票模拟交易回测系统 - 快速启动脚本

echo "🚀 股票模拟交易回测系统 - 快速启动"
echo "========================================="

# 检查Python环境
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未安装，请先安装Python3"
    exit 1
fi

# 检查必要的Python包
echo "📦 检查Python依赖..."
python3 -c "import pandas, numpy, matplotlib, seaborn" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  缺少必要的Python包，正在安装..."
    pip3 install pandas numpy matplotlib seaborn
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p data results visualizations

# 运行测试
echo "🧪 运行系统测试..."
python3 run_tests.py

if [ $? -eq 0 ]; then
    echo "✅ 测试通过！"
    
    # 运行主程序
    echo "🏃 运行主回测程序..."
    python3 main_backtest.py
    
    echo "📊 生成分析报告..."
    python3 results/analysis.py
    
    echo "🎉 系统运行完成！"
    echo "📁 结果文件："
    echo "   - results/backtest_report.csv"
    echo "   - results/visualizations/"
    echo "   - results/performance_report.md"
else
    echo "❌ 测试失败，请检查系统配置"
    exit 1
fi