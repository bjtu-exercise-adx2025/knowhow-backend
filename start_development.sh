#!/bin/bash

# 开发环境启动脚本

echo "🔧 启动 Project2025-Backend开发环境..."

# 检查虚拟环境
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建虚拟环境"
    exit 1
fi

# 激活虚拟环境
source venv/bin/activate

# 检查依赖
echo "📦 检查依赖..."
pip install -r requirements.txt

# 停止已存在的进程
echo "🛑 停止已存在的进程..."
pkill -f "python run.py"

# 等待进程完全停止
sleep 2

# 启动 Flask 开发服务器
echo "🌟 启动 Flask 开发服务器..."
python run.py 