"""
在Flask应用上下文中使用LangGraph的示例

正确的使用方式，确保数据库连接正常工作
"""

import os
import sys

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import create_app
from langgraph import ArticleProcessorService


def example_with_flask_context():
    """在Flask应用上下文中使用LangGraph"""
    print("=== 在Flask应用上下文中使用LangGraph ===")
    
    # 创建Flask应用
    app = create_app()
    
    # 在应用上下文中运行
    with app.app_context():
        try:
            # 初始化服务
            service = ArticleProcessorService()
            
            # 检查服务状态
            status = service.get_service_status()
            print(f"服务状态: {status}")
            
            if status["database"]["status"] == "connected":
                print("✅ 数据库连接成功!")
                
                # 模拟处理语音转录与文章
                transcript_id = 15  # 使用实际存在的转录ID
                article_ids = [1, 44, 69, 45]  # 使用实际存在的文章ID
                
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
                    
                    if data['created_articles']:
                        print(f"   新建文章: {data['created_articles']}")
                    if data['updated_articles']:
                        print(f"   更新文章: {data['updated_articles']}")
                else:
                    print(f"❌ 处理失败: {result['error_message']}")
                    print(f"   错误码: {result['error_code']}")
            else:
                print("❌ 数据库连接失败，无法继续处理")
                
        except Exception as e:
            print(f"❌ 示例执行失败: {str(e)}")
            import traceback
            traceback.print_exc()


def example_batch_processing():
    """批量处理示例"""
    print("\n=== 批量处理示例 ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            service = ArticleProcessorService()
            
            # 批量处理多个转录文本和文章对
            transcript_article_pairs = [
                {"transcript_id": 15, "article_ids": [1, 44]},
                {"transcript_id": 14, "article_ids": [69]},
                {"transcript_id": 13, "article_ids": []}  # 没有相关文章
            ]
            
            print(f"批量处理 {len(transcript_article_pairs)} 个转录文本...")
            
            batch_result = service.batch_process_transcripts(
                transcript_article_pairs=transcript_article_pairs,
                user_id=2
            )
            
            if batch_result["success"]:
                stats = batch_result["overall_stats"]
                print(f"✅ 批量处理完成!")
                print(f"   总对数: {stats['total_pairs']}")
                print(f"   成功: {stats['successful_pairs']}")
                print(f"   失败: {stats['failed_pairs']}")
                print(f"   总创建: {stats['total_created']}")
                print(f"   总更新: {stats['total_updated']}")
                
                # 显示个别结果
                for result in batch_result["individual_results"]:
                    transcript_id = result["transcript_id"]
                    success = result["result"]["success"]
                    status = "✅" if success else "❌"
                    print(f"   {status} 转录ID {transcript_id}: {'成功' if success else '失败'}")
            else:
                print(f"❌ 批量处理失败: {batch_result['message']}")
                
        except Exception as e:
            print(f"❌ 批量处理示例失败: {str(e)}")


def example_error_handling():
    """错误处理示例"""
    print("\n=== 错误处理示例 ===")
    
    app = create_app()
    
    with app.app_context():
        try:
            service = ArticleProcessorService()
            
            # 测试无效的转录ID
            print("测试无效的转录ID...")
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
            
            # 测试无效的文章ID
            print("\n测试无效的文章ID...")
            result = service.process_transcript_with_articles(
                transcript_id=15,
                article_ids=[99999],  # 不存在的文章ID
                user_id=2
            )
            
            if not result["success"]:
                print(f"✅ 正确捕获错误:")
                print(f"   错误消息: {result['error_message']}")
                print(f"   错误码: {result['error_code']}")
                
        except Exception as e:
            print(f"❌ 错误处理示例失败: {str(e)}")


def main():
    """主函数"""
    print("LangGraph模块Flask上下文使用示例")
    print("=" * 50)
    
    try:
        # 基础使用
        example_with_flask_context()
        
        # 批量处理
        example_batch_processing()
        
        # 错误处理
        example_error_handling()
        
        print("\n" + "=" * 50)
        print("✅ 所有示例执行完成!")
        
    except Exception as e:
        print(f"\n❌ 示例执行过程中发生错误: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()