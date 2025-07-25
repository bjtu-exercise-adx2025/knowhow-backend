"""
LangGraph模块使用示例

演示如何使用ArticleProcessorService处理文章内容
"""

import os
import sys
from typing import Dict, Any

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from langgraph import ArticleProcessorService


def example_basic_usage():
    """基础使用示例"""
    print("=== LangGraph基础使用示例 ===")
    
    try:
        # 初始化服务（使用默认配置）
        service = ArticleProcessorService()
        
        # 检查服务状态
        status = service.get_service_status()
        print(f"服务状态: {status}")
        
        # 模拟处理语音转录与文章
        transcript_id = 19  # 假设存在的转录ID
        article_ids = [1, 44, 78, 71]  # 假设存在的文章ID列表
        
        print(f"\n处理转录ID: {transcript_id}")
        print(f"相关文章ID: {article_ids}")
        
        # 处理内容
        result = service.process_transcript_with_articles(
            transcript_id=transcript_id,
            article_ids=article_ids,
            user_id=2
        )
        
        print(f"\n处理结果: {result}")
        
        if result["success"]:
            data = result["data"]
            print(f"✅ 处理成功!")
            print(f"   新建文章数: {data['created_count']}")
            print(f"   更新文章数: {data['updated_count']}")
            print(f"   总处理数: {data['total_processed']}")
        else:
            print(f"❌ 处理失败: {result['error_message']}")
            print(f"   错误码: {result['error_code']}")
        
    except Exception as e:
        print(f"❌ 示例执行失败: {str(e)}")


def example_custom_config():
    """自定义配置示例"""
    print("\n=== 自定义配置示例 ===")
    
    try:
        # 使用自定义配置文件
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        service = ArticleProcessorService(config_path=config_path, model_name="default")
        
        print("✅ 使用自定义配置初始化成功")
        
        # 更新模型配置
        update_result = service.update_model_config(
            model_name="test_model",
            url="https://api.example.com/v1/chat/completions",
            api_key="test_api_key",
            model_api_name="test-model-name"
        )
        
        print(f"配置更新结果: {update_result}")
        
    except Exception as e:
        print(f"❌ 自定义配置示例失败: {str(e)}")


def example_batch_processing():
    """批量处理示例"""
    print("\n=== 批量处理示例 ===")
    
    try:
        service = ArticleProcessorService()
        
        # 批量处理多个转录文本和文章对
        transcript_article_pairs = [
            {"transcript_id": 1, "article_ids": [1, 2]},
            {"transcript_id": 2, "article_ids": [3]},
            {"transcript_id": 3, "article_ids": []}  # 没有相关文章
        ]
        
        print(f"批量处理 {len(transcript_article_pairs)} 个转录文本...")
        
        batch_result = service.batch_process_transcripts(
            transcript_article_pairs=transcript_article_pairs,
            user_id=2
        )
        
        print(f"批量处理结果: {batch_result}")
        
        if batch_result["success"]:
            stats = batch_result["overall_stats"]
            print(f"✅ 批量处理完成!")
            print(f"   总对数: {stats['total_pairs']}")
            print(f"   成功: {stats['successful_pairs']}")
            print(f"   失败: {stats['failed_pairs']}")
            print(f"   总创建: {stats['total_created']}")
            print(f"   总更新: {stats['total_updated']}")
        else:
            print(f"❌ 批量处理失败: {batch_result['message']}")
        
    except Exception as e:
        print(f"❌ 批量处理示例失败: {str(e)}")


def example_error_handling():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    try:
        service = ArticleProcessorService()
        
        # 测试无效的转录ID
        result = service.process_transcript_with_articles(
            transcript_id=99999,  # 不存在的ID
            article_ids=[1],
            user_id=2
        )
        
        if not result["success"]:
            print(f"✅ 正确捕获错误:")
            print(f"   错误消息: {result['error_message']}")
            print(f"   错误码: {result['error_code']}")
            print(f"   详细信息: {result.get('details', 'N/A')}")
        
    except Exception as e:
        print(f"❌ 错误处理示例失败: {str(e)}")


def main():
    """主函数"""
    print("LangGraph模块使用示例")
    print("=" * 50)
    
    try:
        # 基础使用
        example_basic_usage()
        
        # # 自定义配置
        # example_custom_config()
        
        # # 批量处理
        # example_batch_processing()
        
        # # 错误处理
        # example_error_handling()
        
        # print("\n" + "=" * 50)
        print("✅ 所有示例执行完成!")
        
    except Exception as e:
        print(f"\n❌ 示例执行过程中发生错误: {str(e)}")


if __name__ == "__main__":
    main()