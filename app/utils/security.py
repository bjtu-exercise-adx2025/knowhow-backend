from functools import wraps

from flask import current_app
from flask_bcrypt import Bcrypt
from itsdangerous import URLSafeTimedSerializer

bcrypt = Bcrypt()


class SecurityUtils:
    """安全工具类，包含密码哈希、令牌生成/验证等"""

    @staticmethod
    def hash_password(password: str) -> str:
        """生成更短的bcrypt哈希（约60字符）"""
        return bcrypt.generate_password_hash(password).decode(
            'utf-8')  # 示例：$2b$12$rSXRS7OFI2MmInOB/0tMgelZLCSby3o/okGPpaVUSTl6I2sCX.ogW

    @staticmethod
    def verify_password(hashed_password: str, password: str) -> bool:
        return bcrypt.check_password_hash(hashed_password, password)

    @staticmethod
    def generate_token(data: dict, salt: str = 'auth') -> str:
        """生成安全令牌（默认有效期1小时）"""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return serializer.dumps(data, salt=salt)

    @staticmethod
    def verify_token(token: str, max_age: int = 3600, salt: str = 'auth') -> dict:
        """验证令牌并返回数据（过期或无效返回None）"""
        serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            return serializer.loads(token, max_age=max_age, salt=salt)
        except:
            return None


def rate_limit(max_requests: int, window: int):
    """请求频率限制装饰器"""
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(
        key_func=get_remote_address,
        storage_uri="memory://",  # 生产环境替换为Redis
        default_limits=[f"{max_requests} per {window} seconds"]
    )

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            return limiter.limit(f"{max_requests}/{window}seconds")(f)(*args, **kwargs)

        return wrapped

    return decorator
