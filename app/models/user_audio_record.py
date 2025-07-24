import datetime as dt
from datetime import datetime

from sqlalchemy import BigInteger, Integer, Text
from sqlalchemy_serializer import SerializerMixin

from app import db


class UserAudioRecord(db.Model, SerializerMixin):
    """用户语音片段记录表"""

    __tablename__ = "user_audio_records"

    id = db.Column(BigInteger, primary_key=True, autoincrement=True, comment="片段ID")
    user_id = db.Column(
        BigInteger, db.ForeignKey("users.id"), nullable=False, comment="所属用户ID"
    )
    audio_url = db.Column(
        db.String(512), nullable=False, comment="语音文件在对象存储中的地址"
    )
    transcript = db.Column(Text, comment="用户确认后的语音转录文字")
    duration = db.Column(Integer, nullable=False, default=0, comment="语音时长（秒）")
    created_at = db.Column(
        db.DateTime, nullable=False, default=datetime.now(dt.UTC), comment="创建时间"
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now(dt.UTC),
        onupdate=datetime.now(dt.UTC),
        comment="更新时间",
    )

    # 添加索引
    __table_args__ = (db.Index("idx_user_id", "user_id"),)
