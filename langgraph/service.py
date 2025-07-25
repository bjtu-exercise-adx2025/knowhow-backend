"""
LangGraph主服务接口

提供文章处理服务的主要入口点
"""

import os
from typing import List, Dict, Any, Optional

from .config.gpt_models import GPTModelConfig
from .database.operations import DatabaseOperations
from .core.workflow import LangGraphWorkflow
from .utils.exceptions import (
    LangGraphException, 
    DatabaseOperationError, 
    GPTAPIError, 
    ConfigurationError,
    ERROR_CODES
)
from .utils.validators import ContentValidator
from .utils.logger import get_logger, set_debug_config


class ArticleProcessorService:
    """文章处理服务主入口类"""
    
    def __init__(self, config_path: Optional[str] = None, model_name: str = "default"):
        """
        初始化服务
        
        Args:
            config_path: GPT模型配置文件路径，如果为None则使用同目录下的config.json
            model_name: 使用的模型配置名称
        """
        self.validator = ContentValidator()
        
        # 如果没有指定配置路径，使用同目录下的config.json
        if config_path is None:
            config_path = os.path.join(os.path.dirname(__file__), "config.json")
        
        # 初始化配置
        try:
            self.gpt_config = GPTModelConfig(config_path)
            self.model_name = model_name
            
            # 初始化debug日志
            debug_config = self.gpt_config.get_debug_config()
            set_debug_config(debug_config)
            self.logger = get_logger()
        except Exception as e:
            raise ConfigurationError(
                f"Failed to initialize configuration: {str(e)}",
                ERROR_CODES["INVALID_CONFIG_FILE"]
            )
        
        # 初始化数据库操作
        try:
            self.db_ops = DatabaseOperations()
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to initialize database operations: {str(e)}",
                ERROR_CODES["DB_CONNECTION_FAILED"]
            )
        
        # 初始化工作流
        try:
            self.workflow = LangGraphWorkflow(self.gpt_config, self.model_name)
        except Exception as e:
            raise GPTAPIError(
                f"Failed to initialize workflow: {str(e)}",
                ERROR_CODES["GPT_API_INVALID_REQUEST"]
            )
    
    def process_transcript_with_articles(
        self, 
        transcript_id: int, 
        article_ids: List[int],
        user_id: int = 2  # TODO: 改为动态用户ID
    ) -> Dict[str, Any]:
        """
        处理语音转录文本与相关文章
        
        Args:
            transcript_id: 语音转录记录ID
            article_ids: 相关文章ID列表
            user_id: 用户ID（暂时固定为2）
            
        Returns:
            处理结果字典，包含成功状态和详细信息
        """
        self.logger.create_section_separator("开始处理转录文本与文章")
        self.logger.info(f"处理请求 - 转录ID: {transcript_id}, 文章IDs: {article_ids}, 用户ID: {user_id}")
        
        try:
            # 验证输入参数
            self.logger.debug("验证输入参数")
            transcript_id = self.validator.validate_transcript_id(transcript_id)
            article_ids = self.validator.validate_article_ids(article_ids)
            user_id = self.validator.validate_user_id(user_id)
            self.logger.debug("输入参数验证通过")
            
            # 从数据库获取数据
            transcript_text = self._get_transcript_text(transcript_id)
            existing_articles = self._get_existing_articles(article_ids)
            
            # 使用LangGraph分析内容
            analysis_result = self._analyze_content(transcript_text, existing_articles)
            
            # 处理分析结果并更新数据库
            processing_result = self._process_analysis_result(analysis_result, user_id)
            
            # 生成成功响应
            return self._create_success_response(processing_result, analysis_result)
            
        except LangGraphException as e:
            # 已知的模块异常
            return self._create_error_response(e)
        except Exception as e:
            # 未知异常
            unknown_error = LangGraphException(
                f"Unexpected error: {str(e)}",
                ERROR_CODES["UNKNOWN_ERROR"],
                {"original_error": str(e)}
            )
            return self._create_error_response(unknown_error)
    
    def _get_transcript_text(self, transcript_id: int) -> str:
        """获取转录文本"""
        self.logger.debug(f"获取转录文本 - ID: {transcript_id}")
        transcript_text = self.db_ops.get_transcript_by_id(transcript_id)
        
        if not transcript_text or not transcript_text.strip():
            self.logger.error(f"转录文本为空或不存在 - ID: {transcript_id}")
            raise DatabaseOperationError(
                f"Transcript {transcript_id} is empty or contains no text",
                ERROR_CODES["DB_TRANSCRIPT_NOT_FOUND"]
            )
        
        self.logger.debug(f"成功获取转录文本 - 长度: {len(transcript_text)} 字符")
        return transcript_text
    
    def _get_existing_articles(self, article_ids: List[int]) -> List[Dict[str, Any]]:
        """获取现有文章"""
        if not article_ids:
            self.logger.debug("无相关文章ID，返回空列表")
            return []
        
        self.logger.debug(f"获取现有文章 - IDs: {article_ids}")
        articles = self.db_ops.get_articles_by_ids(article_ids)
        self.logger.debug(f"成功获取 {len(articles)} 篇文章")
        
        return articles
    
    def _analyze_content(self, transcript_text: str, existing_articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """分析内容"""
        self.logger.debug("开始GPT内容分析")
        self.logger.debug(f"输入文本长度: {len(transcript_text)}, 相关文章数: {len(existing_articles)}")
        
        analysis_result = self.workflow.analyze_content_with_articles(
            transcript_text, 
            existing_articles
        )
        
        # 验证分析结果
        if not self.workflow.validate_analysis_result(analysis_result):
            self.logger.error("GPT分析结果格式无效")
            raise GPTAPIError(
                "Invalid analysis result from workflow",
                ERROR_CODES["INVALID_JSON_RESPONSE"]
            )
        
        self.logger.debug(f"GPT分析完成 - 返回 {len(analysis_result)} 个处理项")
        return analysis_result
    
    def _process_analysis_result(self, analysis_result: List[Dict[str, Any]], user_id: int) -> Dict[str, Any]:
        """处理分析结果并更新数据库"""
        result = {
            "created_articles": [],
            "updated_articles": [],
            "created_count": 0,
            "updated_count": 0,
            "total_processed": 0
        }
        
        for item in analysis_result:
            item_id = item["id"]
            content = item["content"]
            title = item["title"]
            summary = item["summary"]
            
            try:
                if item_id == "new":
                    # 创建新文章，使用AI生成的title和summary
                    article_id = self.db_ops.create_article(content, user_id, title, summary)
                    
                    # 记录引用信息
                    citations = self.db_ops._extract_citation_references(content)
                    self.logger.debug(f"新文章 {article_id} 包含引用: {citations}")
                    
                    result["created_articles"].append({
                        "new_id": article_id,
                        "title": title,
                        "summary": summary,
                        "content_length": len(content),
                        "citations": citations
                    })
                    result["created_count"] += 1
                else:
                    # 更新现有文章，使用AI生成的title和summary
                    success = self.db_ops.update_article(int(item_id), content, title, summary)
                    if success:
                        # 记录引用信息
                        citations = self.db_ops._extract_citation_references(content)
                        self.logger.debug(f"更新文章 {item_id} 包含引用: {citations}")
                        
                        result["updated_articles"].append({
                            "id": int(item_id),
                            "title": title,
                            "summary": summary,
                            "content_length": len(content),
                            "citations": citations
                        })
                        result["updated_count"] += 1
                    else:
                        # 更新失败，记录错误但不中断整个流程
                        continue
                
                result["total_processed"] += 1
                
            except Exception as e:
                # 记录单个项目的处理错误，但继续处理其他项目
                continue
        
        return result
    
    def _create_success_response(self, processing_result: Dict[str, Any], analysis_result: List[Dict[str, Any]]) -> Dict[str, Any]:
        """创建成功响应"""
        return {
            "success": True,
            "message": "Content processing completed successfully",
            "data": {
                "created_count": processing_result["created_count"],
                "updated_count": processing_result["updated_count"],
                "total_processed": processing_result["total_processed"],
                "created_articles": processing_result["created_articles"],
                "updated_articles": processing_result["updated_articles"],
                "analysis_items_count": len(analysis_result)
            },
            "error_code": None,
            "error_message": None
        }
    
    def _create_error_response(self, exception: LangGraphException) -> Dict[str, Any]:
        """创建错误响应"""
        return {
            "success": False,
            "message": "Content processing failed",
            "data": None,
            "error_code": exception.error_code,
            "error_message": exception.message,
            "details": exception.details
        }
    
    def batch_process_transcripts(
        self, 
        transcript_article_pairs: List[Dict[str, Any]], 
        user_id: int = 2
    ) -> Dict[str, Any]:
        """
        批量处理多个转录文本和文章对
        
        Args:
            transcript_article_pairs: 转录文本和文章ID对列表
                格式: [{"transcript_id": 1, "article_ids": [1, 2, 3]}]
            user_id: 用户ID
            
        Returns:
            批量处理结果
        """
        try:
            user_id = self.validator.validate_user_id(user_id)
            
            results = []
            overall_stats = {
                "total_pairs": len(transcript_article_pairs),
                "successful_pairs": 0,
                "failed_pairs": 0,
                "total_created": 0,
                "total_updated": 0
            }
            
            for i, pair in enumerate(transcript_article_pairs):
                try:
                    transcript_id = pair["transcript_id"]
                    article_ids = pair["article_ids"]
                    
                    result = self.process_transcript_with_articles(
                        transcript_id, article_ids, user_id
                    )
                    
                    results.append({
                        "index": i,
                        "transcript_id": transcript_id,
                        "article_ids": article_ids,
                        "result": result
                    })
                    
                    if result["success"]:
                        overall_stats["successful_pairs"] += 1
                        overall_stats["total_created"] += result["data"]["created_count"]
                        overall_stats["total_updated"] += result["data"]["updated_count"]
                    else:
                        overall_stats["failed_pairs"] += 1
                        
                except Exception as e:
                    results.append({
                        "index": i,
                        "transcript_id": pair.get("transcript_id"),
                        "article_ids": pair.get("article_ids"),
                        "result": {
                            "success": False,
                            "error_message": str(e)
                        }
                    })
                    overall_stats["failed_pairs"] += 1
            
            return {
                "success": True,
                "message": "Batch processing completed",
                "overall_stats": overall_stats,
                "individual_results": results
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Batch processing failed: {str(e)}",
                "error_code": ERROR_CODES["PROCESSING_FAILED"]
            }
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        获取服务状态
        
        Returns:
            服务状态信息
        """
        try:
            # 测试数据库连接
            db_status = "connected"
            try:
                self.db_ops.connection.test_connection()
            except Exception:
                db_status = "disconnected"
            
            # 测试GPT配置
            gpt_status = "configured"
            try:
                self.gpt_config.validate_model_config(self.model_name)
            except Exception:
                gpt_status = "misconfigured"
            
            return {
                "service": "ArticleProcessorService",
                "status": "running",
                "database": {
                    "status": db_status
                },
                "gpt_model": {
                    "name": self.model_name,
                    "status": gpt_status,
                    "available_models": self.gpt_config.list_models()
                },
                "version": "1.0.0"
            }
            
        except Exception as e:
            return {
                "service": "ArticleProcessorService",
                "status": "error",
                "error_message": str(e)
            }
    
    def update_model_config(self, model_name: str, url: str, api_key: str, model_api_name: str) -> Dict[str, Any]:
        """
        更新模型配置
        
        Args:
            model_name: 模型配置名称
            url: API端点URL
            api_key: API密钥
            model_api_name: API中的模型名称
            
        Returns:
            更新结果
        """
        try:
            self.gpt_config.add_model(model_name, url, api_key, model_api_name)
            
            return {
                "success": True,
                "message": f"Model configuration '{model_name}' updated successfully"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Failed to update model configuration: {str(e)}",
                "error_code": ERROR_CODES["INVALID_MODEL_CONFIG"]
            }