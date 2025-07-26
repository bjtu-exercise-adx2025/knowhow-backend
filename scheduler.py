from app import create_app
from app.utils.task_scheduler import scheduler
import signal
import sys

app = create_app()


def shutdown_handler(sig, frame):
    print("\n收到关闭信号，正在停止调度器...")
    if scheduler.running:
        scheduler.stop()
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    scheduler.init_app(app)

    print("启动独立的定时任务调度器...")
    scheduler.start()
    print("定时任务调度器已启动，按 Ctrl+C 停止")

    try:
        # 保持进程运行
        signal.pause()
    except KeyboardInterrupt:
        shutdown_handler(None, None)
