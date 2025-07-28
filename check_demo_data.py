#!/usr/bin/env python3
"""
查看用户ID=5的当前演示数据脚本
"""

import sys
import os

# 添加项目路径到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User
from app.models.article import Article, ArticleRelationship, ArticleTag
from app.models.tag import Tag
from app.models.generation_task import GenerationTask
from app.models.user_audio_record import UserAudioRecord

def main():
    app = create_app()
    
    with app.app_context():
        target_user_id = 5
        print(f"=== 查看用户ID={target_user_id}的当前数据 ===\n")
        
        # 1. 查看用户信息
        user = User.query.get(target_user_id)
        if not user:
            print(f"❌ 用户ID={target_user_id}不存在")
            return
        
        print(f"👤 用户信息:")
        print(f"   ID: {user.id}")
        print(f"   用户名: {user.username}")
        print(f"   邮箱: {user.email}")
        print(f"   头像: {user.avatar_url}")
        print(f"   个人简介: {user.bio}")
        print()
        
        # 2. 查看标签
        tags = Tag.query.filter_by(user_id=target_user_id).order_by(Tag.created_at).all()
        print(f"🏷️  标签数据 ({len(tags)}个):")
        tag_dict = {}
        for tag in tags:
            tag_dict[tag.id] = tag
            print(f"   ID: {tag.id}, 名称: '{tag.name}', 创建时间: {tag.created_at}")
        print()
        
        # 3. 查看文章
        articles = Article.query.filter_by(author_id=target_user_id).order_by(Article.created_at).all()
        print(f"📝 文章数据 ({len(articles)}篇):")
        article_dict = {}
        for article in articles:
            article_dict[article.id] = article
            
            # 获取文章标签
            article_tags = []
            for tag in article.tags:
                article_tags.append(f"'{tag.name}'")
            
            print(f"   ID: {article.id}")
            print(f"   标题: '{article.title}'")
            print(f"   摘要: '{article.summary[:50]}{'...' if len(article.summary) > 50 else ''}'")
            print(f"   状态: {article.status}")
            print(f"   标签: [{', '.join(article_tags)}]")
            print(f"   创建时间: {article.created_at}")
            print(f"   内容预览: '{article.content[:100]}{'...' if len(article.content) > 100 else ''}'")
            print()
        
        # 4. 查看文章引用关系
        relationships = ArticleRelationship.query.filter(
            ArticleRelationship.citing_article_id.in_([a.id for a in articles])
        ).all()
        
        relationships.extend(ArticleRelationship.query.filter(
            ArticleRelationship.referenced_article_id.in_([a.id for a in articles])
        ).all())
        
        # 去重
        unique_relationships = {}
        for rel in relationships:
            key = (rel.citing_article_id, rel.referenced_article_id)
            if key not in unique_relationships:
                unique_relationships[key] = rel
        
        print(f"🔗 文章引用关系 ({len(unique_relationships)}个):")
        for rel in unique_relationships.values():
            citing_article = article_dict.get(rel.citing_article_id)
            referenced_article = article_dict.get(rel.referenced_article_id)
            
            citing_title = citing_article.title if citing_article else f"ID:{rel.citing_article_id}(不存在)"
            referenced_title = referenced_article.title if referenced_article else f"ID:{rel.referenced_article_id}(不存在)"
            
            print(f"   '{citing_title}' 引用了 '{referenced_title}'")
            print(f"   创建时间: {rel.created_at}")
            print()
        
        # 5. 查看生成任务
        tasks = GenerationTask.query.filter_by(user_id=target_user_id).order_by(GenerationTask.created_at).all()
        print(f"⚙️  生成任务 ({len(tasks)}个):")
        for task in tasks:
            print(f"   ID: {task.id}")
            print(f"   摘要状态: {task.summary_status}")
            print(f"   处理状态: {task.langgraph_status}")
            print(f"   创建时间: {task.created_at}")
            print()
        
        # 6. 查看音频记录
        records = UserAudioRecord.query.filter_by(user_id=target_user_id).order_by(UserAudioRecord.created_at).all()
        print(f"🎤 音频记录 ({len(records)}个):")
        for record in records:
            print(f"   ID: {record.id}")
            print(f"   标题: '{record.title}'")
            print(f"   转录内容: '{record.transcript[:100]}{'...' if len(record.transcript) > 100 else ''}'")
            print(f"   创建时间: {record.created_at}")
            print()
        
        # 7. 生成Python代码格式的数据
        print("=" * 80)
        print("📋 可用于代码的数据格式:")
        print()
        
        print("# 标签数据")
        print("demo_tags_data = [", end="")
        tag_names = [f'"{tag.name}"' for tag in tags]
        print(", ".join(tag_names), end="")
        print("]")
        print()
        
        print("# 文章数据")
        print("demo_articles_data = [")
        for i, article in enumerate(articles):
            article_tag_names = [f'"{tag.name}"' for tag in article.tags]
            
            print("    {")
            print(f'        "title": "{article.title}",')
            print(f'        "summary": "{article.summary}",')
            # 转义内容中的换行符和引号
            content_escaped = article.content.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n')
            print(f'        "content": "{content_escaped}",')
            print(f'        "tags": [{", ".join(article_tag_names)}],')
            print(f'        "status": "{article.status}"')
            print("    }", end="")
            if i < len(articles) - 1:
                print(",")
            else:
                print()
        print("]")
        print()
        
        print("# 引用关系数据")
        print("demo_relationships = [")
        rel_list = list(unique_relationships.values())
        for i, rel in enumerate(rel_list):
            citing_article = article_dict.get(rel.citing_article_id)
            referenced_article = article_dict.get(rel.referenced_article_id)
            
            if citing_article and referenced_article:
                print("    {")
                print(f'        "citing": "{citing_article.title}",')
                print(f'        "referenced": "{referenced_article.title}"')
                print("    }", end="")
                if i < len(rel_list) - 1:
                    print(",")
                else:
                    print()
        print("]")
        
        print("\n✅ 数据查看完成！")

if __name__ == "__main__":
    main()