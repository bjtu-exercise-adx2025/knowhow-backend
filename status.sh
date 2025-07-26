#!/bin/bash

echo "📊 Project2025-Backend 服务状态"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查 Gunicorn
if pgrep -f "gunicorn.*run:app" > /dev/null; then
    GUNICORN_PID=$(pgrep -f "gunicorn.*run:app")
    echo "🌐 Web 服务: ✅ 运行中 (PID: $GUNICORN_PID)"
else
    echo "🌐 Web 服务: ❌ 未运行"
fi

# 检查调度器
if pgrep -f "python.*scheduler.py" > /dev/null; then
    SCHEDULER_PID=$(pgrep -f "python.*scheduler.py")
    echo "⏰ 调度器: ✅ 运行中 (PID: $SCHEDULER_PID)"
else
    echo "⏰ 调度器: ❌ 未运行"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 显示端口占用情况
echo "🔌 端口使用情况："
netstat -tlnp 2>/dev/null | grep :8888 || echo "   端口 8888 未被占用"

# 显示最近的日志
if [ -f "logs/gunicorn.log" ]; then
    echo ""
    echo "📄 Web 服务最近日志 (最后 5 行)："
    tail -5 logs/gunicorn.log
fi

if [ -f "logs/scheduler.log" ]; then
    echo ""
    echo "⏰ 调度器最近日志 (最后 5 行)："
    tail -5 logs/scheduler.log
fi
