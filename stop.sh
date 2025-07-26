#!/bin/bash

echo "🛑 停止 Project2025-Backend 所有服务..."

# 停止服务
pkill -f "gunicorn.*run:app"
pkill -f "python.*scheduler.py"

# 等待进程停止
sleep 2

# 强制停止（如果需要）
if pgrep -f "gunicorn.*run:app" > /dev/null || pgrep -f "python.*scheduler.py" > /dev/null; then
    echo "⚠️  强制停止残留进程..."
    pkill -9 -f "gunicorn.*run:app"
    pkill -9 -f "python.*scheduler.py"
    sleep 1
fi

# 清理 PID 文件
rm -f logs/scheduler.pid logs/gunicorn.pid

# 检查停止结果
if ! pgrep -f "gunicorn.*run:app" > /dev/null && ! pgrep -f "python.*scheduler.py" > /dev/null; then
    echo "✅ 所有服务已成功停止"
else
    echo "❌ 部分服务停止失败，请手动检查"
fi
