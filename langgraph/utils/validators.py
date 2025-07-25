"""
内容验证工具

用于验证输入数据和GPT返回结果的格式正确性
"""

import json
import re
from typing import List, Dict, Any, Optional
from .exceptions import ContentValidationError, ERROR_CODES


class ContentValidator:
    """内容验证器"""
    
    @staticmethod
    def validate_transcript_id(transcript_id: Any) -> int:
        """验证transcript_id格式"""
        if not isinstance(transcript_id, int) or transcript_id <= 0:
            raise ContentValidationError(
                "Invalid transcript_id: must be a positive integer",
                ERROR_CODES["CONTENT_VALIDATION_FAILED"]
            )
        return transcript_id
    
    @staticmethod
    def validate_article_ids(article_ids: Any) -> List[int]:
        """验证article_ids格式"""
        if not isinstance(article_ids, list):
            raise ContentValidationError(
                "Invalid article_ids: must be a list",
                ERROR_CODES["CONTENT_VALIDATION_FAILED"]
            )
        
        validated_ids = []
        for article_id in article_ids:
            if not isinstance(article_id, int) or article_id <= 0:
                raise ContentValidationError(
                    f"Invalid article_id: {article_id} must be a positive integer",
                    ERROR_CODES["CONTENT_VALIDATION_FAILED"]  
                )
            validated_ids.append(article_id)
        
        return validated_ids
    
    @staticmethod
    def validate_user_id(user_id: Any) -> int:
        """验证user_id格式"""
        if not isinstance(user_id, int) or user_id <= 0:
            raise ContentValidationError(
                "Invalid user_id: must be a positive integer",
                ERROR_CODES["CONTENT_VALIDATION_FAILED"]
            )
        return user_id
    
    @staticmethod
    def validate_gpt_response(response_text: str) -> List[Dict[str, Any]]:
        """验证GPT API返回的JSON格式"""
        if not response_text or not response_text.strip():
            raise ContentValidationError(
                "Empty GPT response",
                ERROR_CODES["INVALID_JSON_RESPONSE"]
            )
        
        # 尝试提取JSON部分（处理可能的前后缀文本）
        json_text = ContentValidator._extract_json_from_text(response_text)
        
        try:
            parsed_data = json.loads(json_text)
        except json.JSONDecodeError as e:
            raise ContentValidationError(
                f"Invalid JSON format in GPT response: {str(e)}",
                ERROR_CODES["INVALID_JSON_RESPONSE"],
                {"original_response": response_text}
            )
        
        # 验证数据结构
        if not isinstance(parsed_data, list):
            raise ContentValidationError(
                "GPT response must be a JSON array",
                ERROR_CODES["INVALID_JSON_RESPONSE"],
                {"parsed_data": parsed_data}
            )
        
        # 验证每个元素的格式
        for i, item in enumerate(parsed_data):
            if not isinstance(item, dict):
                raise ContentValidationError(
                    f"Item {i} in GPT response must be an object",
                    ERROR_CODES["INVALID_JSON_RESPONSE"]
                )
            
            required_fields = ["id", "title", "summary", "content"]
            missing_fields = [field for field in required_fields if field not in item]
            if missing_fields:
                raise ContentValidationError(
                    f"Item {i} missing required fields: {missing_fields}",
                    ERROR_CODES["MISSING_REQUIRED_FIELDS"]
                )
            
            # 验证id字段
            item_id = item["id"]
            if not (isinstance(item_id, str) or isinstance(item_id, int)):
                raise ContentValidationError(
                    f"Item {i} id must be string or integer",
                    ERROR_CODES["INVALID_ARTICLE_FORMAT"]
                )
            
            # 如果id是数字字符串，转换为整数
            if isinstance(item_id, str) and item_id.isdigit():
                item["id"] = int(item_id)
            elif isinstance(item_id, str) and item_id != "new":
                raise ContentValidationError(
                    f"Item {i} invalid id format: must be 'new' or numeric",
                    ERROR_CODES["INVALID_ARTICLE_FORMAT"]
                )
            
            # 验证title字段
            if not isinstance(item["title"], str) or not item["title"].strip():
                raise ContentValidationError(
                    f"Item {i} title must be non-empty string",
                    ERROR_CODES["INVALID_ARTICLE_FORMAT"]
                )
            
            # 验证summary字段
            if not isinstance(item["summary"], str) or not item["summary"].strip():
                raise ContentValidationError(
                    f"Item {i} summary must be non-empty string",
                    ERROR_CODES["INVALID_ARTICLE_FORMAT"]
                )
            
            # 验证content字段
            if not isinstance(item["content"], str) or not item["content"].strip():
                raise ContentValidationError(
                    f"Item {i} content must be non-empty string",
                    ERROR_CODES["INVALID_ARTICLE_FORMAT"]
                )
        
        return parsed_data
    
    @staticmethod
    def _extract_json_from_text(text: str) -> str:
        """从文本中提取JSON部分"""
        # 移除可能的markdown代码块标记
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*$', '', text)
        
        # 寻找JSON数组的开始和结束
        start_idx = text.find('[')
        end_idx = text.rfind(']')
        
        if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
            # 如果没找到数组，尝试寻找对象
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx == -1 or end_idx == -1 or start_idx >= end_idx:
                # 仍然没找到，返回原文本
                return text.strip()
        
        return text[start_idx:end_idx + 1].strip()
    
    @staticmethod
    def validate_article_content(content: str) -> str:
        """验证文章内容格式"""
        if not isinstance(content, str):
            raise ContentValidationError(
                "Article content must be a string",
                ERROR_CODES["INVALID_ARTICLE_FORMAT"]
            )
        
        content = content.strip()
        if not content:
            raise ContentValidationError(
                "Article content cannot be empty",
                ERROR_CODES["INVALID_ARTICLE_FORMAT"]
            )
        
        # 检查内容长度（避免过长或过短）
        if len(content) < 10:
            raise ContentValidationError(
                "Article content too short (minimum 10 characters)",
                ERROR_CODES["INVALID_ARTICLE_FORMAT"]
            )
        
        if len(content) > 50000:  # 50KB limit
            raise ContentValidationError(
                "Article content too long (maximum 50,000 characters)",
                ERROR_CODES["INVALID_ARTICLE_FORMAT"]
            )
        
        return content