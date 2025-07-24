from flask import Blueprint
from flask_restx import Api, Namespace

# 创建 v1 版本的蓝图
v1_bp = Blueprint('v1', __name__, url_prefix='/v1')
# 创建命名空间
ns_v1 = Namespace('v1', description='API version 1 operations')  # 添加path参数

# 创建 API 实例并绑定到蓝图
api_v1 = Api(
    v1_bp,
    version='1.0',
    title='API v1',
    description='API version 1 operations',
    doc=False,  # 禁用子蓝图文档
)

api_v1.add_namespace(ns_v1)

# 导入并注册当前版本的路由模块
from . import (
    analytics,
    appointment,
    auth,
    cart,
    health_profile,
    order,
    shop,
    system,
    user,
    admin_auth
)

# 将蓝图注册到主 API 蓝图
v1_bp.register_blueprint(user.user_bp)  # 明确子级前缀
v1_bp.register_blueprint(health_profile.health_profile_bp)
v1_bp.register_blueprint(auth.auth_bp)
v1_bp.register_blueprint(shop.shop_bp)
v1_bp.register_blueprint(appointment.appointment_bp)
v1_bp.register_blueprint(cart.cart_bp)
v1_bp.register_blueprint(order.order_bp)
v1_bp.register_blueprint(admin_auth.admin_auth_bp)
