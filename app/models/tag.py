import datetime as dt
from datetime import datetime

from sqlalchemy import Integer
from sqlalchemy_serializer import SerializerMixin

from app import db


class Tag(db.Model, SerializerMixin):
    """标签表"""

    __tablename__ = "tags"

    id = db.Column(Integer, primary_key=True, autoincrement=True, comment="标签ID")
    name = db.Column(db.String(50), nullable=False, comment="标签名")
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now(dt.UTC), comment="创建时间"
    )

    # 添加唯一约束
    __table_args__ = (db.UniqueConstraint("name", name="uk_name"),)
