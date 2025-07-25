import os

from flask import Flask, redirect, request, send_from_directory
from flask_sslify import SSLify

from flask import Flask, redirect, request, send_from_directory

from .config import Config, DevelopmentConfig
from .extensions import db, jwt, login_manager
from .utils.log_utils import init_logging


def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    sslify = SSLify(app)

    # 初始化日志
    init_logging(app)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    jwt.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message = "请先登录以访问该页面"
    login_manager.login_message_category = "info"

    # 注册API蓝图
    from .api import api_bp

    app.register_blueprint(api_bp, url_prefix="/api")

    # 添加静态资源路由（处理 /assets/ 和 /vite.svg 等路径）
    @app.route("/assets/<path:filename>")
    def serve_assets(filename):
        admin_dist_path = os.path.join(app.root_path, "..", "admin", "dist")
        file_path = os.path.join(admin_dist_path, "assets", filename)
        if os.path.exists(file_path):
            return send_from_directory(
                os.path.join(admin_dist_path, "assets"), filename
            )
        return {"error": "File not found"}, 404

    @app.route("/vite.svg")
    @app.route("/apple-touch-icon.png")
    @app.route("/apple-touch-icon-precomposed.png")
    def serve_root_assets():
        admin_dist_path = os.path.join(app.root_path, "..", "admin", "dist")
        filename = request.path.lstrip("/")
        file_path = os.path.join(admin_dist_path, filename)
        if os.path.exists(file_path):
            return send_from_directory(admin_dist_path, filename)
        return {"error": "File not found"}, 404

    # 添加 admin 前端路由
    @app.route("/admin")
    @app.route("/admin/<path:path>")
    def serve_admin(path=""):
        # 检查是否存在构建后的 admin 文件
        admin_dist_path = os.path.join(app.root_path, "..", "admin", "dist")

        if os.path.exists(admin_dist_path):
            # 生产环境：服务构建后的静态文件
            if path and os.path.exists(os.path.join(admin_dist_path, path)):
                return send_from_directory(admin_dist_path, path)
            else:
                return send_from_directory(admin_dist_path, "index.html")
        else:
            # 开发环境：重定向到 React 开发服务器
            return redirect("http://localhost:5173")

    return app
