import json
from datetime import datetime
from typing import Any

from flask import Blueprint, current_app, request
from sqlalchemy import extract

from app import db
from app.models.article import Article, ArticleRelationship, ArticleTag
from app.models.generation_task import GenerationTask, TaskRecordsMapping
from app.models.tag import Tag
from app.models.user import User
from app.models.user_audio_record import UserAudioRecord
from app.utils.llm_service import llm_call_qwen3_8b

article_bp = Blueprint("articles", __name__)


@article_bp.route("/articles/text-record", methods=["POST"])
def create_text_record():
    """
    用户提交文字记录并创建生成任务
    ---
    parameters:
        - name: data
          in: body
          required: true
          schema:
            type: object
            properties:
                user_id:
                    type: integer
                    description: 用户ID
                text:
                    type: string
                    description: 用户输入的文字内容
    responses:
        200:
            description: 记录创建成功
            schema:
                type: object
                properties:
                    message:
                        type: string
                    title:
                        type: string
                    task_id:
                        type: integer
                    record_id:
                        type: integer
        400:
            description: 请求参数错误
        404:
            description: 用户不存在
        500:
            description: 服务器内部错误
    """
    try:
        data = request.get_json()
        user_id = data.get("user_id")
        text = data.get("text")

        # 参数验证
        if not user_id or not text:
            return {"message": "用户ID和文字内容不能为空"}, 400

        if not isinstance(user_id, int):
            return {"message": "用户ID必须为整数"}, 400

        if not isinstance(text, str) or len(text.strip()) == 0:
            return {"message": "文字内容不能为空"}, 400

        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return {"message": "用户不存在"}, 404

        # 1. 生成标题
        title = generate_title_only(text, user_id)

        # 2. 创建音频记录（复用表结构存储文字），保存标题
        audio_record = UserAudioRecord(
            user_id=user_id, transcript=text.strip(), title=title
        )
        db.session.add(audio_record)
        db.session.flush()  # 获取记录ID

        # 3. 创建生成任务
        generation_task = GenerationTask(
            user_id=user_id, summary_status=0, langgraph_status=0  # pending  # pending
        )
        db.session.add(generation_task)
        db.session.flush()  # 获取任务ID

        # 4. 创建任务与记录的关联
        task_mapping = TaskRecordsMapping(
            task_id=generation_task.id, record_id=audio_record.id
        )
        db.session.add(task_mapping)

        # 注意：此时不创建article记录，article将在langgraph处理时创建

        # 提交事务
        db.session.commit()

        return {
            "message": "记录创建成功",
            "title": title,
            "task_id": generation_task.id,
            "record_id": audio_record.id,
        }, 200

    except Exception as e:
        current_app.logger.error(f"创建文字记录失败: {str(e)}")
        db.session.rollback()
        return {"message": "创建记录失败，请稍后重试"}, 500


# def generate_title_tags(text: str, user_id: int) -> str | tuple[Any, Any]:
#     """
#     根据文字内容生成标题与标签

#     Args:
#         text: 用户输入的文字内容

#     Returns:
#         str: 生成的标题
#         list[str]: 生成的标签列表
#     """
#     # 根据user_id获取其tag
#     user = User.query.get(user_id)
#     if not user:
#         current_app.logger.error(f"用户ID {user_id} 不存在")
#         return "未能生成标题，请重试"
#     # 查询tag表中与用户相关的标签, tag表中有user_id项
#     tags = Tag.query.filter_by(user_id=user_id).all()
#     if len(tags) == 0:
#         prompt = f"""
# # 角色
# 你是一位资深的内容编辑和新媒体运营专家。你不仅擅长从复杂的文本中精准地提炼核心主题标签（Tag），还精通如何创作引人注目、概括精准的标题（Title）。

# # 任务
# 为我提供的【待处理文本】生成一个吸引人的标题（Title）和2-5个最相关的标签（Tags）。所有标签都需要你根据文本内容从零开始创作。

# # 工作流程
# 1.  **深入分析**：首先，请仔细阅读并理解【待处理文本】的中心思想、关键论点、以及文本中呈现的核心矛盾或疑问（例如：亮眼数据与糟糕体感的反差）。
# 2.  **构思标题 (Title Crafting)**：基于你的分析，创作一个标题。这个标题应该：
#     *   **引人入胜**：能抓住读者眼球，引发好奇心。可以采用提问、制造悬念或点出矛盾的方式。
#     *   **概括核心**：准确反映文章最关键的信息或冲突点。
#     *   **避免平庸**：不要使用“关于XXX的分析”这种平淡的表述。
# 3.  **核心标签提炼 (Core Tag Extraction)**：基于你的分析，直接创作2-5个全新的标签。这些标签必须是原文核心概念的精炼概括，并具备以下特点：
#     *   **高度概括性**：能抓住一个核心议题。**例如，对于讨论经济数据和现实感受差异的文章，`“GDP”`、`“经济体感”`、`“数据背离”` 都是很好的标签。**
#     *   **精炼且多样**：**优先使用最精炼的词语。标签长度不应拘泥于四字，请大胆结合使用2字、3字的短标签（如“通缩”、“内需”）和4字的核心概念标签，使标签组合更自然、易读。**
#     *   **覆盖关键点**：组合起来应能覆盖文章的主要讨论方向（如：经济数据、现实体感、未来对策等）。
# 4.  **整合输出**：将你创作的标题和提炼出的2-5个精华标签，按照【输出格式要求】返回。

# # 约束与要求
# *   **标题要求**：只能生成一个标题，必须精炼且吸引人。
# *   **标签数量**：严格控制在2到5个之间。
# *   **标签质量**：所有标签必须是你根据文本内容独立创作的，且必须精准、贴切、长短结合。
# *   **输出格式要求**：必须返回一个单一的JSON对象，结构必须为 `{{"title": "这里是生成的标题", "tags": ["tag1", "tag2", ...]}}`。

# ---

# ## 输入内容

# ### 待处理文本
# ```text
# {text}
# ```
# """
#     else:
#         tag_names = [tag.name for tag in tags]
#         prompt = f"""
# # 角色
# 你是一位资深的内容编辑和新媒体运营专家。你不仅擅长从复杂的文本中精准地提炼核心主题标签（Tag），还精通如何创作引人注目、概括精准的标题（Title）。

# # 任务
# 为我提供的【待处理文本】生成一个吸引人的标题（Title）和2-5个最相关的标签（Tags）。

# # 工作流程
# 1.  **深入分析**：首先，请仔细阅读并理解【待处理文本】的中心思想、关键论点、以及文本中呈现的核心矛盾或疑问（例如：亮眼数据与糟糕体感的反差）。
# 2.  **构思标题 (Title Crafting)**：基于你的分析，创作一个标题。这个标题应该：
#     *   **引人入胜**：能抓住读者眼球，引发好奇心。可以采用提问、制造悬念或点出矛盾的方式。
#     *   **概括核心**：准确反映文章最关键的信息或冲突点。
#     *   **避免平庸**：不要使用“关于XXX的分析”这种平淡的表述。
# 3.  **核心标签提炼 (Core Tag Extraction)**：基于你的分析，直接创作2-5个全新的标签。这些标签必须是原文核心概念的精炼概括，并具备以下特点：
#     *   **优先匹配**：将你分析出的核心概念与【已有Tag库】进行比对。如果文本内容与库中某个Tag高度相关，请优先使用。
#     *   **高度概括性**：能抓住一个核心议题。**例如，对于讨论经济数据和现实感受差异的文章，`“GDP”`、`“经济体感”`、`“数据背离”` 都是很好的标签。**
#     *   **精炼且多样**：**优先使用最精炼的词语。标签长度不应拘泥于四字，请大胆结合使用2字、3字的短标签（如“通缩”、“内需”）和4字的核心概念标签，使标签组合更自然、易读。**
#     *   **覆盖关键点**：组合起来应能覆盖文章的主要讨论方向（如：经济数据、现实体感、未来对策等）。
# 4.  **整合输出**：将你创作的标题和提炼出的2-5个精华标签，按照【输出格式要求】返回。

# # 约束与要求
# *   **标题要求**：只能生成一个标题，必须精炼且吸引人。
# *   **标签数量**：严格控制在2到5个之间。
# *   **标签相关性**：优先使用【已有Tag库】中的标签，新标签必须与文本高度相关。
# *   **标签质量**：所有标签必须是你根据文本内容独立创作的，且必须精准、贴切、长短结合。
# *   **输出格式要求**：必须返回一个单一的JSON对象，结构必须为 `{{"title": "这里是生成的标题", "tags": ["tag1", "tag2", ...]}}`。

# ---

# ## 输入内容

# ### 已有Tag库
# ```json
# {tag_names}
# ### 待处理文本
# ```text
# {text}
# """
#     try:
#         json_string = llm_call_qwen3_8b(
#             user_content=prompt,
#             system_content="你是一个智能助手，请根据用户输入的文字内容生成一个简洁明了的标题。",
#         )
#         data = json.loads(json_string)
#         return data["title"], data["tags"]
#     except Exception as e:
#         current_app.logger.error(f"生成标题失败: {str(e)}")
#         return "未能生成标题和tag，请重试"


def generate_title_only(text: str, user_id: int) -> str:
    """
    根据文字内容只生成标题

    Args:
        text: 用户输入的文字内容
        user_id: 用户ID

    Returns:
        str: 生成的标题
    """
    prompt = f"""
# 角色
你是一位资深的内容编辑和新媒体运营专家，擅长创作引人注目、概括精准的标题。

# 任务
为我提供的【待处理文本】生成一个吸引人的标题（Title）。

# 工作流程
1. **深入分析**：首先，请仔细阅读并理解【待处理文本】的中心思想、关键论点、以及文本中呈现的核心矛盾或疑问。
2. **构思标题**：基于你的分析，创作一个标题。这个标题应该：
   * **引人入胜**：能抓住读者眼球，引发好奇心。可以采用提问、制造悬念或点出矛盾的方式。
   * **概括核心**：准确反映文章最关键的信息或冲突点。
   * **避免平庸**：不要使用"关于XXX的分析"这种平淡的表述。

# 约束与要求
* **标题要求**：只能生成一个标题，必须精炼且吸引人。
* **输出格式要求**：必须返回一个单一的JSON对象，结构必须为 {{"title": "这里是生成的标题"}}。

---

## 输入内容

### 待处理文本
```text
{text}
```
"""

    try:
        json_string = llm_call_qwen3_8b(
            user_content=prompt,
            system_content="你是一个智能助手，请根据用户输入的文字内容生成一个简洁明了的标题。",
        )
        data = json.loads(json_string)
        return data["title"]
    except Exception as e:
        current_app.logger.error(f"生成标题失败: {str(e)}")
        return "未能生成标题，请重试"


def generate_tags_from_article(article_content: str, user_id: int) -> list[str]:
    """
    根据文章内容生成标签

    Args:
        article_content: 完整的文章内容（标题+内容+摘要）
        user_id: 用户ID

    Returns:
        list[str]: 生成的标签列表
    """
    # 查询tag表中与用户相关的标签
    tags = Tag.query.filter_by(user_id=user_id).all()

    if len(tags) == 0:
        prompt = f"""
# 角色
你是一位资深的内容编辑和新媒体运营专家，擅长从复杂的文本中精准地提炼核心主题标签。

# 任务
为我提供的【文章内容】生成2-5个最相关的标签（Tags）。所有标签都需要你根据文章内容从零开始创作。

# 工作流程
1. **深入分析**：首先，请仔细阅读并理解【文章内容】的中心思想、关键论点、以及文章中呈现的核心概念。
2. **核心标签提炼**：基于你的分析，直接创作2-5个全新的标签。这些标签必须是原文核心概念的精炼概括，并具备以下特点：
   * **高度概括性**：能抓住一个核心议题。
   * **精炼且多样**：优先使用最精炼的词语。标签长度不应拘泥于四字，请大胆结合使用2字、3字的短标签和4字的核心概念标签。
   * **覆盖关键点**：组合起来应能覆盖文章的主要讨论方向。

# 约束与要求
* **标签数量**：严格控制在2到5个之间。
* **标签质量**：所有标签必须是你根据文章内容独立创作的，且必须精准、贴切、长短结合。
* **输出格式要求**：必须返回一个单一的JSON对象，结构必须为 {{"tags": ["tag1", "tag2", ...]}}。

---

## 输入内容

### 文章内容
```text
{article_content}
```
"""
    else:
        tag_names = [tag.name for tag in tags]
        prompt = f"""
# 角色
你是一位资深的内容编辑和新媒体运营专家，擅长从复杂的文本中精准地提炼核心主题标签。

# 任务
为我提供的【文章内容】生成2-5个最相关的标签（Tags）。

# 工作流程
1. **深入分析**：首先，请仔细阅读并理解【文章内容】的中心思想、关键论点、以及文章中呈现的核心概念。
2. **核心标签提炼**：基于你的分析，直接创作2-5个标签。这些标签必须是原文核心概念的精炼概括，并具备以下特点：
   * **优先匹配**：将你分析出的核心概念与【已有Tag库】进行比对。如果文章内容与库中某个Tag高度相关，请优先使用。
   * **高度概括性**：能抓住一个核心议题。
   * **精炼且多样**：优先使用最精炼的词语。标签长度不应拘泥于四字，请大胆结合使用2字、3字的短标签和4字的核心概念标签。
   * **覆盖关键点**：组合起来应能覆盖文章的主要讨论方向。

# 约束与要求
* **标签数量**：严格控制在2到5个之间。
* **标签相关性**：优先使用【已有Tag库】中的标签，新标签必须与文章内容高度相关。
* **标签质量**：所有标签必须是你根据文章内容独立创作的，且必须精准、贴切、长短结合。
* **输出格式要求**：必须返回一个单一的JSON对象，结构必须为 {{"tags": ["tag1", "tag2", ...]}}。

---

## 输入内容

### 已有Tag库
```json
{tag_names}
```

### 文章内容
```text
{article_content}
```
"""

    try:
        # 打印prompt
        print(f"⚠️⚠️ prompt: {prompt}")
        json_string = llm_call_qwen3_8b(
            user_content=prompt,
            system_content="你是一个智能助手，请根据用户输入的文章内容生成相关的标签。",
        )
        data = json.loads(json_string)
        return data["tags"]
    except Exception as e:
        current_app.logger.error(f"生成标签失败: {str(e)}")
        return []


def add_tags_to_article(article_id: int, tag_names: list[str], user_id: int):
    """
    为文章添加标签

    Args:
        article_id: 文章ID
        tag_names: 标签名称列表
        user_id: 用户ID
    """
    try:
        # 处理标签
        tag_ids = []
        for tag_name in tag_names:
            # 检查用户是否已有该标签
            existing_tag = Tag.query.filter_by(user_id=user_id, name=tag_name).first()

            if existing_tag:
                # 使用现有标签
                tag_ids.append(existing_tag.id)
            else:
                # 创建新标签
                new_tag = Tag(user_id=user_id, name=tag_name)
                db.session.add(new_tag)
                db.session.flush()  # 获取标签ID
                tag_ids.append(new_tag.id)

        # 创建文章-标签关系
        for tag_id in tag_ids:
            # 检查关系是否已存在，避免重复
            existing_relation = ArticleTag.query.filter_by(
                article_id=article_id, tag_id=tag_id
            ).first()

            if not existing_relation:
                article_tag = ArticleTag(article_id=article_id, tag_id=tag_id)
                db.session.add(article_tag)

        current_app.logger.info(
            f"为文章{article_id}添加了{len(tag_names)}个标签: {tag_names}"
        )

    except Exception as e:
        current_app.logger.error(f"为文章添加标签失败: {str(e)}")
        raise e


# def create_article_and_tags(title: str, tag_names: list[str], user_id: int, task_id: int) -> int:
#     """
#     创建文章和标签的数据库记录

#     Args:
#         title: 文章标题
#         tag_names: 标签名称列表
#         user_id: 用户ID
#         task_id: 任务ID

#     Returns:
#         int: 创建的文章ID
#     """
#     try:
#         # 1. 创建文章记录
#         article = Article(
#             author_id=user_id,
#             source_task_id=task_id,
#             title=title,
#             status="archived",  # 设置为archived状态
#             finished_at=None    # finished_at为空，因为任务未完成
#         )
#         db.session.add(article)
#         db.session.flush()  # 获取文章ID

#         # 2. 处理标签
#         tag_ids = []
#         for tag_name in tag_names:
#             # 检查用户是否已有该标签
#             existing_tag = Tag.query.filter_by(user_id=user_id, name=tag_name).first()

#             if existing_tag:
#                 # 使用现有标签
#                 tag_ids.append(existing_tag.id)
#             else:
#                 # 创建新标签
#                 new_tag = Tag(
#                     user_id=user_id,
#                     name=tag_name
#                 )
#                 db.session.add(new_tag)
#                 db.session.flush()  # 获取标签ID
#                 tag_ids.append(new_tag.id)

#         # 3. 创建文章-标签关系
#         for tag_id in tag_ids:
#             article_tag = ArticleTag(
#                 article_id=article.id,
#                 tag_id=tag_id
#             )
#             db.session.add(article_tag)

#         return article.id

#     except Exception as e:
#         current_app.logger.error(f"创建文章和标签失败: {str(e)}")
#         raise e


@article_bp.route("/articles/tasks", methods=["GET"])
def get_tasks_by_user_and_month():
    """
    通过user_id和月份查看所有任务信息及其状态
    ---
    parameters:
        - name: user_id
          in: query
          required: true
          type: integer
          description: 用户ID
        - name: year
          in: query
          required: true
          type: integer
          description: 年份 (如: 2025)
        - name: month
          in: query
          required: true
          type: integer
          description: 月份 (1-12)
    responses:
        200:
            description: 成功获取任务列表
            schema:
                type: object
                properties:
                    message:
                        type: string
                    total:
                        type: integer
                    tasks:
                        type: array
                        items:
                            type: object
                            properties:
                                task_id:
                                    type: integer
                                user_id:
                                    type: integer
                                summary_status:
                                    type: integer
                                langgraph_status:
                                    type: integer
                                created_at:
                                    type: string
                                updated_at:
                                    type: string
        400:
            description: 请求参数错误
        404:
            description: 用户不存在
        500:
            description: 服务器内部错误
    """
    try:
        user_id = request.args.get("user_id", type=int)
        year = request.args.get("year", type=int)
        month = request.args.get("month", type=int)

        # 参数验证
        if not user_id or not year or not month:
            return {"message": "user_id、year和month参数不能为空"}, 400

        if month < 1 or month > 12:
            return {"message": "月份必须在1-12之间"}, 400

        if year < 2020 or year > 2030:
            return {"message": "年份必须在2020-2030之间"}, 400

        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return {"message": "用户不存在"}, 404

        # 查询指定用户和月份的任务
        tasks = (
            GenerationTask.query.filter(
                GenerationTask.user_id == user_id,
                extract("year", GenerationTask.created_at) == year,
                extract("month", GenerationTask.created_at) == month,
            )
            .order_by(GenerationTask.created_at.desc())
            .all()
        )

        # 格式化返回数据
        task_list = []
        for task in tasks:
            task_data = {
                "task_id": task.id,
                "user_id": task.user_id,
                "summary_status": task.summary_status,
                "langgraph_status": task.langgraph_status,
                "error_message": task.error_message,
                "created_at": task.created_at.isoformat(),
                "updated_at": task.updated_at.isoformat(),
            }
            task_list.append(task_data)

        return {
            "message": "获取任务列表成功",
            "total": len(task_list),
            "tasks": task_list,
        }, 200

    except Exception as e:
        current_app.logger.error(f"获取任务列表失败: {str(e)}")
        return {"message": "获取任务列表失败，请稍后重试"}, 500


@article_bp.route("/articles/tasks/<int:task_id>", methods=["GET"])
def get_task_status(task_id):
    """
    通过task_id查看该任务的状态
    ---
    parameters:
        - name: task_id
          in: path
          required: true
          type: integer
          description: 任务ID
    responses:
        200:
            description: 成功获取任务状态
            schema:
                type: object
                properties:
                    message:
                        type: string
                    task:
                        type: object
                        properties:
                            task_id:
                                type: integer
                            user_id:
                                type: integer
                            summary_status:
                                type: integer
                            langgraph_status:
                                type: integer
                            error_message:
                                type: string
                            created_at:
                                type: string
                            updated_at:
                                type: string
                            status_description:
                                type: object
                                properties:
                                    summary:
                                        type: string
                                    tag:
                                        type: string
                                    langgraph:
                                        type: string
        404:
            description: 任务不存在
        500:
            description: 服务器内部错误
    """
    try:
        # 查询任务
        task = GenerationTask.query.get(task_id)
        if not task:
            return {"message": "任务不存在"}, 404

        # 状态描述映射
        status_map = {0: "pending", 1: "processing", 2: "completed", 3: "failed"}

        # 格式化返回数据
        task_data = {
            "task_id": task.id,
            "user_id": task.user_id,
            "summary_status": task.summary_status,
            "langgraph_status": task.langgraph_status,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "status_description": {
                "summary": status_map.get(task.summary_status, "unknown"),
                "langgraph": status_map.get(task.langgraph_status, "unknown"),
            },
        }

        return {"message": "获取任务状态成功", "task": task_data}, 200

    except Exception as e:
        current_app.logger.error(f"获取任务状态失败: {str(e)}")
        return {"message": "获取任务状态失败，请稍后重试"}, 500


@article_bp.route("/articles/my-articles", methods=["GET"])
def get_my_articles():
    """
    用户获取自己的所有文章概览
    ---
    parameters:
        - name: user_id
          in: query
          required: true
          type: integer
          description: 用户ID
        - name: page
          in: query
          required: false
          type: integer
          default: 1
          description: 页码
        - name: per_page
          in: query
          required: false
          type: integer
          default: 10
          description: 每页数量
    responses:
        200:
            description: 成功获取文章列表
        400:
            description: 请求参数错误
        404:
            description: 用户不存在
        500:
            description: 服务器内部错误
    """
    try:
        user_id = request.args.get("user_id", type=int)
        page = request.args.get("page", type=int, default=1)
        per_page = request.args.get("per_page", type=int, default=10)

        if not user_id:
            return {"message": "用户ID不能为空"}, 400

        if page < 1 or per_page < 1 or per_page > 50:
            return {"message": "页码和每页数量参数不合法"}, 400

        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return {"message": "用户不存在"}, 404

        # 查询用户的文章（分页）
        articles_query = Article.query.filter_by(author_id=user_id).order_by(
            Article.created_at.desc()
        )
        total = articles_query.count()
        articles = articles_query.offset((page - 1) * per_page).limit(per_page).all()

        # 格式化返回数据
        article_list = []
        for article in articles:
            # 获取文章标签
            tags = []
            for tag in article.tags:
                tags.append({"id": tag.id, "name": tag.name})

            article_data = {
                "id": article.id,
                "title": article.title,
                "summary": article.summary,
                "status": article.status,
                "tags": tags,
                "created_at": article.created_at.isoformat(),
                "updated_at": article.updated_at.isoformat(),
                "finished_at": (
                    article.finished_at.isoformat() if article.finished_at else None
                ),
            }
            article_list.append(article_data)

        return {
            "message": "获取文章列表成功",
            "total": total,
            "page": page,
            "per_page": per_page,
            "articles": article_list,
        }, 200

    except Exception as e:
        current_app.logger.error(f"获取用户文章失败: {str(e)}")
        return {"message": "获取文章列表失败，请稍后重试"}, 500


@article_bp.route("/articles/recommendations", methods=["GET"])
def get_article_recommendations():
    """
    用户获取别人文章概览的推荐列表
    ---
    parameters:
        - name: user_id
          in: query
          required: true
          type: integer
          description: 当前用户ID
        - name: page
          in: query
          required: false
          type: integer
          default: 1
          description: 页码
        - name: per_page
          in: query
          required: false
          type: integer
          default: 10
          description: 每页数量
    responses:
        200:
            description: 成功获取推荐文章列表
        400:
            description: 请求参数错误
        404:
            description: 用户不存在
        500:
            description: 服务器内部错误
    """
    try:
        user_id = request.args.get("user_id", type=int)
        page = request.args.get("page", type=int, default=1)
        per_page = request.args.get("per_page", type=int, default=10)

        if not user_id:
            return {"message": "用户ID不能为空"}, 400

        if page < 1 or per_page < 1 or per_page > 50:
            return {"message": "页码和每页数量参数不合法"}, 400

        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return {"message": "用户不存在"}, 404

        # Mock推荐逻辑：获取其他用户的已发布文章，按时间倒序
        articles_query = Article.query.filter(
            Article.author_id != user_id, Article.status == "published"
        ).order_by(Article.created_at.desc())

        total = articles_query.count()
        articles = articles_query.offset((page - 1) * per_page).limit(per_page).all()

        # 格式化返回数据
        article_list = []
        for article in articles:
            # 获取作者信息
            author = User.query.get(article.author_id)
            if not author:
                current_app.logger.warning(
                    f"文章ID {article.id} 的作者ID {article.author_id} 不存在"
                )
                continue  # 跳过作者不存在的文章

            # 获取文章标签
            tags = []
            for tag in article.tags:
                tags.append({"id": tag.id, "name": tag.name})

            article_data = {
                "id": article.id,
                "title": article.title,
                "summary": article.summary,
                "tags": tags,
                "author": {
                    "id": author.id,
                    "username": author.username,
                    "avatar_url": author.avatar_url,
                },
                "created_at": article.created_at.isoformat(),
                "finished_at": (
                    article.finished_at.isoformat() if article.finished_at else None
                ),
            }
            article_list.append(article_data)

        return {
            "message": "获取推荐文章成功",
            "total": total,
            "page": page,
            "per_page": per_page,
            "articles": article_list,
        }, 200

    except Exception as e:
        current_app.logger.error(f"获取推荐文章失败: {str(e)}")
        return {"message": "获取推荐文章失败，请稍后重试"}, 500


@article_bp.route("/articles/<int:article_id>", methods=["GET"])
def get_article_detail(article_id):
    """
    获取文章详情和相关推荐
    ---
    parameters:
        - name: article_id
          in: path
          required: true
          type: integer
          description: 文章ID
        - name: user_id
          in: query
          required: false
          type: integer
          description: 当前用户ID（用于个性化推荐）
    responses:
        200:
            description: 成功获取文章详情
        404:
            description: 文章不存在
        500:
            description: 服务器内部错误
    """
    try:
        user_id = request.args.get("user_id", type=int)

        # 查询文章
        article = Article.query.get(article_id)
        if not article:
            return {"message": "文章不存在"}, 404

        # 获取作者信息
        author = User.query.get(article.author_id)
        if not author:
            return {"message": "文章作者不存在"}, 404

        # 获取文章标签
        tags = []
        for tag in article.tags:
            tags.append({"id": tag.id, "name": tag.name})

        # 获取文章引用的其他文章
        referenced_articles = []
        references = ArticleRelationship.query.filter_by(
            citing_article_id=article_id
        ).all()
        for ref in references:
            ref_article = Article.query.get(ref.referenced_article_id)
            if ref_article:
                referenced_articles.append(
                    {"id": ref_article.id, "title": ref_article.title}
                )

        # 获取引用本文章的其他文章
        citing_articles = []
        citations = ArticleRelationship.query.filter_by(
            referenced_article_id=article_id
        ).all()
        for cite in citations:
            cite_article = Article.query.get(cite.citing_article_id)
            if cite_article:
                citing_articles.append(
                    {"id": cite_article.id, "title": cite_article.title}
                )

        # Mock相关推荐：获取同作者的其他文章或相似标签的文章
        recommendations = []
        rec_query = (
            Article.query.filter(
                Article.id != article_id, Article.status == "published"
            )
            .order_by(Article.created_at.desc())
            .limit(5)
        )

        for rec_article in rec_query:
            rec_author = User.query.get(rec_article.author_id)
            if not rec_author:
                continue  # 跳过作者不存在的文章

            rec_tags = [{"id": tag.id, "name": tag.name} for tag in rec_article.tags]

            recommendations.append(
                {
                    "id": rec_article.id,
                    "title": rec_article.title,
                    "summary": rec_article.summary,
                    "tags": rec_tags,
                    "author": {
                        "id": rec_author.id,
                        "username": rec_author.username,
                        "avatar_url": rec_author.avatar_url,
                    },
                    "created_at": rec_article.created_at.isoformat(),
                }
            )

        # 构建返回数据
        article_data = {
            "id": article.id,
            "title": article.title,
            "summary": article.summary,
            "content": article.content,
            "status": article.status,
            "tags": tags,
            "author": {
                "id": author.id,
                "username": author.username,
                "email": author.email,
                "avatar_url": author.avatar_url,
            },
            "referenced_articles": referenced_articles,
            "citing_articles": citing_articles,
            "created_at": article.created_at.isoformat(),
            "updated_at": article.updated_at.isoformat(),
            "finished_at": (
                article.finished_at.isoformat() if article.finished_at else None
            ),
            "recommendations": recommendations,
        }

        return {"message": "获取文章详情成功", "article": article_data}, 200

    except Exception as e:
        current_app.logger.error(f"获取文章详情失败: {str(e)}")
        return {"message": "获取文章详情失败，请稍后重试"}, 500
