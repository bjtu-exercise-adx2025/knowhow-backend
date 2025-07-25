"""
LangGraph模块异常定义

定义了模块中使用的所有自定义异常类和错误码
"""

from typing import Dict, Any


class LangGraphException(Exception):
    """LangGraph模块基础异常类"""
    
    def __init__(self, message: str, error_code: int = None, details: Dict[str, Any] = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于API返回"""
        return {
            "error_message": self.message,
            "error_code": self.error_code,
            "details": self.details
        }


class DatabaseOperationError(LangGraphException):
    """数据库操作异常"""
    pass


class GPTAPIError(LangGraphException):
    """GPT API调用异常"""
    pass


class ContentValidationError(LangGraphException):
    """内容验证异常"""
    pass


class ConfigurationError(LangGraphException):
    """配置错误异常"""
    pass


# 错误码定义
ERROR_CODES = {
    # 数据库相关错误 (1000-1999)
    "DB_TRANSCRIPT_NOT_FOUND": 1001,
    "DB_ARTICLE_NOT_FOUND": 1002,
    "DB_OPERATION_FAILED": 1003,
    "DB_CONNECTION_FAILED": 1004,
    "DB_TRANSACTION_FAILED": 1005,
    
    # GPT API相关错误 (2000-2999)
    "GPT_API_TIMEOUT": 2001,
    "GPT_API_QUOTA_EXCEEDED": 2002,
    "GPT_API_UNAUTHORIZED": 2003,
    "GPT_API_INVALID_REQUEST": 2004,
    "GPT_API_SERVER_ERROR": 2005,
    
    # 内容验证相关错误 (3000-3999)
    "INVALID_JSON_RESPONSE": 3001,
    "CONTENT_VALIDATION_FAILED": 3002,
    "INVALID_ARTICLE_FORMAT": 3003,
    "MISSING_REQUIRED_FIELDS": 3004,
    
    # 配置相关错误 (4000-4999)
    "INVALID_MODEL_CONFIG": 4001,
    "MISSING_API_KEY": 4002,
    "INVALID_CONFIG_FILE": 4003,
    
    # 通用错误 (9000+)
    "UNKNOWN_ERROR": 9001,
    "PROCESSING_FAILED": 9002,
}