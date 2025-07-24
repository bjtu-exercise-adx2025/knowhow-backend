import datetime as dt
from datetime import datetime

from sqlalchemy import BigInteger
from sqlalchemy_serializer import SerializerMixin

from app import db
from app.utils.security import SecurityUtils


class User(db.Model, SerializerMixin):
    """系统注册用户信息"""
    __tablename__ = 'User'
    user_id = db.Column(BigInteger, primary_key=True, autoincrement=True, comment='用户唯一标识')
    username = db.Column(db.String(50), nullable=False, comment='登录用户名（3-50字符，唯一）')
    email = db.Column(db.String(255), nullable=True, comment='已验证的邮箱地址')
    phone = db.Column(db.String(20), comment='E.164格式国际电话号码，如：+8613812345678')
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.now(dt.UTC),
                           comment='账户创建时间（UTC时区）')
    last_login = db.Column(db.DateTime, comment='最近登录时间（可为空）')
    password = db.Column(db.String(128), nullable=False, comment='加密后的密码')

    def set_username_by_time(self):
        """设置用户名，取当前时间后8位数字再加上一个内置的掩码"""
        self.username = f'用户{int(datetime.now(dt.UTC).strftime("%Y%m%d%H%M%S")[:8]) + 0o02050231}'

    def set_hashed_password(self, password: str):
        """设置加密后的密码"""
        self.password = SecurityUtils.hash_password(password)

    def verify_password(self, password: str) -> bool:
        """验证密码是否正确"""
        return SecurityUtils.verify_password(self.password, password)
