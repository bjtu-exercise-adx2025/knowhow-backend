import logging
import os
from logging.handlers import RotatingFileHandler

from flask import has_request_context, request


class RequestFormatter(logging.Formatter):
    def format(self, record):
        # 安全获取请求信息
        record.url = request.url if has_request_context() else '[no request]'
        record.remote_addr = request.remote_addr if has_request_context() else '[no request]'
        return super().format(record)


def init_logging(app):
    log_level = logging.DEBUG if app.debug else logging.INFO
    log_dir = os.path.join(app.root_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)

    """线程安全的日志初始化"""
    if hasattr(app, '_logging_configured'):  # 避免重复初始化
        return

    # 移除默认处理器（防止重复日志）
    from flask.logging import default_handler
    if default_handler in app.logger.handlers:
        app.logger.removeHandler(default_handler)

    # 配置格式和处理器（同原代码）
    formatter = RequestFormatter(
        '[%(asctime)s] %(remote_addr)s requested %(url)s\n'
        '%(levelname)s in %(module)s: %(message)s'
    )
    # 文件处理器（按大小轮换）
    file_handler = RotatingFileHandler(
        filename=os.path.join(log_dir, 'app.log'),
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)

    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.DEBUG if app.debug else logging.WARNING)

    # 绑定处理器
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG if app.debug else logging.INFO)

    # 标记已配置
    app._logging_configured = True
