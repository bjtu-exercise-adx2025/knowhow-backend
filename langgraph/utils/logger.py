"""
LangGraph模块专用日志管理器

提供灵活的日志配置和输出功能，支持debug模式
"""

import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import json


class LangGraphLogger:
    """LangGraph专用日志管理器"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        初始化日志管理器
        
        Args:
            config: debug配置字典
        """
        self.config = config
        self.logger = logging.getLogger('langgraph')
        self._setup_logger()
    
    def _setup_logger(self):
        """设置日志器"""
        # 清除已有的handlers
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # 设置日志级别
        log_level = getattr(logging, self.config.get('log_level', 'INFO').upper())
        self.logger.setLevel(log_level)
        
        # 防止日志传播到父记录器，避免重复打印
        self.logger.propagate = False
        
        # 创建formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s'
        )
        
        # 添加控制台输出
        if self.config.get('log_to_console', True):
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        # 添加文件输出
        if self.config.get('log_to_file', False):
            log_file = self.config.get('log_file', 'langgraph_debug.log')
            
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, exist_ok=True)
            
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
    
    def is_debug_enabled(self) -> bool:
        """检查是否启用debug模式"""
        return self.config.get('enabled', False)
    
    def debug(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """输出debug级别日志"""
        if not self.is_debug_enabled():
            return
        
        if extra_data:
            message += f" | Extra: {json.dumps(extra_data, ensure_ascii=False, indent=2)}"
        
        self.logger.debug(message)
    
    def info(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """输出info级别日志"""
        if not self.is_debug_enabled():
            return
        
        if extra_data:
            message += f" | Extra: {json.dumps(extra_data, ensure_ascii=False, indent=2)}"
        
        self.logger.info(message)
    
    def warning(self, message: str, extra_data: Optional[Dict[str, Any]] = None):
        """输出warning级别日志"""
        if not self.is_debug_enabled():
            return
        
        if extra_data:
            message += f" | Extra: {json.dumps(extra_data, ensure_ascii=False, indent=2)}"
        
        self.logger.warning(message)
    
    def error(self, message: str, extra_data: Optional[Dict[str, Any]] = None, exc_info: bool = False):
        """输出error级别日志"""
        if not self.is_debug_enabled():
            return
        
        if extra_data:
            message += f" | Extra: {json.dumps(extra_data, ensure_ascii=False, indent=2)}"
        
        self.logger.error(message, exc_info=exc_info)
    
    def log_request(self, url: str, method: str, headers: Dict[str, Any], data: Any):
        """记录API请求日志"""
        if not self.config.get('log_requests', False):
            return
        
        request_data = {
            "url": url,
            "method": method,
            "headers": {k: v for k, v in headers.items() if 'authorization' not in k.lower()},  # 隐藏API密钥
            "data_size": len(str(data)) if data else 0,
            "timestamp": datetime.now().isoformat()
        }
        
        self.debug(f"API Request: {method} {url}", request_data)
    
    def log_response(self, status_code: int, response_data: Any, response_time: float):
        """记录API响应日志"""
        if not self.config.get('log_responses', False):
            return
        
        response_info = {
            "status_code": status_code,
            "response_size": len(str(response_data)) if response_data else 0,
            "response_time_ms": round(response_time * 1000, 2),
            "timestamp": datetime.now().isoformat()
        }
        
        # 如果响应数据太长，只记录前500个字符
        if response_data and len(str(response_data)) > 500:
            response_info["response_preview"] = str(response_data)[:500] + "..."
        else:
            response_info["response_data"] = response_data
        
        self.debug(f"API Response: {status_code}", response_info)
    
    def log_database_query(self, operation: str, table: str, conditions: Optional[Dict[str, Any]] = None, 
                          result_count: Optional[int] = None):
        """记录数据库查询日志"""
        if not self.config.get('log_database_queries', False):
            return
        
        query_info = {
            "operation": operation,
            "table": table,
            "conditions": conditions,
            "result_count": result_count,
            "timestamp": datetime.now().isoformat()
        }
        
        self.debug(f"Database Query: {operation} on {table}", query_info)
    
    def log_processing_step(self, step: str, input_data: Any, output_data: Any, 
                           processing_time: Optional[float] = None):
        """记录处理步骤日志"""
        if not self.config.get('log_processing_steps', False):
            return
        
        step_info = {
            "step": step,
            "input_size": len(str(input_data)) if input_data else 0,
            "output_size": len(str(output_data)) if output_data else 0,
            "processing_time_ms": round(processing_time * 1000, 2) if processing_time else None,
            "timestamp": datetime.now().isoformat()
        }
        
        # 对于大数据，只记录摘要
        if input_data and len(str(input_data)) > 200:
            step_info["input_preview"] = str(input_data)[:200] + "..."
        else:
            step_info["input_data"] = input_data
        
        if output_data and len(str(output_data)) > 200:
            step_info["output_preview"] = str(output_data)[:200] + "..."
        else:
            step_info["output_data"] = output_data
        
        self.debug(f"Processing Step: {step}", step_info)
    
    def log_gpt_analysis(self, prompt: str, response: str, model: str, 
                        tokens_used: Optional[int] = None, cost: Optional[float] = None):
        """记录GPT分析详细日志"""
        if not self.is_debug_enabled():
            return
        
        analysis_info = {
            "model": model,
            "prompt_length": len(prompt),
            "response_length": len(response),
            "tokens_used": tokens_used,
            "estimated_cost": cost,
            "timestamp": datetime.now().isoformat()
        }
        
        # 记录prompt和response的前200个字符

        analysis_info["prompt"] = prompt
        
        if len(response) > 200:  
            analysis_info["response_preview"] = response[:200] + "..."
        else:
            analysis_info["response"] = response
        
        self.debug("GPT Analysis Complete", analysis_info)
    
    def create_section_separator(self, title: str):
        """创建日志分段分隔符"""
        if not self.is_debug_enabled():
            return
        
        separator = "=" * 50
        self.debug(f"\n{separator}")
        self.debug(f"  {title}")
        self.debug(f"{separator}")
    
    def flush_logs(self):
        """刷新所有日志输出"""
        for handler in self.logger.handlers:
            handler.flush()


# 全局日志管理器实例
_global_logger: Optional[LangGraphLogger] = None


def get_logger(config: Optional[Dict[str, Any]] = None) -> LangGraphLogger:
    """
    获取全局日志管理器实例
    
    Args:
        config: debug配置，如果为None则使用默认配置
        
    Returns:
        LangGraphLogger实例
    """
    global _global_logger
    
    if _global_logger is None or config is not None:
        if config is None:
            # 默认配置
            config = {
                "enabled": False,
                "log_level": "INFO",
                "log_to_console": True,
                "log_to_file": False
            }
        
        _global_logger = LangGraphLogger(config)
    
    return _global_logger


def set_debug_config(config: Dict[str, Any]):
    """
    设置debug配置
    
    Args:
        config: debug配置字典
    """
    global _global_logger
    _global_logger = LangGraphLogger(config)