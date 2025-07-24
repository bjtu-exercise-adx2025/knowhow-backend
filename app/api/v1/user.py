from flask import Blueprint, request
from flask import current_app

from app import db
from app.models.user import User

user_bp = Blueprint('users', __name__)


def check_if_email_exist(email: str) -> bool:
    users = User.query.filter_by(email=email).all()
    return len(users) > 0


@user_bp.route('/users', methods=['GET'])
def get_user_list():
    """
    获取用户列表
    ---
    responses:
        200:
            description: 成功获取用户列表
            schema:
                type: array
                items:
                    $ref: '#/definitions/User'
    """
    users = User.query.all()
    return {'users': [user.to_dict() for user in users]}


@user_bp.route('/users', methods=['POST'])
def create_user():
    """
    创建新用户
    ---
    parameters:
        - name: user
            in: body
            required: true
            schema:
                type: object
                properties:
                    email:
                      type: string
                    password:
                      type: string
                    username:
                      type: string
                    phone:
                      type: string
    """
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    username = data.get('username')
    phone = data.get('phone')

    if not email or not password:
        return {'message': '邮箱或密码为空'}, 400
    if check_if_email_exist(email):
        return {'message': '邮箱已存在'}, 400
    try:

        user = User(email=email)
        user.set_hashed_password(password)
        if username:
            user.username = username
        else:
            user.set_username_by_time()
        if phone:
            user.phone = phone
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return {'message': str(e)}, 400

    return {'message': '用户创建成功'}, 201


@user_bp.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    获取用户信息
    ---
    parameters:
        - name: user_id
            in: path
            required: true
            type: integer
    responses:
        200:
            description: 成功获取用户信息
            schema:
                $ref: '#/definitions/User'
        404:
            description: 用户不存在
    """
    user = User.query.get(user_id)
    if not user:
        return {'message': '用户不存在'}, 404

    return user.to_dict()


@user_bp.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    更新用户信息
    ---
    parameters:
        - name: user_id
            in: path
            required: true
            type: integer
        - name: user
            in: body
            required: true
            schema:
                type: object
                properties:
                    email:
                        type: string
                    password:
                        type: string
                    last_login:
                        type: string
                      format: date-time
                    phone:
                        type: string
                    username:
                        type: string
    responses:
        200:
            description: 成功更新用户信息
        404:
            description: 用户不存在
    """
    data = request.get_json()
    user = User.query.get(user_id)
    if not user:
        return {'message': '用户不存在'}, 404

    if 'email' in data:
        user.email = data['email']
    if 'password' in data:
        user.set_hashed_password(data['password'])
    if 'last_login' in data:
        user.last_login = data['last_login']
    if 'phone' in data:
        user.phone = data['phone']
    if 'username' in data:
        user.username = data['username']

    db.session.commit()

    return {'message': '用户信息更新成功'}


@user_bp.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    删除用户
    ---
    parameters:
        - name: user_id
            in: path
            required: true
            type: integer
    responses:
        200:
            description: 成功删除用户
        404:
            description: 用户不存在
    """
    user = User.query.get(user_id)
    if not user:
        return {'message': '用户不存在'}, 404

    db.session.delete(user)
    db.session.commit()

    return {'message': '用户删除成功'}
