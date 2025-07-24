from flask import Blueprint, current_app, request

from app import db
from app.models.user import User
from app.utils.oss_service import OSSService

user_bp = Blueprint("users", __name__)
AVATAR_FIELD = "avatar"


def check_if_email_exist(email: str) -> bool:
    users = User.query.filter_by(email=email).all()
    return len(users) > 0


@user_bp.route("/users", methods=["GET"])
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
    return {"users": [user.to_dict() for user in users]}


@user_bp.route("/users", methods=["POST"])
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
    email = data.get("email")
    password = data.get("password")
    username = data.get("username")
    phone = data.get("phone")

    if not email or not password:
        return {"message": "邮箱或密码为空"}, 400
    if check_if_email_exist(email):
        return {"message": "邮箱已存在"}, 400
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
        return {"message": str(e)}, 400

    return {"message": "用户创建成功"}, 201


@user_bp.route("/users/<int:user_id>", methods=["GET"])
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
        return {"message": "用户不存在"}, 404

    return user.to_dict()


@user_bp.route("/users/<int:user_id>", methods=["PUT"])
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
        return {"message": "用户不存在"}, 404

    if "email" in data:
        user.email = data["email"]
    if "password" in data:
        user.set_hashed_password(data["password"])
    if "last_login" in data:
        user.last_login = data["last_login"]
    if "phone" in data:
        user.phone = data["phone"]
    if "username" in data:
        user.username = data["username"]

    db.session.commit()

    return {"message": "用户信息更新成功"}


@user_bp.route("/users/<int:user_id>", methods=["DELETE"])
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
        return {"message": "用户不存在"}, 404

    db.session.delete(user)
    db.session.commit()

    return {"message": "用户删除成功"}


@user_bp.route("/users/<int:user_id>/avatar", methods=["POST"])
def upload_avatar(user_id):
    """
    上传用户头像
    ---
    parameters:
        - name: user_id
          in: path
          required: true
          type: integer
        - name: avatar
          in: formData
          required: true
          type: file
          description: 头像文件 (支持 JPG, PNG, GIF, WebP，最大5MB)
    responses:
        200:
            description: 头像上传成功
            schema:
                type: object
                properties:
                    message:
                        type: string
                    avatar_url:
                        type: string
        400:
            description: 请求参数错误
        404:
            description: 用户不存在
        500:
            description: 服务器内部错误
    """
    try:
        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return {"message": "用户不存在"}, 404

        # 检查是否有文件上传
        if AVATAR_FIELD not in request.files:
            return {"message": "请选择要上传的头像文件"}, 400

        file = request.files[AVATAR_FIELD]
        if file.filename == "":
            return {"message": "请选择要上传的头像文件"}, 400

        # 读取文件数据
        file_data = file.read()
        if not file_data:
            return {"message": "文件内容为空"}, 400

        # 验证文件
        is_valid, result = OSSService.validate_image_file(file_data)
        if not is_valid:
            return {"message": result}, 400

        file_extension = result

        # 创建OSS服务实例并上传文件
        oss_service = OSSService()

        # 如果用户已有头像，先删除旧头像
        if user.avatar_url:
            oss_service.delete_avatar(user.avatar_url)

        # 上传新头像
        avatar_url = oss_service.upload_avatar(file_data, file_extension, user_id)

        # 更新用户头像URL
        user.avatar_url = avatar_url
        db.session.commit()

        return {"message": "头像上传成功", "avatar_url": avatar_url}, 200

    except ValueError as e:
        current_app.logger.error(f"OSS配置错误: {str(e)}")
        return {"message": "服务配置错误，请联系管理员"}, 500
    except Exception as e:
        current_app.logger.error(f"头像上传失败: {str(e)}")
        db.session.rollback()
        return {"message": "头像上传失败，请稍后重试"}, 500


@user_bp.route("/users/<int:user_id>/avatar", methods=["DELETE"])
def delete_avatar(user_id):
    """
    删除用户头像
    ---
    parameters:
        - name: user_id
          in: path
          required: true
          type: integer
    responses:
        200:
            description: 头像删除成功
        404:
            description: 用户不存在
        500:
            description: 服务器内部错误
    """
    try:
        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return {"message": "用户不存在"}, 404

        if not user.avatar_url:
            return {"message": "用户暂无头像"}, 400

        # 创建OSS服务实例并删除文件
        oss_service = OSSService()

        # 删除OSS中的头像文件
        delete_success = oss_service.delete_avatar(user.avatar_url)

        # 清空用户头像URL
        user.avatar_url = ""
        db.session.commit()

        if delete_success:
            return {"message": "头像删除成功"}, 200
        else:
            return {"message": "头像删除成功（文件已不存在）"}, 200

    except Exception as e:
        current_app.logger.error(f"头像删除失败: {str(e)}")
        db.session.rollback()
        return {"message": "头像删除失败，请稍后重试"}, 500
