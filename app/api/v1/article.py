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
    您是一位资深的内容编辑专家，擅长撰写精准传达核心信息的标题。

    # 任务
    基于提供的【待处理文本】，创作一个直接明确的标题（Title）。

    # 工作流程
    1. 文本分析：仔细解析文本的核心论点、关键数据和主要结论
    2. 标题创作要求：
       * 直述核心：用主谓结构直接呈现核心发现或结论
       * 信息完整：包含关键主体+核心动作+量化结果（如有）
       * 语言规范：使用书面语，禁止夸张副词和情绪化表达

    # 技术规范
    1. 禁止使用以下手法：
       - 疑问句式
       - 悬念设置
       - 隐藏关键信息
       - 夸张比较（"震惊"、"惊人"等）
       - 过度承诺（"必看"、"改变认知"等）

    2. 格式要求：
       - 长度控制在8-18字之间
       - 使用主谓宾完整结构
       - 输出纯JSON格式：{{"title": "标题内容"}}

    # 示例参考
    正确案例：{{"title": "A市6月房价环比下降2.3% 刚需户型成交量领跌"}}
    错误案例：{{"title": "楼市惊现逆转！这个信号预示房价要崩？"}}

    ## 待处理文本
    {text}
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
        资深内容策略专家，擅长提炼文本核心概念为概括性标签

        # 任务
        为【文章内容】生成2-5个高度概括的标签（Tags），要求像小红书标签那样简洁通用

        # 核心原则
        1. **概括性优先**：每个标签必须代表一个核心概念类别（如"旅行"而非"三亚自由行"，"天气"而非"晴空万里"）
        2. **简洁表达**：
           - 主要使用2-3字短标签（占60%以上）
           - 必要时用4字标签（不超过40%）
           - 禁用具体描述性词汇
        3. **概念覆盖**：组合标签需覆盖文章核心主题

        # 工作流程
        1. 识别内容中的核心概念类别（如旅行/科技/健康）
        2. 提炼为最简概括词（避免细节描述）
        3. 确保标签具备通用性和复用性

        # 硬性要求
        - 标签数量：2-5个
        - 输出格式：严格使用 {{"tags": ["标签1", "标签2"]}} 
        - 禁止：具体描述、专有名词、细节特征

        ### 文章内容
        ```text
        {article_content}
        ```
        """
    else:
        tag_names = [tag.name for tag in tags]
        prompt = f"""
        # 角色
        资深内容策略专家，擅长复用现有标签体系

        # 任务
        为【文章内容】匹配2-5个标签，优先使用【已有Tag库】中的概括性标签

        # 核心原则
        1. **标签优先级**：
           - 首选：直接复用【已有Tag库】中匹配的概括性标签
           - 次选：仅当库中无合适标签时，创建新概括标签
        2. **概括性标准**：
           - 所有标签必须代表概念类别
           - 新标签需符合2-3字为主原则
           - 禁用具体描述（如用"穿搭"而非"牛仔外套"）

        # 工作流程
        1. 检查内容核心概念是否被【已有Tag库】覆盖
        2. 优先选择库中匹配的概括性标签
        3. 必要时创建新标签（需符合概括性原则）

        # 硬性要求
        - 复用率：库中标签优先使用率 ≥70%
        - 新标签需通过概括性测试：能否适用于同类内容
        - 输出格式：{{"tags": ["标签1", "标签2"]}}

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

        # 获取创建和更新的文章信息
        created_articles_info = []
        updated_articles_info = []
        
        # 处理创建的文章
        if task.created_articles:
            for article_id in task.created_articles:
                article = Article.query.get(article_id)
                if article:
                    # 获取文章标签
                    tags = []
                    for tag in article.tags:
                        tags.append({"id": tag.id, "name": tag.name})
                    
                    article_info = {
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
                    created_articles_info.append(article_info)
        
        # 处理更新的文章
        if task.updated_articles:
            for article_id in task.updated_articles:
                article = Article.query.get(article_id)
                if article:
                    # 获取文章标签
                    tags = []
                    for tag in article.tags:
                        tags.append({"id": tag.id, "name": tag.name})
                    
                    article_info = {
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
                    updated_articles_info.append(article_info)

        # 格式化返回数据
        task_data = {
            "task_id": task.id,
            "user_id": task.user_id,
            "summary_status": task.summary_status,
            "langgraph_status": task.langgraph_status,
            "error_message": task.error_message,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "created_articles_info": created_articles_info,
            "updated_articles_info": updated_articles_info,
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
        - name: tag_id
          in: query
          required: false
          type: integer
          description: 标签ID，用于筛选特定标签的文章
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
            description: 用户不存在或标签不存在
        500:
            description: 服务器内部错误
    """
    try:
        user_id = request.args.get("user_id", type=int)
        tag_id = request.args.get("tag_id", type=int)
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

        # 如果提供了tag_id，验证标签是否存在且属于该用户
        if tag_id:
            tag = Tag.query.filter_by(id=tag_id, user_id=user_id).first()
            if not tag:
                return {"message": "标签不存在或不属于该用户"}, 404

        # 构建查询条件
        if tag_id:
            # 通过tag_id筛选文章：需要连接ArticleTag表
            articles_query = (
                Article.query
                .join(ArticleTag, Article.id == ArticleTag.article_id)
                .filter(
                    Article.author_id == user_id,
                    ArticleTag.tag_id == tag_id
                )
                .order_by(Article.created_at.desc())
            )
        else:
            # 返回用户的所有文章
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


@article_bp.route("/articles/user-records", methods=["GET"])
def get_user_records():
    """
    查询指定用户下的所有records内容及其对应的task状态信息
    ---
    parameters:
        - name: user_id
          in: query
          required: true
          type: integer
          description: 用户ID
    responses:
        200:
            description: 成功获取用户记录列表
            schema:
                type: object
                properties:
                    message:
                        type: string
                    total:
                        type: integer
                    records:
                        type: array
                        items:
                            type: object
                            properties:
                                record_id:
                                    type: integer
                                transcript:
                                    type: string
                                title:
                                    type: string
                                record_created_at:
                                    type: string
                                    format: date-time
                                task:
                                    type: object
                                    properties:
                                        task_id:
                                            type: integer
                                        summary_status:
                                            type: integer
                                        langgraph_status:
                                            type: integer
                                        error_message:
                                            type: string
                                        created_articles:
                                            type: array
                                            items:
                                                type: integer
                                        updated_articles:
                                            type: array
                                            items:
                                                type: integer
                                        task_created_at:
                                            type: string
                                            format: date-time
                                        task_updated_at:
                                            type: string
                                            format: date-time
        400:
            description: 请求参数错误
        404:
            description: 用户不存在
        500:
            description: 服务器内部错误
    """
    try:
        user_id = request.args.get("user_id", type=int)

        if not user_id:
            return {"message": "用户ID不能为空"}, 400

        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return {"message": "用户不存在"}, 404

        # 查询用户的所有音频记录及其关联的任务
        # 使用LEFT JOIN确保即使没有对应的task也能返回record
        records_query = (
            db.session.query(UserAudioRecord, GenerationTask)
            .outerjoin(TaskRecordsMapping, UserAudioRecord.id == TaskRecordsMapping.record_id)
            .outerjoin(GenerationTask, TaskRecordsMapping.task_id == GenerationTask.id)
            .filter(UserAudioRecord.user_id == user_id)
            .order_by(UserAudioRecord.created_at.desc())
        )

        results = records_query.all()

        # 格式化返回数据
        record_list = []
        for record, task in results:
            record_data = {
                "record_id": record.id,
                "transcript": record.transcript,
                "title": record.title,
                "record_created_at": record.created_at.isoformat(),
                "task": None
            }

            # 如果存在关联的任务，添加任务信息
            if task:
                record_data["task"] = {
                    "task_id": task.id,
                    "summary_status": task.summary_status,
                    "langgraph_status": task.langgraph_status,
                    "error_message": task.error_message,
                    "created_articles": task.created_articles or [],
                    "updated_articles": task.updated_articles or [],
                    "task_created_at": task.created_at.isoformat(),
                    "task_updated_at": task.updated_at.isoformat()
                }

            record_list.append(record_data)

        return {
            "message": "获取用户记录成功",
            "total": len(record_list),
            "records": record_list,
        }, 200

    except Exception as e:
        current_app.logger.error(f"获取用户记录失败: {str(e)}")
        return {"message": "获取用户记录失败，请稍后重试"}, 500


@article_bp.route("/articles/relationships", methods=["GET"])
def get_article_relationships():
    """
    获取所有文章引用关系
    ---
    parameters:
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
          default: 20
          description: 每页数量
        - name: citing_article_id
          in: query
          required: false
          type: integer
          description: 引用文章ID（筛选条件）
        - name: referenced_article_id
          in: query
          required: false
          type: integer
          description: 被引用文章ID（筛选条件）
    responses:
        200:
            description: 成功获取文章关系列表
            schema:
                type: object
                properties:
                    message:
                        type: string
                    total:
                        type: integer
                    page:
                        type: integer
                    per_page:
                        type: integer
                    relationships:
                        type: array
                        items:
                            type: object
                            properties:
                                id:
                                    type: integer
                                citing_article:
                                    type: object
                                    properties:
                                        id:
                                            type: integer
                                        title:
                                            type: string
                                        author_name:
                                            type: string
                                referenced_article:
                                    type: object
                                    properties:
                                        id:
                                            type: integer
                                        title:
                                            type: string
                                        author_name:
                                            type: string
                                created_at:
                                    type: string
                                    format: date-time
        400:
            description: 请求参数错误
        500:
            description: 服务器内部错误
    """
    try:
        page = request.args.get("page", type=int, default=1)
        per_page = request.args.get("per_page", type=int, default=20)
        citing_article_id = request.args.get("citing_article_id", type=int)
        referenced_article_id = request.args.get("referenced_article_id", type=int)

        if page < 1 or per_page < 1 or per_page > 100:
            return {"message": "页码和每页数量参数不合法"}, 400

        # 构建查询条件
        query = ArticleRelationship.query
        
        if citing_article_id:
            query = query.filter(ArticleRelationship.citing_article_id == citing_article_id)
        
        if referenced_article_id:
            query = query.filter(ArticleRelationship.referenced_article_id == referenced_article_id)

        # 按创建时间倒序排列
        query = query.order_by(ArticleRelationship.created_at.desc())
        
        # 分页查询
        total = query.count()
        relationships = query.offset((page - 1) * per_page).limit(per_page).all()

        # 格式化返回数据
        relationship_list = []
        for rel in relationships:
            # 获取引用文章信息
            citing_article = Article.query.get(rel.citing_article_id)
            citing_author = User.query.get(citing_article.author_id) if citing_article else None
            
            # 获取被引用文章信息
            referenced_article = Article.query.get(rel.referenced_article_id)
            referenced_author = User.query.get(referenced_article.author_id) if referenced_article else None

            relationship_data = {
                "id": rel.id,
                "citing_article": {
                    "id": citing_article.id if citing_article else None,
                    "title": citing_article.title if citing_article else "文章已删除",
                    "author_name": citing_author.username if citing_author else "作者未知"
                },
                "referenced_article": {
                    "id": referenced_article.id if referenced_article else None,
                    "title": referenced_article.title if referenced_article else "文章已删除",
                    "author_name": referenced_author.username if referenced_author else "作者未知"
                },
                "created_at": rel.created_at.isoformat()
            }
            relationship_list.append(relationship_data)

        return {
            "message": "获取文章关系列表成功",
            "total": total,
            "page": page,
            "per_page": per_page,
            "relationships": relationship_list,
        }, 200

    except Exception as e:
        current_app.logger.error(f"获取文章关系列表失败: {str(e)}")
        return {"message": "获取文章关系列表失败，请稍后重试"}, 500


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

        # 获取该文章引用的文章的详细概览信息
        recommendations = []
        references = ArticleRelationship.query.filter_by(
            citing_article_id=article_id
        ).all()
        
        for ref in references:
            ref_article = Article.query.get(ref.referenced_article_id)
            if not ref_article:
                continue  # 跳过已删除的文章
                
            ref_author = User.query.get(ref_article.author_id)
            if not ref_author:
                continue  # 跳过作者不存在的文章

            ref_tags = [{"id": tag.id, "name": tag.name} for tag in ref_article.tags]

            recommendations.append(
                {
                    "id": ref_article.id,
                    "title": ref_article.title,
                    "summary": ref_article.summary,
                    "tags": ref_tags,
                    "author": {
                        "id": ref_author.id,
                        "username": ref_author.username,
                        "avatar_url": ref_author.avatar_url,
                    },
                    "created_at": ref_article.created_at.isoformat(),
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
