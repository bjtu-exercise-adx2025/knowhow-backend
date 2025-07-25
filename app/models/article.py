import datetime as dt
from datetime import datetime

from sqlalchemy import BigInteger, Integer, Text
from sqlalchemy_serializer import SerializerMixin

from app import db


class Article(db.Model, SerializerMixin):
    """文章表"""

    __tablename__ = "articles"
    
    # 序列化规则：限制tags关系的深度，避免循环引用
    serialize_rules = ('-tags.articles',)

    id = db.Column(BigInteger, primary_key=True, autoincrement=True, comment="文章ID")
    author_id = db.Column(
        BigInteger, db.ForeignKey("users.id"), nullable=False, comment="作者ID"
    )
    title = db.Column(
        db.String(255), nullable=False, default="", comment="AI生成的标题"
    )
    summary = db.Column(Text, comment="AI生成的摘要/概览")
    content = db.Column(db.Text, comment="AI生成的完整文章内容 (Markdown格式)")
    status = db.Column(
        db.String(20),
        nullable=False,
        default="published",
        comment="状态: published, archived",
    )
    finished_at = db.Column(db.DateTime, comment="任务完成并自动发布的时间")
    created_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now(dt.UTC),
        comment="记录创建时间",
    )
    updated_at = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.now(dt.UTC),
        onupdate=datetime.now(dt.UTC),
        comment="更新时间",
    )

    # 关系定义
    tags = db.relationship(
        "Tag", secondary="article_tags", backref="articles", lazy="dynamic"
    )

    # 添加索引
    __table_args__ = (
        db.Index("idx_author_id_status_finished", "author_id", "status", "finished_at"),
    )


class ArticleTag(db.Model):
    """文章与标签的关联表"""

    __tablename__ = "article_tags"

    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    article_id = db.Column(
        BigInteger, db.ForeignKey("articles.id"), nullable=False, comment="文章ID"
    )
    tag_id = db.Column(
        Integer, db.ForeignKey("tags.id"), nullable=False, comment="标签ID"
    )

    # 添加索引和唯一约束
    __table_args__ = (
        db.UniqueConstraint("article_id", "tag_id", name="uk_article_tag"),
        db.Index("idx_tag_id", "tag_id"),
    )


class ArticleRelationship(db.Model):
    """文章引用关系表"""

    __tablename__ = "article_relationships"

    id = db.Column(BigInteger, primary_key=True, autoincrement=True)
    citing_article_id = db.Column(
        BigInteger, 
        db.ForeignKey("articles.id"), 
        nullable=False, 
        comment="引用文章ID（新文章）"
    )
    referenced_article_id = db.Column(
        BigInteger, 
        db.ForeignKey("articles.id"), 
        nullable=False, 
        comment="被引用文章ID（被引用的文章）"
    )
    created_at = db.Column(
        db.DateTime, 
        nullable=False, 
        default=datetime.now(dt.UTC), 
        comment="引用关系创建时间"
    )

    # 添加索引和唯一约束
    __table_args__ = (
        db.UniqueConstraint("citing_article_id", "referenced_article_id", name="uk_article_relationship"),
        db.Index("idx_citing_article_id", "citing_article_id"),
        db.Index("idx_referenced_article_id", "referenced_article_id"),
    )
