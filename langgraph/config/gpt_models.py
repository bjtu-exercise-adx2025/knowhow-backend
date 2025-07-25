"""
GPT模型配置管理

提供灵活的GPT模型配置管理，支持多个模型和自定义参数
"""

import json
import os
from typing import Any, Dict, Optional

from ..utils.exceptions import ERROR_CODES, ConfigurationError


class GPTModelConfig:
    """GPT模型配置管理器"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径，如果为None则使用默认配置
        """
        self.models: Dict[str, Dict[str, Any]] = {}
        self.settings: Dict[str, Any] = {}

        # 设置默认配置
        self._load_default_config()

        # 如果提供了配置文件路径，加载配置文件
        if config_path:
            self.load_config(config_path)

    def _load_default_config(self):
        """加载默认配置"""
        self.models = {
            "default": {
                "url": "https://api.openai.com/v1/chat/completions",
                "api_key": "",  # 需要在使用前设置
                "model_name": "gpt-3.5-turbo",
            },
            "qwen": {
                "url": "http://localhost:8000/v1/chat/completions",  # 本地qwen服务
                "api_key": "dummy_key",
                "model_name": "qwen-turbo",
            },
        }

        self.settings = {
            "timeout": 200,
            "max_retries": 3,
            "temperature": 0.1,
            "max_tokens": 4000,
        }

        self.debug_config = {
            "enabled": False,
            "log_level": "INFO",
            "log_to_file": False,
            "log_file": "langgraph_debug.log",
            "log_to_console": True,
            "log_requests": False,
            "log_responses": False,
            "log_database_queries": False,
            "log_processing_steps": False,
        }

    def load_config(self, config_path: str):
        """
        从JSON文件加载配置

        Args:
            config_path: 配置文件路径
        """
        if not os.path.exists(config_path):
            raise ConfigurationError(
                f"Configuration file not found: {config_path}",
                ERROR_CODES["INVALID_CONFIG_FILE"],
            )

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 更新模型配置
            if "models" in config:
                self.models.update(config["models"])

            # 更新设置
            if "settings" in config:
                self.settings.update(config["settings"])

            # 更新debug配置
            if "debug" in config:
                self.debug_config.update(config["debug"])

        except json.JSONDecodeError as e:
            raise ConfigurationError(
                f"Invalid JSON in configuration file: {str(e)}",
                ERROR_CODES["INVALID_CONFIG_FILE"],
            )
        except Exception as e:
            raise ConfigurationError(
                f"Error loading configuration: {str(e)}",
                ERROR_CODES["INVALID_CONFIG_FILE"],
            )

    def add_model(self, name: str, url: str, api_key: str, model_name: str):
        """
        添加新的模型配置

        Args:
            name: 模型配置名称
            url: API端点URL
            api_key: API密钥
            model_name: 模型名称
        """
        if not all([name, url, api_key, model_name]):
            raise ConfigurationError(
                "All model configuration parameters are required",
                ERROR_CODES["INVALID_MODEL_CONFIG"],
            )

        self.models[name] = {"url": url, "api_key": api_key, "model_name": model_name}

    def get_model(self, name: str = "default") -> Dict[str, str]:
        """
        获取指定模型配置

        Args:
            name: 模型配置名称

        Returns:
            模型配置字典
        """
        if name not in self.models:
            raise ConfigurationError(
                f"Model configuration '{name}' not found",
                ERROR_CODES["INVALID_MODEL_CONFIG"],
            )

        model_config = self.models[name].copy()

        # 检查API密钥
        if not model_config.get("api_key"):
            raise ConfigurationError(
                f"API key not configured for model '{name}'",
                ERROR_CODES["MISSING_API_KEY"],
            )

        return model_config

    def get_setting(self, key: str, default: Any = None) -> Any:
        """
        获取配置设置

        Args:
            key: 设置键名
            default: 默认值

        Returns:
            设置值
        """
        return self.settings.get(key, default)

    def update_setting(self, key: str, value: Any):
        """
        更新配置设置

        Args:
            key: 设置键名
            value: 设置值
        """
        self.settings[key] = value

    def list_models(self) -> list:
        """获取所有可用的模型名称列表"""
        return list(self.models.keys())

    def validate_model_config(self, name: str) -> bool:
        """
        验证模型配置是否有效

        Args:
            name: 模型配置名称

        Returns:
            配置是否有效
        """
        try:
            config = self.get_model(name)
            required_fields = ["url", "api_key", "model_name"]

            for field in required_fields:
                if not config.get(field):
                    return False

            return True
        except ConfigurationError:
            return False

    def save_config(self, config_path: str):
        """
        保存当前配置到文件

        Args:
            config_path: 配置文件保存路径
        """
        config = {"models": self.models, "settings": self.settings}

        try:
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigurationError(
                f"Error saving configuration: {str(e)}",
                ERROR_CODES["INVALID_CONFIG_FILE"],
            )

    def get_debug_config(self) -> Dict[str, Any]:
        """获取debug配置"""
        return self.debug_config.copy()

    def update_debug_config(self, config: Dict[str, Any]):
        """更新debug配置"""
        self.debug_config.update(config)

    def is_debug_enabled(self) -> bool:
        """检查是否启用debug模式"""
        return self.debug_config.get("enabled", False)

    def to_dict(self) -> Dict[str, Any]:
        """将配置转换为字典格式"""
        return {
            "models": self.models,
            "settings": self.settings,
            "debug": self.debug_config,
        }
