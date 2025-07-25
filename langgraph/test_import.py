"""
简单的导入测试脚本

验证LangGraph模块的所有组件是否可以正常导入
"""

import sys
import os

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def test_imports():
    """测试所有模块的导入"""
    
    try:
        print("测试导入 LangGraph 主模块...")
        from langgraph import ArticleProcessorService, GPTModelConfig
        print("✅ 主模块导入成功")
        
        print("测试导入异常类...")
        from langgraph.utils.exceptions import (
            LangGraphException,
            DatabaseOperationError, 
            GPTAPIError,
            ContentValidationError
        )
        print("✅ 异常类导入成功")
        
        print("测试导入配置模块...")
        from langgraph.config.gpt_models import GPTModelConfig
        print("✅ 配置模块导入成功")
        
        print("测试导入数据库操作模块...")
        from langgraph.database.operations import DatabaseOperations
        print("✅ 数据库操作模块导入成功")
        
        print("测试导入核心工作流模块...")
        from langgraph.core.workflow import LangGraphWorkflow
        from langgraph.core.prompts import PromptManager
        from langgraph.core.processors import ContentProcessor
        print("✅ 核心工作流模块导入成功")
        
        print("测试导入工具模块...")
        from langgraph.utils.validators import ContentValidator
        print("✅ 工具模块导入成功")
        
        print("\n🎉 所有模块导入测试通过!")
        return True
        
    except ImportError as e:
        print(f"❌ 导入失败: {e}")
        return False
    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        return False

def test_basic_initialization():
    """测试基础初始化"""
    
    try:
        print("\n测试基础组件初始化...")
        
        # 测试配置管理器
        from langgraph.config.gpt_models import GPTModelConfig
        config = GPTModelConfig()
        print(f"✅ GPT配置管理器初始化成功，可用模型: {config.list_models()}")
        
        # 测试验证器
        from langgraph.utils.validators import ContentValidator
        validator = ContentValidator()
        print("✅ 内容验证器初始化成功")
        
        # 测试Prompt管理器
        from langgraph.core.prompts import PromptManager
        prompt_manager = PromptManager()
        print("✅ Prompt管理器初始化成功")
        
        # 测试内容处理器
        from langgraph.core.processors import ContentProcessor
        processor = ContentProcessor()
        print("✅ 内容处理器初始化成功")
        
        print("\n🎉 基础组件初始化测试通过!")
        return True
        
    except Exception as e:
        print(f"❌ 初始化测试失败: {e}")
        return False

def test_configuration():
    """测试配置功能"""
    
    try:
        print("\n测试配置功能...")
        
        from langgraph.config.gpt_models import GPTModelConfig
        
        # 创建配置实例
        config = GPTModelConfig()
        
        # 测试添加模型配置
        config.add_model(
            name="test_model",
            url="https://api.test.com/v1",
            api_key="test_key",
            model_name="test-model"
        )
        
        # 验证模型配置
        model_config = config.get_model("test_model")
        assert model_config["url"] == "https://api.test.com/v1"
        assert model_config["api_key"] == "test_key"
        assert model_config["model_name"] == "test-model"
        
        print("✅ 配置功能测试通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置功能测试失败: {e}")
        return False

def main():
    """主测试函数"""
    print("LangGraph 模块导入测试")
    print("=" * 50)
    
    tests = [
        test_imports,
        test_basic_initialization,
        test_configuration
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"❌ 测试函数 {test.__name__} 执行失败: {e}")
    
    print("\n" + "=" * 50)
    print(f"测试结果: {passed}/{total} 个测试通过")
    
    if passed == total:
        print("✅ 所有测试通过！模块可以正常使用。")
        return True
    else:
        print("❌ 部分测试失败，请检查模块配置。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)