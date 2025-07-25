from sqlalchemy import text

from app import create_app, db
from app.utils.task_scheduler import scheduler

app = create_app()


def reset_db():
    with app.app_context():
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 0"))
        db.session.commit()
        db.drop_all()  # 先删除所有表（慎用生产环境！）
        db.create_all()
        db.session.execute(text("SET FOREIGN_KEY_CHECKS = 1"))
        db.session.commit()
        # 创建一个AdminUser， username=admin， password=admin
        from app.models.admin_user import AdminUser
        admin = AdminUser()
        admin.username = 'admin'
        admin.password = 'admin'
        db.session.add(admin)
        db.session.commit()
        app.logger.info("数据库表结构已重建")


if __name__ == '__main__':
    import signal
    import sys
    
    port = 8888

    @app.route('/')
    def test():
        return f"Flask is working! Port {port}"

    # 初始化定时任务调度器
    scheduler.init_app(app)
    
    # 定义优雅关闭函数
    def shutdown_handler(sig, frame):
        print("\n收到关闭信号，正在停止服务...")
        scheduler.stop()
        sys.exit(0)
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    with app.app_context():
        routes = [rule.rule for rule in app.url_map.iter_rules() if rule.endpoint != 'static']
        print("所有路由路径：", routes)

    # reset_db()
    
    # 启动定时任务调度器
    print("启动定时任务调度器...")
    scheduler.start()
    print("定时任务调度器已启动")

    print(f"启动Flask应用，端口：{port}")
    print("现在同时运行Web服务器和定时任务调度器")
    print("按 Ctrl+C 停止所有服务")
    
    app.run(
        host='127.0.0.1',  # 允许外部访问（默认127.0.0.1仅本地）
        port=port,  # 默认端口5000，可修改为80或其他
        threaded=True,  # 启用多线程处理请求
        ssl_context='adhoc'  # 可选：启用HTTPS（生产环境建议用Nginx反向代理）
    )
