from flask import Blueprint
from flask_restx import Api  # 或使用 Flask-RESTful

# 创建主 API 蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api')  # 保持父级前缀

# 初始化 RESTX API 实例（可选，若使用 Flask-RESTX）
api = Api(
    api_bp,
    version='1.0',
    title='Project 2025 API',
    description='A RESTful API built with Flask',
    doc='/docs'  # Swagger UI 路径
)

# 导入并注册版本化的子蓝图
from .v1 import v1_bp

api_bp.register_blueprint(v1_bp)  # 明确子级前缀
