"""
数据库CRUD操作

提供文章处理相关的数据库操作功能
"""

import sys
import os
import re
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.models.user_audio_record import UserAudioRecord
from app.models.article import Article, ArticleRelationship
from .connection import DatabaseConnection
from ..utils.exceptions import DatabaseOperationError, ERROR_CODES
from ..utils.logger import get_logger


class DatabaseOperations:
    """数据库操作封装类"""
    
    def __init__(self):
        """初始化数据库操作类"""
        self.connection = DatabaseConnection()
        self.logger = get_logger()
        self._app_context = None
        self._ensure_app_context()
    
    def _ensure_app_context(self):
        """确保在Flask应用上下文中"""
        try:
            from flask import has_app_context
            
            if not has_app_context():
                from app import create_app
                app = create_app()
                self._app_context = app.app_context()
                self._app_context.__enter__()
        except Exception:
            # 如果无法创建应用上下文，继续运行但可能会有限制
            pass
    
    def get_transcript_by_id(self, transcript_id: int) -> Optional[str]:
        """
        根据ID获取语音转录文本
        
        Args:
            transcript_id: 语音转录记录ID
            
        Returns:
            转录文本内容，如果不存在返回None
        """
        try:
            self.logger.log_database_query("SELECT", "user_audio_records", {"id": transcript_id})
            
            session = self.connection.get_session()
            record = session.query(UserAudioRecord).filter_by(id=transcript_id).first()
            
            if not record:
                self.logger.log_database_query("SELECT", "user_audio_records", {"id": transcript_id}, 0)
                raise DatabaseOperationError(
                    f"Transcript with ID {transcript_id} not found",
                    ERROR_CODES["DB_TRANSCRIPT_NOT_FOUND"],
                    {"transcript_id": transcript_id}
                )
            
            self.logger.log_database_query("SELECT", "user_audio_records", {"id": transcript_id}, 1)
            return record.transcript
            
        except DatabaseOperationError:
            raise
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to get transcript: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {"transcript_id": transcript_id}
            )
    
    def get_articles_by_ids(self, article_ids: List[int]) -> List[Dict[str, Any]]:
        """
        根据ID列表获取文章内容
        
        Args:
            article_ids: 文章ID列表
            
        Returns:
            文章信息列表，每个元素包含id和content字段
        """
        try:
            if not article_ids:
                return []
            
            session = self.connection.get_session()
            articles = session.query(Article).filter(Article.id.in_(article_ids)).all()
            
            # 检查是否所有文章都存在
            found_ids = {article.id for article in articles}
            missing_ids = set(article_ids) - found_ids
            
            if missing_ids:
                raise DatabaseOperationError(
                    f"Articles not found: {list(missing_ids)}",
                    ERROR_CODES["DB_ARTICLE_NOT_FOUND"],
                    {"missing_ids": list(missing_ids), "requested_ids": article_ids}
                )
            
            # 格式化返回数据
            result = []
            for article in articles:
                result.append({
                    "id": article.id,
                    "content": article.content or ""  # 处理content为None的情况
                })
            
            # 按原始ID顺序排序
            id_to_article = {item["id"]: item for item in result}
            ordered_result = [id_to_article[article_id] for article_id in article_ids]
            
            return ordered_result
            
        except DatabaseOperationError:
            raise
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to get articles: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {"article_ids": article_ids}
            )
    
    def create_article(self, content: str, author_id: int, title: str = None, summary: str = None) -> int:
        """
        创建新文章
        
        Args:
            content: 文章内容 (Markdown格式)
            author_id: 作者ID
            title: 文章标题，如果未提供则从内容生成
            summary: 文章摘要，如果未提供则从内容生成
            
        Returns:
            新创建文章的ID
        """
        try:
            session = self.connection.get_session()
            
            # 如果没有提供标题，从内容前50个字符生成
            if not title:
                title = self._generate_title_from_content(content)
            
            # 如果没有提供摘要，从内容前50个字符生成
            if not summary:
                summary = content[:50] + "..." if len(content) > 50 else content
            
            # 创建文章记录
            article = Article(
                author_id=author_id,
                title=title,
                summary=summary,
                content=content,
                status="published",  # 默认为已发布状态
                finished_at=datetime.utcnow(),  # 设置完成时间为当前时间
                # 移除了source_task_id字段
            )
            
            session.add(article)
            session.flush()  # 获取ID但不提交事务
            
            article_id = article.id
            session.commit()
            
            # 处理引用关系
            try:
                referenced_ids = self._extract_citation_references(content)
                self._create_article_relationships(article_id, referenced_ids)
            except Exception as e:
                # 引用关系处理失败不影响文章创建，但记录错误
                self.logger.error(f"处理文章引用关系失败: {str(e)}")
            
            return article_id
            
        except Exception as e:
            session.rollback()
            raise DatabaseOperationError(
                f"Failed to create article: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {"content_length": len(content), "author_id": author_id}
            )
    
    def update_article(self, article_id: int, content: str, title: str = None, summary: str = None) -> bool:
        """
        更新现有文章
        
        Args:
            article_id: 文章ID
            content: 新的文章内容
            title: 新的文章标题，如果未提供则保持原标题
            summary: 新的文章摘要，如果未提供则从内容生成
            
        Returns:
            更新是否成功
        """
        try:
            session = self.connection.get_session()
            
            # 查找文章
            article = session.query(Article).filter_by(id=article_id).first()
            if not article:
                raise DatabaseOperationError(
                    f"Article with ID {article_id} not found",
                    ERROR_CODES["DB_ARTICLE_NOT_FOUND"],
                    {"article_id": article_id}
                )
            
            # 更新内容
            article.content = content
            
            # 更新标题（如果提供了新标题）
            if title:
                article.title = title
            
            # 更新摘要（如果提供了新摘要，否则从内容生成）
            if summary:
                article.summary = summary
            else:
                article.summary = content[:50] + "..." if len(content) > 50 else content
            
            # 更新修改时间
            article.updated_at = datetime.utcnow()
            
            session.commit()
            
            # 处理引用关系
            try:
                # 清理旧的引用关系
                self._clean_article_relationships(article_id)
                # 创建新的引用关系
                referenced_ids = self._extract_citation_references(content)
                self._create_article_relationships(article_id, referenced_ids)
            except Exception as e:
                # 引用关系处理失败不影响文章更新，但记录错误
                self.logger.error(f"处理文章引用关系失败: {str(e)}")
            
            return True
            
        except DatabaseOperationError:
            session.rollback()
            raise
        except Exception as e:
            session.rollback()
            raise DatabaseOperationError(
                f"Failed to update article: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {"article_id": article_id, "content_length": len(content)}
            )
    
    def get_article_by_id(self, article_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID获取单篇文章的详细信息
        
        Args:
            article_id: 文章ID
            
        Returns:
            文章信息字典，如果不存在返回None
        """
        try:
            session = self.connection.get_session()
            article = session.query(Article).filter_by(id=article_id).first()
            
            if not article:
                return None
            
            return {
                "id": article.id,
                "title": article.title,
                "content": article.content or "",
                "summary": article.summary or "",
                "author_id": article.author_id,
                "status": article.status,
                "created_at": article.created_at.isoformat() if article.created_at else None,
                "updated_at": article.updated_at.isoformat() if article.updated_at else None,
                "finished_at": article.finished_at.isoformat() if article.finished_at else None
            }
            
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to get article: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {"article_id": article_id}
            )
    
    def _generate_title_from_content(self, content: str) -> str:
        """
        从内容生成标题
        
        Args:
            content: 文章内容
            
        Returns:
            生成的标题
        """
        # 移除markdown标记并取前30个字符作为标题
        import re
        
        # 移除markdown标记
        clean_content = re.sub(r'[#*`_\[\](){}]', '', content)
        clean_content = clean_content.strip()
        
        if not clean_content:
            return "未命名文章"
        
        # 取前30个字符作为标题
        title = clean_content[:30]
        if len(clean_content) > 30:
            title += "..."
        
        return title
    
    def _extract_citation_references(self, content: str) -> List[int]:
        """
        从文章内容中提取引用的文章ID
        
        Args:
            content: 文章内容
            
        Returns:
            被引用的文章ID列表
        """
        # 使用正则表达式匹配 [[cite:数字]] 格式
        citation_pattern = r'\[\[cite:(\d+)\]\]'
        matches = re.findall(citation_pattern, content)
        
        # 转换为整数并去重
        referenced_ids = list(set(int(match) for match in matches))
        
        self.logger.debug(f"从内容中提取到引用ID: {referenced_ids}")
        return referenced_ids
    
    def _create_article_relationships(self, citing_article_id: int, referenced_article_ids: List[int]) -> bool:
        """
        创建文章引用关系记录
        
        Args:
            citing_article_id: 引用文章的ID
            referenced_article_ids: 被引用文章的ID列表
            
        Returns:
            创建是否成功
        """
        if not referenced_article_ids:
            self.logger.debug("无引用关系需要创建")
            return True
        
        try:
            session = self.connection.get_session()
            
            # 过滤掉自引用（文章不能引用自己）
            valid_referenced_ids = [aid for aid in referenced_article_ids if aid != citing_article_id]
            self_refs = [aid for aid in referenced_article_ids if aid == citing_article_id]
            
            if self_refs:
                self.logger.warning(f"过滤掉自引用: 文章 {citing_article_id} 不能引用自己")
            
            if not valid_referenced_ids:
                self.logger.debug("过滤后无有效引用关系需要创建")
                return True
            
            # 验证被引用的文章是否存在
            existing_articles = session.query(Article).filter(
                Article.id.in_(valid_referenced_ids)
            ).all()
            existing_ids = {article.id for article in existing_articles}
            
            # 过滤掉不存在的文章ID
            final_referenced_ids = [aid for aid in valid_referenced_ids if aid in existing_ids]
            invalid_ids = set(valid_referenced_ids) - existing_ids
            
            if invalid_ids:
                self.logger.warning(f"引用的文章ID不存在: {invalid_ids}")
            
            # 创建引用关系记录
            created_count = 0
            for referenced_id in final_referenced_ids:
                # 检查是否已存在相同的引用关系
                existing_relationship = session.query(ArticleRelationship).filter_by(
                    citing_article_id=citing_article_id,
                    referenced_article_id=referenced_id
                ).first()
                
                if not existing_relationship:
                    relationship = ArticleRelationship(
                        citing_article_id=citing_article_id,
                        referenced_article_id=referenced_id
                    )
                    session.add(relationship)
                    created_count += 1
            
            session.commit()
            self.logger.debug(f"成功创建 {created_count} 个引用关系")
            return True
            
        except Exception as e:
            session.rollback()
            self.logger.error(f"创建引用关系失败: {str(e)}")
            raise DatabaseOperationError(
                f"Failed to create article relationships: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {
                    "citing_article_id": citing_article_id,
                    "referenced_article_ids": referenced_article_ids
                }
            )
    
    def _clean_article_relationships(self, citing_article_id: int) -> bool:
        """
        清理文章的旧引用关系（在更新文章时使用）
        
        Args:
            citing_article_id: 引用文章的ID
            
        Returns:
            清理是否成功
        """
        try:
            session = self.connection.get_session()
            
            # 删除该文章的所有引用关系
            deleted_count = session.query(ArticleRelationship).filter_by(
                citing_article_id=citing_article_id
            ).delete()
            
            session.commit()
            self.logger.debug(f"清理了 {deleted_count} 个旧引用关系")
            return True
            
        except Exception as e:
            session.rollback()
            raise DatabaseOperationError(
                f"Failed to clean article relationships: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {"citing_article_id": citing_article_id}
            )
    
    def batch_create_articles(self, articles_data: List[Dict[str, Any]], author_id: int) -> List[int]:
        """
        批量创建文章
        
        Args:
            articles_data: 文章数据列表，每个元素包含content和可选的title、summary
            author_id: 作者ID
            
        Returns:
            创建的文章ID列表
        """
        try:
            session = self.connection.get_session()
            created_ids = []
            
            for article_data in articles_data:
                content = article_data["content"]
                title = article_data.get("title") or self._generate_title_from_content(content)
                summary = article_data.get("summary") or (content[:50] + "..." if len(content) > 50 else content)
                
                article = Article(
                    author_id=author_id,
                    title=title,
                    summary=summary,
                    content=content,
                    status="published",
                    finished_at=datetime.utcnow(),
                    # 移除了source_task_id字段
                )
                
                session.add(article)
                session.flush()
                created_ids.append(article.id)
            
            session.commit()
            
            # 批量处理引用关系
            for i, article_data in enumerate(articles_data):
                try:
                    content = article_data["content"]
                    article_id = created_ids[i]
                    referenced_ids = self._extract_citation_references(content)
                    self._create_article_relationships(article_id, referenced_ids)
                except Exception as e:
                    # 引用关系处理失败不影响文章创建，但记录错误
                    self.logger.error(f"处理文章 {created_ids[i]} 引用关系失败: {str(e)}")
            
            return created_ids
            
        except Exception as e:
            session.rollback()
            raise DatabaseOperationError(
                f"Failed to batch create articles: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {"articles_count": len(articles_data), "author_id": author_id}
            )
    
    def batch_update_articles(self, updates: List[Dict[str, Any]]) -> List[bool]:
        """
        批量更新文章
        
        Args:
            updates: 更新数据列表，每个元素包含id, content和可选的title、summary
            
        Returns:
            更新结果列表
        """
        try:
            session = self.connection.get_session()
            results = []
            
            for update_data in updates:
                article_id = update_data["id"]
                content = update_data["content"]
                title = update_data.get("title")
                summary = update_data.get("summary")
                
                article = session.query(Article).filter_by(id=article_id).first()
                if not article:
                    results.append(False)
                    continue
                
                article.content = content
                if title:
                    article.title = title
                if summary:
                    article.summary = summary
                else:
                    article.summary = content[:50] + "..." if len(content) > 50 else content
                article.updated_at = datetime.utcnow()
                
                results.append(True)
            
            session.commit()
            
            # 批量处理引用关系
            for i, update_data in enumerate(updates):
                if results[i]:  # 只处理更新成功的文章
                    try:
                        article_id = update_data["id"]
                        content = update_data["content"]
                        
                        # 清理旧的引用关系
                        self._clean_article_relationships(article_id)
                        # 创建新的引用关系
                        referenced_ids = self._extract_citation_references(content)
                        self._create_article_relationships(article_id, referenced_ids)
                    except Exception as e:
                        # 引用关系处理失败不影响文章更新，但记录错误
                        self.logger.error(f"处理文章 {article_id} 引用关系失败: {str(e)}")
            
            return results
            
        except Exception as e:
            session.rollback()
            raise DatabaseOperationError(
                f"Failed to batch update articles: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {"updates_count": len(updates)}
            )