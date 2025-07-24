#!/bin/bash

# 生产环境启动脚本

echo "🚀 启动 Project2025-Backend生产环境..."

# 检查是否已构建前端
if [ ! -d "admin/dist" ]; then
    echo "⚠️  前端未构建，正在构建..."
    ./build_admin.sh
fi

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
pkill -f gunicorn

# 等待进程完全停止
sleep 2

# 启动 Gunicorn
echo "🌟 启动 Gunicorn 服务器..."
nohup gunicorn -c gunicorn.conf.py run:app > gunicorn.log 2>&1 &

# 等待服务启动
sleep 3

# 检查服务状态
if pgrep -f gunicorn > /dev/null; then
    echo "✅ 服务启动成功！"
    echo "📊 服务信息："
    echo "   - 地址: http://0.0.0.0:8888"
    echo "   - 管理界面: http://0.0.0.0:8888/admin"
    echo "   - API 文档: http://0.0.0.0:8888/api/docs"
    echo "📝 日志文件: gunicorn.log"
    echo "🛑 停止服务: pkill -f gunicorn"
else
    echo "❌ 服务启动失败，请检查日志文件 gunicorn.log"
    exit 1
fi 