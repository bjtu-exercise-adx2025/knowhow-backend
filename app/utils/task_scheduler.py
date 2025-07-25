"""
定时任务调度器
"""

import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from flask import current_app
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# 添加项目根目录到Python路径
project_root = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app import db
from app.api.v1.article import add_tags_to_article, generate_tags_from_article
from app.models.article import Article
from app.models.generation_task import GenerationTask, TaskRecordsMapping
from app.models.user import User
from app.models.user_audio_record import UserAudioRecord
from app.utils.get_simlarity import cosine_similarity_list_sbert
from langgraph import ArticleProcessorService


class TaskScheduler:
    """任务调度器"""

    def __init__(self, app=None):
        self.app = app
        self.executor = ThreadPoolExecutor(max_workers=5)
        self.running = False
        self.scheduler_thread = None

        # 初始化 LangGraph 服务
        try:
            self.langgraph_service = ArticleProcessorService()
        except Exception as e:
            print(f"警告：LangGraph服务初始化失败: {e}")
            self.langgraph_service = None

    def init_app(self, app):
        """初始化应用"""
        self.app = app

    def start(self):
        """启动定时任务"""
        if self.running:
            return

        self.running = True
        self.scheduler_thread = threading.Thread(
            target=self._run_scheduler, daemon=True
        )
        self.scheduler_thread.start()
        print("定时任务调度器已启动")

    def stop(self):
        """停止定时任务"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
        self.executor.shutdown(wait=True)
        print("定时任务调度器已停止")

    def _run_scheduler(self):
        """运行调度器主循环"""
        while self.running:
            try:
                with self.app.app_context():
                    self._check_and_process_tasks()
            except Exception as e:
                current_app.logger.error(f"定时任务执行失败: {e}")

            # 等待10秒
            time.sleep(10)

    def _check_and_process_tasks(self):
        """检查并处理任务"""
        # 查找需要开始langgraph的任务（只需要检查langgraph_status，因为LangGraph会处理summary）
        langgraph_tasks = GenerationTask.query.filter_by(
            langgraph_status=0
        ).all()

        for task in langgraph_tasks:
            self.executor.submit(self._begin_langgraph, task.id)
            current_app.logger.info(f"提交langgraph任务: {task.id}")

        # 注释：LangGraph服务已集成summary和标签生成，不需要单独的summary任务

    def _begin_langgraph(self, task_id):
        """开始langgraph任务"""
        try:
            with self.app.app_context():
                # 获取任务
                task = GenerationTask.query.get(task_id)
                if not task:
                    current_app.logger.error(f"任务不存在: {task_id}")
                    return

                # 更新状态为processing
                task.langgraph_status = 1
                db.session.commit()
                current_app.logger.info(f"开始处理langgraph任务: {task_id}")

                # 获取关联的用户音频记录
                task_mapping = TaskRecordsMapping.query.filter_by(
                    task_id=task_id
                ).first()
                if not task_mapping:
                    current_app.logger.error(f"任务{task_id}没有关联的记录映射")
                    task.langgraph_status = 3  # failed
                    task.error_message = "没有关联的记录映射"
                    db.session.commit()
                    return

                # 获取原始记录
                user_record = UserAudioRecord.query.get(task_mapping.record_id)
                if not user_record:
                    current_app.logger.error(f"任务{task_id}没有关联的用户记录")
                    task.langgraph_status = 3  # failed
                    task.error_message = "没有关联的用户记录"
                    db.session.commit()
                    return

                # 获取原始文字内容
                original_text = user_record.transcript
                if not original_text:
                    current_app.logger.error(f"任务{task_id}的用户记录没有文字内容")
                    task.langgraph_status = 3  # failed
                    task.error_message = "用户记录没有文字内容"
                    db.session.commit()
                    return

                # 获取用户的历史文章
                user_articles = Article.query.filter(
                    Article.author_id == task.user_id,
                    Article.status == "published",
                ).all()

                if not user_articles:
                    current_app.logger.warning(f"用户{task.user_id}没有历史文章")
                    # 直接调用langgraph服务处理单篇文章
                    is_success, result = self._call_langgraph_service(
                        task_mapping.record_id, [], task.user_id
                    )
                else:
                    # 计算相似度并获取top-4文章
                    article_texts = []

                    for article in user_articles:
                        text = article.title + " " + (article.summary or "")
                        article_texts.append(text)

                    # 计算相似度（使用原始用户输入文字）
                    similarities = cosine_similarity_list_sbert(
                        original_text, article_texts
                    )

                    # 获取相似度大于0.5的top-4相似文章
                    top_articles = []
                    sorted_indices = sorted(
                        range(len(similarities)),
                        key=lambda i: similarities[i],
                        reverse=True,
                    )

                    # 筛选相似度大于0.5的文章，最多取4篇
                    for i in sorted_indices:
                        if similarities[i] > 0.5 and len(top_articles) < 4:
                            top_articles.append(
                                {
                                    "id": user_articles[i].id,
                                    "title": user_articles[i].title,
                                    "summary": user_articles[i].summary,
                                    "similarity": similarities[i],
                                }
                            )
                        elif similarities[i] <= 0.5:
                            # 相似度不够，由于已经按降序排列，后面的都不够了
                            break

                    # 调用真实的langgraph服务
                    is_success, result = self._call_langgraph_service(
                        task_mapping.record_id, top_articles, task.user_id
                    )

                if is_success:
                    # 更新langgraph状态为完成
                    task.langgraph_status = 2
                    task.summary_status = 2  # 同时将summary状态设为完成，因为LangGraph已经处理了摘要
                    db.session.commit()
                    current_app.logger.info(f"Langgraph任务完成: {task_id}")

                    # 处理返回结果中的文章，为新创建和更新的文章生成标签
                    self._process_article_tags(result, task.user_id)
                else:
                    # 更新状态为失败
                    task.langgraph_status = 3
                    task.error_message = result
                    db.session.commit()
                    current_app.logger.error(
                        f"Langgraph任务失败: {task_id}, 错误: {result}"
                    )

        except Exception as e:
            current_app.logger.error(f"处理langgraph任务失败: {task_id}, 错误: {e}")
            try:
                with self.app.app_context():
                    task = GenerationTask.query.get(task_id)
                    if task:
                        task.langgraph_status = 3
                        task.error_message = str(e)
                        db.session.commit()
            except:
                pass


    def _call_langgraph_service(self, transcript_id, similar_articles, user_id):
        """调用真实的langgraph服务"""
        try:
            current_app.logger.info(
                f"开始处理转录ID: {transcript_id}, 用户ID: {user_id}"
            )
            current_app.logger.info(f"相似文章数量: {len(similar_articles)}")

            # 检查服务是否可用
            if not self.langgraph_service:
                current_app.logger.error("LangGraph服务未初始化")
                return False, "LangGraph服务未初始化"

            # 从similar_articles中提取article_ids
            article_ids = (
                [article["id"] for article in similar_articles]
                if similar_articles
                else []
            )
            current_app.logger.info(f"提取的文章IDs: {article_ids}")

            # 调用langgraph服务
            result = self.langgraph_service.process_transcript_with_articles(
                transcript_id=transcript_id, article_ids=article_ids, user_id=user_id
            )

            current_app.logger.info(f"LangGraph处理结果: {result}")

            if result["success"]:
                data = result["data"]
                message = f"处理成功 - 创建文章: {data['created_count']}, 更新文章: {data['updated_count']}, 总处理: {data['total_processed']}"
                current_app.logger.info(message)
                return True, result  # 返回完整的结果，而不是消息
            else:
                error_msg = f"处理失败: {result['error_message']} (错误码: {result['error_code']})"
                current_app.logger.error(error_msg)
                return False, error_msg

        except Exception as e:
            error_msg = f"调用LangGraph服务异常: {str(e)}"
            current_app.logger.error(error_msg)
            return False, error_msg

    def _process_article_tags(self, langgraph_result, user_id):
        """处理LangGraph返回结果中的文章，为相关文章生成标签"""
        try:
            with self.app.app_context():
                # 从LangGraph返回结果中获取data字段
                data = langgraph_result.get("data", {})
                article_ids_to_process = []
                
                # 处理created_articles
                if data.get("created_articles"):
                    for created_article in data["created_articles"]:
                        article_ids_to_process.append(created_article["new_id"])
                        current_app.logger.info(f"添加新创建文章到标签生成队列: {created_article['new_id']}")
                
                # 处理updated_articles
                # if data.get("updated_articles"):
                #     for updated_article in data["updated_articles"]:
                #         article_ids_to_process.append(updated_article["id"])
                #         current_app.logger.info(f"添加更新文章到标签生成队列: {updated_article['id']}")
                
                current_app.logger.info(f"总共需要生成标签的文章数量: {len(article_ids_to_process)}")
                
                # 为每篇文章生成标签
                for article_id in article_ids_to_process:
                    self._generate_tags_for_article(article_id, user_id)
                
                current_app.logger.info(f"完成为{len(article_ids_to_process)}篇文章生成标签")
        
        except Exception as e:
            current_app.logger.error(f"处理文章标签失败: {str(e)}")
            current_app.logger.error(f"LangGraph结果格式: {langgraph_result}")  # 添加调试信息

    def _generate_tags_for_article(self, article_id, user_id):
        """为指定文章生成标签"""
        try:
            with self.app.app_context():
                # 获取文章
                article = Article.query.get(article_id)
                if not article:
                    current_app.logger.error(f"文章{article_id}不存在")
                    return
                
                current_app.logger.info(f"开始为文章{article_id}生成标签")
                
                # 构建完整的文章内容
                full_article_content = f"{article.title}\n\n{article.content or ''}\n\n{article.summary or ''}"
                current_app.logger.info(f"文章内容长度: {len(full_article_content)}")
                
                # 生成标签
                tags = generate_tags_from_article(full_article_content, user_id)
                current_app.logger.info(f"生成的标签: {tags}")
                
                if tags:
                    # 为文章添加标签
                    add_tags_to_article(article_id, tags, user_id)
                    current_app.logger.info(f"成功为文章{article_id}添加了{len(tags)}个标签")
                    
                    # 提交数据库更改
                    db.session.commit()
                else:
                    current_app.logger.warning(f"文章{article_id}未生成任何标签")
        
        except Exception as e:
            current_app.logger.error(f"为文章{article_id}生成标签失败: {str(e)}")
            db.session.rollback()



# 全局调度器实例
scheduler = TaskScheduler()
