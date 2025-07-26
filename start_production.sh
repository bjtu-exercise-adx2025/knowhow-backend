#!/bin/bash

# 生产环境启动脚本

echo "🚀 启动 Project2025-Backend 生产环境..."

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建虚拟环境"
    exit 1
fi

# 激活虚拟环境
source .venv/bin/activate

# 检查依赖
echo "📦 检查依赖..."
pip install -r requirements.txt

# 停止已存在的进程
echo "🛑 停止已存在的进程..."
pkill -f "gunicorn.*run:app"
pkill -f "python.*scheduler.py"

# 等待进程完全停止
sleep 3

# 确保进程已完全停止
if pgrep -f "gunicorn.*run:app" > /dev/null || pgrep -f "python.*scheduler.py" > /dev/null; then
    echo "⚠️  强制停止残留进程..."
    pkill -9 -f "gunicorn.*run:app"
    pkill -9 -f "python.*scheduler.py"
    sleep 2
fi

# 创建日志目录
mkdir -p logs

# 启动调度器
echo "⏰ 启动定时任务调度器..."
nohup python scheduler.py > logs/scheduler.log 2>&1 &
SCHEDULER_PID=$!

# 等待调度器启动
sleep 2

# 检查调度器是否启动成功
if ! pgrep -f "python.*scheduler.py" > /dev/null; then
    echo "❌ 调度器启动失败，请检查日志文件 logs/scheduler.log"
    exit 1
fi

echo "✅ 调度器启动成功 (PID: $SCHEDULER_PID)"

# 启动 Gunicorn Web 服务
echo "🌟 启动 Gunicorn Web 服务器..."
nohup gunicorn -c gunicorn.conf.py run:app > logs/gunicorn.log 2>&1 &
GUNICORN_PID=$!

# 等待 Web 服务启动
sleep 3

# 检查 Web 服务状态
if ! pgrep -f "gunicorn.*run:app" > /dev/null; then
    echo "❌ Web 服务启动失败，请检查日志文件 logs/gunicorn.log"
    echo "🛑 停止调度器..."
    pkill -f "python.*scheduler.py"
    exit 1
fi

echo "✅ Web 服务启动成功 (PID: $GUNICORN_PID)"

# 保存 PID 到文件，方便后续管理
echo $SCHEDULER_PID > logs/scheduler.pid
echo $GUNICORN_PID > logs/gunicorn.pid

# 显示服务信息
echo ""
echo "🎉 所有服务启动成功！"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 服务信息："
echo "   🌐 Web 服务地址: http://0.0.0.0:8888"
echo "   🔐 管理界面: http://0.0.0.0:8888/admin"
echo "   📚 API 文档: http://0.0.0.0:8888/api/docs"
echo ""
echo "📁 日志文件："
echo "   📄 Web 服务日志: logs/gunicorn.log"
echo "   ⏰ 调度器日志: logs/scheduler.log"
echo ""
echo "🔧 进程管理："
echo "   📋 查看服务状态: ./status.sh"
echo "   🛑 停止所有服务: ./stop.sh"
echo "   🔄 重启所有服务: ./restart.sh"
echo "   📊 查看日志: tail -f logs/gunicorn.log 或 tail -f logs/scheduler.log"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 简单的健康检查
echo ""
echo "🔍 执行健康检查..."
sleep 2

if curl -s http://127.0.0.1:8888/ > /dev/null; then
    echo "✅ Web 服务健康检查通过"
else
    echo "⚠️  Web 服务健康检查失败，请检查服务状态"
fi

if pgrep -f "python.*scheduler.py" > /dev/null; then
    echo "✅ 调度器服务运行正常"
else
    echo "⚠️  调度器服务异常，请检查日志"
fi

echo ""
echo "🎯 服务启动完成！按 Ctrl+C 查看实时日志，或使用上述命令管理服务。"
