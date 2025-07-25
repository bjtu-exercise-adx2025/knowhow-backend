import datetime as dt
from datetime import datetime

from sqlalchemy import BigInteger, Text, JSON
from sqlalchemy_serializer import SerializerMixin

from app import db


class GenerationTask(db.Model, SerializerMixin):
    """文章生成任务表"""

    __tablename__ = "generation_tasks"

    id = db.Column(BigInteger, primary_key=True, autoincrement=True, comment="任务ID")
    user_id = db.Column(
        BigInteger, db.ForeignKey("users.id"), nullable=False, comment="任务创建者ID"
    )
    summary_status = db.Column(
        BigInteger,
        nullable=False,
        default=0,
        comment="文章总结任务状态: 0-pending, 1-processing, 2-completed,",
    )
    langgraph_status = db.Column(
        BigInteger,
        nullable=False,
        default=0,
        comment="LangGraph任务状态: 0-pending, 1-processing, 2-completed, 3-failed",
    )
    error_message = db.Column(Text, comment="任务失败时的错误信息")
    created_articles = db.Column(
        JSON, nullable=False, default=lambda: [], comment="langgraph创建的文章ID列表"
    )
    updated_articles = db.Column(
        JSON, nullable=False, default=lambda: [], comment="langgraph更新的文章ID列表"
    )
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

    # 关系定义
    audio_records = db.relationship(
        "UserAudioRecord",
        secondary="task_records_mapping",
        backref="generation_tasks",
        lazy="dynamic",
    )

    # 添加索引
    __table_args__ = (db.Index("idx_user_id", "user_id"),)


class TaskRecordsMapping(db.Model):
    """任务与语音片段的关联表"""

    __tablename__ = "task_records_mapping"

    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = db.Column(
        BigInteger,
        db.ForeignKey("generation_tasks.id"),
        nullable=False,
        comment="任务ID",
    )
    record_id = db.Column(
        BigInteger,
        db.ForeignKey("user_audio_records.id"),
        nullable=False,
        comment="语音片段ID",
    )

    # 添加索引和唯一约束
    __table_args__ = (
        db.UniqueConstraint("task_id", "record_id", name="uk_task_record"),
        db.Index("idx_record_id", "record_id"),
    )
