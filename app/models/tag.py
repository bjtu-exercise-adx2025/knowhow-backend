import datetime as dt
from datetime import datetime

from sqlalchemy import BigInteger, Integer
from sqlalchemy_serializer import SerializerMixin

from app import db


class Tag(db.Model, SerializerMixin):
    """标签表"""

    __tablename__ = "tags"
    
    # 序列化规则：排除循环引用的关系字段
    serialize_rules = ('-articles',)

    id = db.Column(Integer, primary_key=True, autoincrement=True, comment="标签ID")
    user_id = db.Column(
        BigInteger, db.ForeignKey("users.id"), nullable=False, comment="用户ID"
    )
    name = db.Column(db.String(50), nullable=False, comment="标签名")
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now(dt.UTC), comment="创建时间"
    )

    # 添加唯一约束
    __table_args__ = (db.UniqueConstraint("name", name="uk_name"),)
