"""
LangGraph Debug功能示例

演示如何使用debug配置和日志功能
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from langgraph import ArticleProcessorService


def example_with_debug_enabled():
    """启用debug模式的示例"""
    print("=== Debug模式启用示例 ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 使用默认配置（debug已启用）
            service = ArticleProcessorService()
            
            print("📋 当前debug配置:")
            debug_config = service.gpt_config.get_debug_config()
            for key, value in debug_config.items():
                print(f"   {key}: {value}")
            
            print(f"\n🔍 Debug模式: {'启用' if service.gpt_config.is_debug_enabled() else '禁用'}")
            
            # 测试处理功能，观察debug日志输出
            print("\n🚀 开始处理测试（观察debug日志）...")
            
            result = service.process_transcript_with_articles(
                transcript_id=15,
                article_ids=[1, 44],
                user_id=2
            )
            
            print(f"\n📊 处理结果: {result['success']}")
            if result['success']:
                data = result['data']
                print(f"   新建: {data['created_count']}, 更新: {data['updated_count']}")
            else:
                print(f"   错误: {result['error_message']}")
                
        except Exception as e:
            print(f"❌ 示例执行失败: {str(e)}")


def example_with_custom_debug_config():
    """自定义debug配置示例"""
    print("\n=== 自定义Debug配置示例 ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            # 创建自定义debug配置
            custom_config_path = os.path.join(os.path.dirname(__file__), "debug_config.json")
            
            # 创建自定义配置文件
            import json
            custom_config = {
                "models": {
                    "default": {
                        "url": "https://ai-proxy.chatwise.app/openrouter/api/v1",
                        "api_key": "***REMOVED_API_KEY***",
                        "model_name": "google/gemini-2.5-pro"
                    }
                },
                "settings": {
                    "timeout": 30,
                    "max_retries": 2,
                    "temperature": 0.0,
                    "max_tokens": 30000
                },
                "debug": {
                    "enabled": True,
                    "log_level": "DEBUG",
                    "log_to_file": True,
                    "log_file": "custom_debug.log",
                    "log_to_console": True,
                    "log_requests": True,
                    "log_responses": True,
                    "log_database_queries": True,
                    "log_processing_steps": True
                }
            }
            
            with open(custom_config_path, 'w', encoding='utf-8') as f:
                json.dump(custom_config, f, indent=2, ensure_ascii=False)
            
            print(f"📝 创建自定义配置文件: {custom_config_path}")
            
            # 使用自定义配置
            service = ArticleProcessorService(config_path=custom_config_path)
            
            print("📋 自定义debug配置:")
            debug_config = service.gpt_config.get_debug_config()
            for key, value in debug_config.items():
                print(f"   {key}: {value}")
            
            print(f"\n📄 日志文件位置: {debug_config['log_file']}")
            
            # 清理临时配置文件
            if os.path.exists(custom_config_path):
                os.remove(custom_config_path)
                print(f"🧹 清理临时配置文件")
                
        except Exception as e:
            print(f"❌ 自定义配置示例失败: {str(e)}")


def example_debug_configuration_methods():
    """演示debug配置方法"""
    print("\n=== Debug配置方法示例 ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            service = ArticleProcessorService()
            
            print("📋 原始debug配置:")
            original_config = service.gpt_config.get_debug_config()
            for key, value in original_config.items():
                print(f"   {key}: {value}")
            
            # 动态更新debug配置
            print("\n🔧 动态更新debug配置...")
            new_debug_config = {
                "enabled": True,
                "log_level": "INFO",
                "log_to_console": True,
                "log_requests": False,
                "log_responses": False,
                "log_database_queries": True,
                "log_processing_steps": True
            }
            
            service.gpt_config.update_debug_config(new_debug_config)
            
            print("📋 更新后的debug配置:")
            updated_config = service.gpt_config.get_debug_config()
            for key, value in updated_config.items():
                print(f"   {key}: {value}")
            
            print(f"\n🔍 Debug状态: {'启用' if service.gpt_config.is_debug_enabled() else '禁用'}")
            
        except Exception as e:
            print(f"❌ 配置方法示例失败: {str(e)}")


def example_check_log_files():
    """检查日志文件示例"""
    print("\n=== 检查日志文件示例 ===")
    
    # 检查可能存在的日志文件
    log_files = [
        "langgraph_debug.log",
        "custom_debug.log"
    ]
    
    for log_file in log_files:
        if os.path.exists(log_file):
            file_size = os.path.getsize(log_file)
            print(f"📄 发现日志文件: {log_file} (大小: {file_size} 字节)")
            
            # 显示最后几行日志
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    if lines:
                        print(f"   最后 {min(3, len(lines))} 行日志:")
                        for line in lines[-3:]:
                            print(f"   > {line.strip()}")
                    else:
                        print("   日志文件为空")
            except Exception as e:
                print(f"   读取日志文件失败: {str(e)}")
        else:
            print(f"📄 日志文件不存在: {log_file}")


def main():
    """主函数"""
    print("LangGraph Debug功能演示")
    print("=" * 50)
    
    try:
        # Debug启用示例
        example_with_debug_enabled()
        
        # 自定义debug配置
        example_with_custom_debug_config()
        
        # Debug配置方法
        example_debug_configuration_methods()
        
        # 检查日志文件
        example_check_log_files()
        
        print("\n" + "=" * 50)
        print("✅ Debug功能演示完成!")
        print("💡 提示: 检查生成的日志文件以查看详细的debug信息")
        
    except Exception as e:
        print(f"\n❌ Debug演示过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()