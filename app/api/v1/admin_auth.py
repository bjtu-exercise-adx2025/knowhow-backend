from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user

from app.models.admin_user import AdminUser

# 创建管理员认证蓝图
admin_auth_bp = Blueprint('admin_auth', __name__, url_prefix='/admin_auth')


@admin_auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # 如果用户已经登录且是管理员，直接跳转到管理页面
    if current_user.is_authenticated:
        return redirect(url_for('admin.index'))

    if request.method == 'POST':
        # 获取表单数据
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False

        # 查找用户
        admin_user = AdminUser.query.filter_by(username=username).first()

        # 检查用户是否存在、密码是否正确
        if not admin_user or not admin_user.verify_password(password):
            flash('登录失败，请检查您的邮箱和密码，或者您可能没有管理员权限', 'danger')
            return redirect(url_for('api.v1.admin_auth.login'))

        # 登录用户
        login_user(admin_user, remember=remember)

        # 如果有next参数，则重定向到该页面，否则重定向到管理员首页
        next_page = request.args.get('next')
        if next_page and next_page.startswith('/admin'):
            return redirect(next_page)
        return redirect(url_for('admin.index'))

    # GET请求时显示登录表单
    return render_template('admin/login.html')


@admin_auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('您已成功退出管理员登录', 'success')
    return redirect(url_for('admin_auth.login'))
