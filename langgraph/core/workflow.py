"""
LangGraph核心工作流

实现文章内容分析和处理的核心逻辑
"""

import json
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI

from ..config.gpt_models import GPTModelConfig
from ..utils.exceptions import GPTAPIError, ERROR_CODES
from ..utils.logger import get_logger
from .prompts import PromptManager
from .processors import ContentProcessor


class LangGraphWorkflow:
    """LangGraph核心工作流类"""
    
    def __init__(self, gpt_config: GPTModelConfig, model_name: str = "default"):
        """
        初始化工作流
        
        Args:
            gpt_config: GPT模型配置
            model_name: 使用的模型配置名称
        """
        self.gpt_config = gpt_config
        self.model_name = model_name
        self.prompt_manager = PromptManager()
        self.content_processor = ContentProcessor()
        self.logger = get_logger()
        
        # 初始化OpenAI客户端
        self._init_openai_client()
    
    def _init_openai_client(self):
        """初始化OpenAI客户端"""
        try:
            model_config = self.gpt_config.get_model(self.model_name)
            
            self.client = OpenAI(
                api_key=model_config["api_key"],
                base_url=model_config["url"]
            )
            
            self.model_name_api = model_config["model_name"]
            
        except Exception as e:
            raise GPTAPIError(
                f"Failed to initialize OpenAI client: {str(e)}",
                ERROR_CODES["GPT_API_INVALID_REQUEST"]
            )
    
    def analyze_content_with_articles(
        self, 
        new_text: str, 
        existing_articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        分析新文本与现有文章的关系
        
        Args:
            new_text: 新的文本内容
            existing_articles: 现有文章列表，每个元素包含id和content字段
            
        Returns:
            需要更新或创建的文章列表
        """
        # 预处理输入
        processed_text = self.content_processor.preprocess_transcript(new_text)
        processed_articles = self._preprocess_articles(existing_articles)
        
        # 验证输入
        if not self.prompt_manager.validate_prompt_inputs(processed_text, processed_articles):
            raise GPTAPIError(
                "Invalid input for content analysis",
                ERROR_CODES["GPT_API_INVALID_REQUEST"]
            )
        
        # 创建prompt
        messages = self.prompt_manager.create_chat_messages(processed_text, processed_articles)
        
        # 调用GPT API
        response_text = self._call_gpt_api(messages)
        
        # 后处理响应
        result = self.content_processor.postprocess_gpt_response(response_text)
        
        return result
    
    def _preprocess_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        预处理文章列表
        
        Args:
            articles: 原始文章列表
            
        Returns:
            处理后的文章列表
        """
        processed_articles = []
        
        for article in articles:
            processed_article = {
                "id": article["id"],
                "content": self.content_processor.preprocess_article_content(article["content"])
            }
            processed_articles.append(processed_article)
        
        return processed_articles
    
    def _call_gpt_api(self, messages: List[Dict[str, str]]) -> str:
        """
        调用GPT API
        
        Args:
            messages: 消息列表
            
        Returns:
            GPT响应文本
        """
        max_retries = self.gpt_config.get_setting("max_retries", 3)
        timeout = self.gpt_config.get_setting("timeout", 30)
        temperature = self.gpt_config.get_setting("temperature", 0.1)
        max_tokens = self.gpt_config.get_setting("max_tokens", 4000)
        
        self.logger.debug(f"调用GPT API - 模型: {self.model_name_api}")
        self.logger.debug(f"API参数 - 温度: {temperature}, 最大token: {max_tokens}, 超时: {timeout}s")
        
        for attempt in range(max_retries):
            try:
                start_time = time.time()
                
                # 记录请求日志
                self.logger.log_request(
                    url=str(self.client.base_url),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                    data={"model": self.model_name_api, "messages": len(messages)}  # 只记录消息数量，避免过长
                )
                
                response = self.client.chat.completions.create(
                    model=self.model_name_api,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout
                )
                
                response_time = time.time() - start_time
                
                if not response.choices:
                    self.logger.error("GPT API返回空响应")
                    raise GPTAPIError(
                        "Empty response from GPT API",
                        ERROR_CODES["GPT_API_SERVER_ERROR"]
                    )
                
                response_content = response.choices[0].message.content
                
                # 记录响应日志
                self.logger.log_response(200, response_content, response_time)
                
                # 记录GPT分析详细信息
                prompt_text = "\n".join([msg["content"] for msg in messages])
                self.logger.log_gpt_analysis(
                    prompt=prompt_text,
                    response=response_content,
                    model=self.model_name_api,
                    tokens_used=getattr(response.usage, 'total_tokens', None) if hasattr(response, 'usage') else None
                )
                
                self.logger.debug(f"GPT API调用成功 - 耗时: {response_time:.2f}s")
                return response_content
                
            except Exception as e:
                self.logger.warning(f"GPT API调用失败 (尝试 {attempt + 1}/{max_retries}): {str(e)}")
                
                if attempt == max_retries - 1:
                    # 最后一次重试失败
                    self.logger.error(f"GPT API调用最终失败: {str(e)}")
                    self._handle_api_error(e)
                else:
                    # 等待后重试
                    wait_time = 2 ** attempt
                    self.logger.debug(f"等待 {wait_time}s 后重试")
                    time.sleep(wait_time)  # 指数退避
                    continue
    
    def _handle_api_error(self, error: Exception):
        """
        处理API错误
        
        Args:
            error: 捕获的异常
        """
        error_message = str(error).lower()
        
        if "timeout" in error_message:
            raise GPTAPIError(
                "GPT API timeout",
                ERROR_CODES["GPT_API_TIMEOUT"],
                {"original_error": str(error)}
            )
        elif "quota" in error_message or "rate limit" in error_message:
            raise GPTAPIError(
                "GPT API quota exceeded or rate limited",
                ERROR_CODES["GPT_API_QUOTA_EXCEEDED"],
                {"original_error": str(error)}
            )
        elif "unauthorized" in error_message or "401" in error_message:
            raise GPTAPIError(
                "GPT API unauthorized - check API key",
                ERROR_CODES["GPT_API_UNAUTHORIZED"],
                {"original_error": str(error)}
            )
        else:
            raise GPTAPIError(
                f"GPT API error: {str(error)}",
                ERROR_CODES["GPT_API_SERVER_ERROR"],
                {"original_error": str(error)}
            )
    
    def batch_analyze_transcripts(
        self, 
        transcripts_with_articles: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        批量分析多个转录文本
        
        Args:
            transcripts_with_articles: 转录文本和相关文章的列表
                格式: [{"transcript": "text", "articles": [{"id": 1, "content": "..."}]}]
                
        Returns:
            批量分析结果列表
        """
        results = []
        
        for i, item in enumerate(transcripts_with_articles):
            try:
                transcript = item["transcript"]
                articles = item["articles"]
                
                result = self.analyze_content_with_articles(transcript, articles)
                
                results.append({
                    "index": i,
                    "success": True,
                    "result": result,
                    "error": None
                })
                
            except Exception as e:
                results.append({
                    "index": i,
                    "success": False,
                    "result": None,
                    "error": str(e)
                })
        
        return results
    
    def validate_analysis_result(self, result: List[Dict[str, Any]]) -> bool:
        """
        验证分析结果的有效性
        
        Args:
            result: 分析结果
            
        Returns:
            结果是否有效
        """
        if not isinstance(result, list):
            return False
        
        for item in result:
            if not isinstance(item, dict):
                return False
            
            if not all(field in item for field in ["id", "title", "summary", "content"]):
                return False
            
            # 验证id格式
            item_id = item["id"]
            if not (isinstance(item_id, (int, str))):
                return False
            
            if isinstance(item_id, str) and item_id != "new":
                return False
            
            # 验证content格式
            if not isinstance(item["content"], str) or not item["content"].strip():
                return False
        
        return True
    
    def get_processing_statistics(self, result: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        获取处理统计信息
        
        Args:
            result: 分析结果
            
        Returns:
            统计信息字典
        """
        stats = {
            "total_items": len(result),
            "new_articles": 0,
            "updated_articles": 0,
            "total_content_length": 0
        }
        
        for item in result:
            if item["id"] == "new":
                stats["new_articles"] += 1
            else:
                stats["updated_articles"] += 1
            
            stats["total_content_length"] += len(item["content"])
        
        return stats
    
    def create_processing_summary(
        self, 
        new_text: str, 
        existing_articles: List[Dict[str, Any]], 
        result: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        创建处理摘要
        
        Args:
            new_text: 输入的新文本
            existing_articles: 现有文章列表
            result: 处理结果
            
        Returns:
            处理摘要字典
        """
        stats = self.get_processing_statistics(result)
        
        summary = {
            "input": {
                "new_text_length": len(new_text),
                "existing_articles_count": len(existing_articles),
                "total_existing_content_length": sum(len(art["content"]) for art in existing_articles)
            },
            "output": {
                "items_count": stats["total_items"],
                "new_articles_count": stats["new_articles"],
                "updated_articles_count": stats["updated_articles"],
                "total_output_length": stats["total_content_length"]
            },
            "processing": {
                "model_used": self.model_name,
                "timestamp": time.time()
            }
        }
        
        return summary