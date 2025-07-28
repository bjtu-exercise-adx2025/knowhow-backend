import json
import re
import unicodedata
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

        # 基础参数验证
        if not user_id or not text:
            return {"message": "用户ID和文字内容不能为空"}, 400

        if not isinstance(user_id, int):
            return {"message": "用户ID必须为整数"}, 400

        if not isinstance(text, str) or len(text.strip()) == 0:
            return {"message": "文字内容不能为空"}, 400

        # 文字长度验证
        text_cleaned = text.strip()
        text_length = len(text_cleaned)

        # 设置长度限制（可根据需要调整）
        MIN_TEXT_LENGTH = 10
        MAX_TEXT_LENGTH = 1000

        if text_length < MIN_TEXT_LENGTH:
            return {"message": f"文字内容至少需要{MIN_TEXT_LENGTH}个字符"}, 400

        if text_length > MAX_TEXT_LENGTH:
            return {"message": f"文字内容不能超过{MAX_TEXT_LENGTH}个字符"}, 400

        # 内容安全检查
        is_safe, safety_message = validate_text_content(text_cleaned)
        if not is_safe:
            return {"message": safety_message}, 400

        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return {"message": "用户不存在"}, 404

        # 1. 生成标题
        title = generate_title_only(text_cleaned, user_id)

        # 2. 创建音频记录（复用表结构存储文字），保存标题
        audio_record = UserAudioRecord(
            user_id=user_id, transcript=text_cleaned, title=title
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


def validate_text_content(text: str) -> tuple[bool, str]:
    """
    验证文本内容的安全性

    Args:
        text: 要验证的文本

    Returns:
        Tuple[bool, str]: (是否安全, 错误信息)
    """
    # # 1. 检查是否包含除中英文外的其他语言
    # if not is_chinese_english_only(text):
    #     return False, "文本只能包含中文和英文字符"

    # 2. 检查特殊符号和字符
    # if contains_suspicious_symbols(text):
    #     return False, "文本包含不允许的特殊字符或符号"

    # 3. 检查敏感词
    if contains_sensitive_words(text):
        return False, "文本包含敏感内容，请修改后重试"

    # 4. 检查注入攻击模式
    if contains_injection_patterns(text):
        return False, "文本包含潜在的安全风险内容"

    return True, ""


def is_chinese_english_only(text: str) -> bool:
    """
    检查文本是否只包含中英文字符
    """
    # 允许的字符范围
    allowed_pattern = re.compile(r'^[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff'  # 中文字符
                                 r'a-zA-Z'  # 英文字母
                                 r'0-9'  # 数字
                                 r'\s'  # 空白字符
                                 r'.,!?;:()[]{}"\'-'  # 基本标点符号
                                 r'，。！？；：（）【】""''、'  # 中文标点
                                 r']+$')

    return bool(allowed_pattern.match(text))


def contains_suspicious_symbols(text: str) -> bool:
    """
    检查是否包含可疑的特殊符号
    """
    # 不允许的特殊字符模式
    suspicious_patterns = [
        r'[<>{}\\|`~#$%^&*+=]',  # 可能用于代码注入的符号
        r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]',  # 控制字符
        r'[\u2000-\u206f\u2e00-\u2e7f]',  # 特殊空格和标点
        r'[\ufeff\ufffe\uffff]',  # BOM和其他特殊字符
    ]

    for pattern in suspicious_patterns:
        if re.search(pattern, text):
            return True

    return False


def contains_sensitive_words(text: str) -> bool:
    """
    检查是否包含敏感词
    """
    # 敏感词列表（这里只是示例，实际使用时应该从配置文件或数据库读取）
    sensitive_words = [
        # AI攻击相关
        'ignore previous instructions',
        'forget everything above',
        'system prompt',
        'jailbreak',
        'prompt injection',
        'override system',
        'act as',
        'pretend you are',

        # 中文攻击模式
        '忽略之前的指令',
        '忘记上面的内容',
        '系统提示',
        '扮演',
        '假装你是',
        '绕过限制',

        # SQL注入相关
        'drop table',
        'delete from',
        'union select',
        'insert into',
        'update set',

        # 其他敏感内容可以根据具体业务需求添加
    ]

    text_lower = text.lower()
    for word in sensitive_words:
        if word.lower() in text_lower:
            return True

    return False


def contains_injection_patterns(text: str) -> bool:
    """
    检查是否包含注入攻击模式
    """
    injection_patterns = [
        r'<script[^>]*>.*?</script>',  # XSS脚本
        r'javascript:',  # JavaScript协议
        r'on\w+\s*=',  # 事件处理器
        r'eval\s*\(',  # eval函数
        r'exec\s*\(',  # exec函数
        r'system\s*\(',  # system调用
        r'\$\{.*?\}',  # 模板注入
        r'\{\{.*?\}\}',  # 模板注入
        r'#{.*?}',  # 表达式注入
        r'@\{.*?\}',  # OGNL注入
    ]

    for pattern in injection_patterns:
        if re.search(pattern, text, re.IGNORECASE | re.DOTALL):
            return True

    return False


def clean_text(text: str) -> str:
    """
    清理文本，移除潜在的危险字符
    """
    # 移除控制字符
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\r\t')

    # 标准化Unicode字符
    text = unicodedata.normalize('NFKC', text)

    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text.strip())

    return text


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
       * 只保留你的核心发现或结论，**不要添加任何其他内容，不要猜测或添加任何其他内容**
       * 由于待处理文本是语音转文字，因此可能会有不准确的地方，你可以根据上下文进行修正

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
你是一位专业的知识管理专家和信息架构师，擅长将零散信息归纳到高度概括的核心分类中。

# 任务
为我提供的【文章内容】归纳出1-3个最核心的顶级分类标签（Tags）。所有标签都需要你根据文章内容从零开始创作。必须至少生成一个标签。

# 工作流程
1. **理解主旨**：深入阅读【文章内容】，精准把握其探讨的核心领域和主题。
2. **归纳分类**：将文章主旨映射到1-3个广为人知、高度概括的通用分类标签上。你需要从零开始创建这些分类标签。
3. 如果用户的内容没有明确的核心领域和主题，则返回空数组，不用生成标签。

# 约束与要求
*   **表标签层级**：必须是顶级、宽泛的分类标签，例如“科技”、“健康”、“财经”、“教育”。绝对不要生成“AI大模型”、“减肥食谱”这类具体或垂直的细分标签。
*   **标签分类示例**：你生成的分类应该像这些例子一样宽泛：`运动`, `理财`, `饮食`, `医疗`, `创业`, `心理`, `职场`, `数码`, `汽车`, `旅行`。
*   **数量限制**：严格控制在1到3个之间。
*   **输出格式**：必须返回一个单一的JSON对象，结构必须为 {{"tags": ["tag1", "tag2", ...]}}。

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
你是一位专业的知识管理专家和信息架构师，擅长将零散信息归纳到高度概括的核心分类中。

# 任务
为我提供的【文章内容】生成1-3个最相关的标签（Tags）。

# 工作流程
1. **理解主旨**：深入阅读【文章内容】，精准把握其探讨的核心领域和主题。
2. **核心标签提炼**：基于你的分析，直接创作1-3个标签。这些标签必须是原文核心概念的精炼概括，并具备以下特点：
   * **优先匹配**：将你分析出的核心概念与【已有Tag库】进行比对。如果文章内容与库中某个Tag高度相关，请优先使用。
   * **高度概括性**：将文章主旨映射到1-3个广为人知、高度概括的通用分类标签上。
3. 如果用户的内容没有明确的核心领域和主题，则返回空数组，不用生成标签。

# 约束与要求
*   **表标签层级**：必须是顶级、宽泛的分类标签，例如“科技”、“健康”、“财经”、“教育”。绝对不要生成“AI大模型”、“减肥食谱”这类具体或垂直的细分标签。
*   **标签分类示例**：你生成的分类应该像这些例子一样宽泛：`运动`, `理财`, `饮食`, `医疗`, `创业`, `心理`, `职场`, `数码`, `汽车`, `旅行`。
*   **数量限制**：严格控制在1到3个之间。
*   **输出格式**：必须返回一个单一的JSON对象，结构必须为 {{"tags": ["tag1", "tag2", ...]}}。

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
        # print(f"⚠️⚠️ prompt: {prompt}")
        json_string = llm_call_qwen3_8b(
            user_content=prompt,
            system_content="你是一个智能助手，请根据用户要求，为文章进行高阶分类。",
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
        # 如果标签列表为空，添加"其他"
        if not tag_names or len(tag_names) == 0:
            tag_names = ["其他"]
            current_app.logger.info(f"文章{article_id}没有生成标签，自动添加'其他'标签")

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
                            article.finished_at.isoformat()
                            if article.finished_at
                            else None
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
                            article.finished_at.isoformat()
                            if article.finished_at
                            else None
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
                Article.query.join(ArticleTag, Article.id == ArticleTag.article_id)
                .filter(Article.author_id == user_id, ArticleTag.tag_id == tag_id)
                .order_by(Article.updated_at.desc())
            )
        else:
            # 返回用户的所有文章
            articles_query = Article.query.filter_by(author_id=user_id).order_by(
                Article.updated_at.desc()
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
        ).order_by(Article.finished_at.desc())

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
            .outerjoin(
                TaskRecordsMapping, UserAudioRecord.id == TaskRecordsMapping.record_id
            )
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
                "task": None,
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
                    "task_updated_at": task.updated_at.isoformat(),
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
    获取指定用户的标签、文章及其引用关系
    ---
    parameters:
        - name: user_id
          in: query
          required: true
          type: integer
          description: 用户ID
    responses:
        200:
            description: 成功获取用户标签和文章关系信息
            schema:
                type: object
                properties:
                    user_id:
                        type: integer
                    username:
                        type: string
                    tags:
                        type: array
                        items:
                            type: object
                            properties:
                                id:
                                    type: integer
                                name:
                                    type: string
                                articles:
                                    type: array
                                    items:
                                        type: object
                                        properties:
                                            id:
                                                type: integer
                                            name:
                                                type: string
                    relationships:
                        type: array
                        items:
                            type: object
                            properties:
                                citing_article:
                                    type: object
                                    properties:
                                        id:
                                            type: integer
                                referenced_article:
                                    type: object
                                    properties:
                                        id:
                                            type: integer
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

        # 获取用户的所有标签
        tags = (
            Tag.query.filter_by(user_id=user_id).order_by(Tag.created_at.desc()).all()
        )

        # 构建标签及其文章的数据结构
        tags_data = []
        for tag in tags:
            # 获取该标签下的所有文章
            articles_query = (
                Article.query.join(ArticleTag, Article.id == ArticleTag.article_id)
                .filter(ArticleTag.tag_id == tag.id)
                .order_by(Article.created_at.desc())
            )
            articles = articles_query.all()

            # 构建文章列表
            articles_data = []
            for article in articles:
                articles_data.append({"id": article.id, "name": article.title})

            tags_data.append(
                {"id": tag.id, "name": tag.name, "articles": articles_data}
            )

        # 获取该用户文章之间的引用关系
        user_article_ids = [
            article.id for article in Article.query.filter_by(author_id=user_id).all()
        ]

        relationships_data = []
        if user_article_ids:
            # 查找该用户文章之间的引用关系
            relationships = (
                ArticleRelationship.query.filter(
                    ArticleRelationship.citing_article_id.in_(user_article_ids),
                    ArticleRelationship.referenced_article_id.in_(user_article_ids),
                )
                .order_by(ArticleRelationship.created_at.desc())
                .all()
            )

            # 构建关系数据
            for rel in relationships:
                relationships_data.append(
                    {
                        "citing_article": {"id": rel.citing_article_id},
                        "referenced_article": {"id": rel.referenced_article_id},
                    }
                )

        return {
            "user_id": user.id,
            "username": user.username,
            "avatar_url": user.avatar_url,
            "tags": tags_data,
            "relationships": relationships_data,
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

        # 获取该文章引用的文章和引用该文章的文章的详细概览信息
        recommendations = []

        # 1. 获取该文章引用的文章（被该文章引用的文章）
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
                    "relationship_type": "referenced_by_current",  # 被当前文章引用
                }
            )

        # 2. 获取引用该文章的文章（引用当前文章的文章）
        citations = ArticleRelationship.query.filter_by(
            referenced_article_id=article_id
        ).all()

        for cite in citations:
            cite_article = Article.query.get(cite.citing_article_id)
            if not cite_article:
                continue  # 跳过已删除的文章

            cite_author = User.query.get(cite_article.author_id)
            if not cite_author:
                continue  # 跳过作者不存在的文章

            cite_tags = [{"id": tag.id, "name": tag.name} for tag in cite_article.tags]

            recommendations.append(
                {
                    "id": cite_article.id,
                    "title": cite_article.title,
                    "summary": cite_article.summary,
                    "tags": cite_tags,
                    "author": {
                        "id": cite_author.id,
                        "username": cite_author.username,
                        "avatar_url": cite_author.avatar_url,
                    },
                    "created_at": cite_article.created_at.isoformat(),
                    "relationship_type": "citing_current",  # 引用当前文章
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


@article_bp.route("/articles/reset-demo-data", methods=["POST"])
def reset_demo_data():
    """
    重置用户ID=5的演示数据
    ---
    responses:
        200:
            description: 成功重置演示数据
            schema:
                type: object
                properties:
                    message:
                        type: string
                    reset_stats:
                        type: object
                        properties:
                            deleted_articles:
                                type: integer
                            deleted_tags:
                                type: integer
                            deleted_tasks:
                                type: integer
                            deleted_records:
                                type: integer
                            created_articles:
                                type: integer
                            created_tags:
                                type: integer
                            created_relationships:
                                type: integer
        500:
            description: 服务器内部错误
    """
    target_user_id = 5
    
    try:
        # 开始事务
        current_app.logger.info(f"开始重置用户ID={target_user_id}的演示数据")
        
        # 检查用户是否存在
        user = User.query.get(target_user_id)
        if not user:
            return {"message": f"用户ID={target_user_id}不存在"}, 404
        
        # 统计信息
        reset_stats = {
            "deleted_articles": 0,
            "deleted_tags": 0,
            "deleted_tasks": 0,
            "deleted_records": 0,
            "created_articles": 0,
            "created_tags": 0,
            "created_relationships": 0
        }
        
        # === 第一阶段：删除现有数据（按外键依赖顺序） ===
        
        # 1. 获取用户相关的所有ID
        user_articles = Article.query.filter_by(author_id=target_user_id).all()
        user_article_ids = [a.id for a in user_articles]
        
        user_tags = Tag.query.filter_by(user_id=target_user_id).all()
        user_tag_ids = [t.id for t in user_tags]
        
        user_tasks = GenerationTask.query.filter_by(user_id=target_user_id).all()
        user_task_ids = [t.id for t in user_tasks]
        
        user_records = UserAudioRecord.query.filter_by(user_id=target_user_id).all()
        user_record_ids = [r.id for r in user_records]
        
        current_app.logger.info(f"找到待删除数据: 文章{len(user_article_ids)}篇, 标签{len(user_tag_ids)}个, 任务{len(user_task_ids)}个, 记录{len(user_record_ids)}个")
        
        # 2. 删除文章引用关系
        if user_article_ids:
            citing_count = ArticleRelationship.query.filter(
                ArticleRelationship.citing_article_id.in_(user_article_ids)
            ).delete(synchronize_session=False)
            
            referenced_count = ArticleRelationship.query.filter(
                ArticleRelationship.referenced_article_id.in_(user_article_ids)
            ).delete(synchronize_session=False)
            
            current_app.logger.info(f"删除文章引用关系: 作为引用方{citing_count}个, 作为被引用方{referenced_count}个")
        
        # 3. 删除文章-标签关联
        if user_article_ids:
            ArticleTag.query.filter(
                ArticleTag.article_id.in_(user_article_ids)
            ).delete(synchronize_session=False)
        
        if user_tag_ids:
            ArticleTag.query.filter(
                ArticleTag.tag_id.in_(user_tag_ids)
            ).delete(synchronize_session=False)
        
        # 4. 删除任务-记录映射
        if user_task_ids:
            TaskRecordsMapping.query.filter(
                TaskRecordsMapping.task_id.in_(user_task_ids)
            ).delete(synchronize_session=False)
        
        if user_record_ids:
            TaskRecordsMapping.query.filter(
                TaskRecordsMapping.record_id.in_(user_record_ids)
            ).delete(synchronize_session=False)
        
        # 5. 删除实体数据
        reset_stats["deleted_articles"] = Article.query.filter_by(author_id=target_user_id).delete()
        reset_stats["deleted_tags"] = Tag.query.filter_by(user_id=target_user_id).delete()
        reset_stats["deleted_tasks"] = GenerationTask.query.filter_by(user_id=target_user_id).delete()
        reset_stats["deleted_records"] = UserAudioRecord.query.filter_by(user_id=target_user_id).delete()
        
        current_app.logger.info(f"完成数据清理阶段")
        
        # === 第二阶段：创建预制数据 ===
        
        # 1. 创建预制标签
        demo_tags_data = ["创新", "科技"]
        demo_tags = {}
        
        for tag_name in demo_tags_data:
            tag = Tag(user_id=target_user_id, name=tag_name)
            db.session.add(tag)
            db.session.flush()  # 获取ID
            demo_tags[tag_name] = tag
            reset_stats["created_tags"] += 1
        
        current_app.logger.info(f"创建预制标签: {list(demo_tags.keys())}")
        
        # 2. 创建预制文章
        demo_articles_data = [
            {
                "title": "中国最大的青年黑客马拉松：由学生社区驱动的创新平台",
                "summary": "这是一个专为年轻创作者打造的盛大平台，被誉为中国最大的黑客马拉松。其特色在于完全由学生和社区组织，为参与者提供全方位的支持。",
                "content": "这是一个专为年轻工程师、设计师和创造者打造的盛大平台，被誉为中国最大、也是首个以青年为导向的黑客马拉松。\n\n### 青年驱动的社区文化\n\n该活动最特别之处在于它完全由学生和社区自发组织，展现了青年一代的领导力和创造力。为了让参与者能全身心投入创新，活动提供了周到的后勤保障，包括每日三餐以及无限量的零食、咖啡和饮料，营造了开放协作的社区氛围。\n\n### 2024年活动规模与影响力\n\n以在杭州举办的AdventureX 2024为例，其规模和影响力十分显著：\n- **参与人员**：活动聚集了247名来自世界各地的年轻工程师、设计师和梦想家。整个活动周吸引了超过200名黑客和2000名访客参与。\n- **产出项目**：活动期间共诞生了50多个创新项目。\n- **企业合作**：获得了将近100家公司的赞助支持。\n- **知识分享**：举办了20场不同主题的工作坊，内容涵盖人工智能（AI）、虚拟现实/增强现实（VR/AR）、Web3等前沿技术领域。",
                "tags": ["科技", "创新"],
                "status": "published"
            },
            {
                "title": "AdventureX 2025午餐供应商变更及初步反馈",
                "summary": "由于参与人数增加，AdventureX 2025的午餐供应商发生变更。与2024年相比，新供应商提供的餐食收到了不太理想的初步反馈。",
                "content": "### 2025年午餐安排调整\nAdventureX 2025年的午餐供应方发生了变更。与2024年由湖畔提供的午餐不同，今年的午餐改由一家新的供应商负责。\n\n### 变更原因及反馈\n此次变更的主要原因是活动参与人数大幅增加，超出了湖畔的供应能力。然而，与会者对新供应商的餐食反馈普遍不佳，认为其口味不如往年。",
                "tags": ["科技", "创新"],
                "status": "published"
            }
        ]
        
        demo_articles = {}
        for article_data in demo_articles_data:
            article = Article(
                author_id=target_user_id,
                title=article_data["title"],
                summary=article_data["summary"],
                content=article_data["content"],
                status=article_data["status"],
                finished_at=datetime.now()
            )
            db.session.add(article)
            db.session.flush()  # 获取ID
            
            # 添加标签关联
            for tag_name in article_data["tags"]:
                if tag_name in demo_tags:
                    article_tag = ArticleTag(
                        article_id=article.id,
                        tag_id=demo_tags[tag_name].id
                    )
                    db.session.add(article_tag)
            
            demo_articles[article_data["title"]] = article
            reset_stats["created_articles"] += 1
        
        current_app.logger.info(f"创建预制文章: {len(demo_articles)}篇")
        
        # 3. 创建文章引用关系（当前无引用关系）
        demo_relationships = []
        
        for rel_data in demo_relationships:
            citing_article = demo_articles.get(rel_data["citing"])
            referenced_article = demo_articles.get(rel_data["referenced"])
            
            if citing_article and referenced_article:
                relationship = ArticleRelationship(
                    citing_article_id=citing_article.id,
                    referenced_article_id=referenced_article.id
                )
                db.session.add(relationship)
                reset_stats["created_relationships"] += 1
        
        current_app.logger.info(f"创建文章引用关系: {reset_stats['created_relationships']}个")
        
        # 提交事务
        db.session.commit()
        
        current_app.logger.info(f"用户ID={target_user_id}的演示数据重置完成")
        
        return {
            "message": "演示数据重置成功",
            "reset_stats": reset_stats,
            "demo_data": {
                "user_id": target_user_id,
                "username": user.username,
                "tags_count": len(demo_tags),
                "articles_count": len(demo_articles),
                "relationships_count": reset_stats["created_relationships"]
            }
        }, 200
        
    except Exception as e:
        # 回滚事务
        db.session.rollback()
        current_app.logger.error(f"重置演示数据失败: {str(e)}")
        return {"message": f"重置演示数据失败: {str(e)}"}, 500


@article_bp.route("/articles/reset-data/<int:user_id>", methods=["DELETE"])
def reset_data(user_id:int):
    """
    重置用户ID=5的演示数据
    ---
    responses:
        200:
            description: 成功重置演示数据
            schema:
                type: object
                properties:
                    message:
                        type: string
                    reset_stats:
                        type: object
                        properties:
                            deleted_articles:
                                type: integer
                            deleted_tags:
                                type: integer
                            deleted_tasks:
                                type: integer
                            deleted_records:
                                type: integer
                            created_articles:
                                type: integer
                            created_tags:
                                type: integer
                            created_relationships:
                                type: integer
        500:
            description: 服务器内部错误
    """

    try:
        # 开始事务
        current_app.logger.info(f"开始重置用户ID={user_id}的演示数据")

        # 检查用户是否存在
        user = User.query.get(user_id)
        if not user:
            return {"message": f"用户ID={user_id}不存在"}, 404

        # 统计信息
        reset_stats = {
            "deleted_articles": 0,
            "deleted_tags": 0,
            "deleted_tasks": 0,
            "deleted_records": 0,
            "created_articles": 0,
            "created_tags": 0,
            "created_relationships": 0
        }

        # === 第一阶段：删除现有数据（按外键依赖顺序） ===

        # 1. 获取用户相关的所有ID
        user_articles = Article.query.filter_by(author_id=user_id).all()
        user_article_ids = [a.id for a in user_articles]

        user_tags = Tag.query.filter_by(user_id=user_id).all()
        user_tag_ids = [t.id for t in user_tags]

        user_tasks = GenerationTask.query.filter_by(user_id=user_id).all()
        user_task_ids = [t.id for t in user_tasks]

        user_records = UserAudioRecord.query.filter_by(user_id=user_id).all()
        user_record_ids = [r.id for r in user_records]

        current_app.logger.info(
            f"找到待删除数据: 文章{len(user_article_ids)}篇, 标签{len(user_tag_ids)}个, 任务{len(user_task_ids)}个, 记录{len(user_record_ids)}个")

        # 2. 删除文章引用关系
        if user_article_ids:
            citing_count = ArticleRelationship.query.filter(
                ArticleRelationship.citing_article_id.in_(user_article_ids)
            ).delete(synchronize_session=False)

            referenced_count = ArticleRelationship.query.filter(
                ArticleRelationship.referenced_article_id.in_(user_article_ids)
            ).delete(synchronize_session=False)

            current_app.logger.info(f"删除文章引用关系: 作为引用方{citing_count}个, 作为被引用方{referenced_count}个")

        # 3. 删除文章-标签关联
        if user_article_ids:
            ArticleTag.query.filter(
                ArticleTag.article_id.in_(user_article_ids)
            ).delete(synchronize_session=False)

        if user_tag_ids:
            ArticleTag.query.filter(
                ArticleTag.tag_id.in_(user_tag_ids)
            ).delete(synchronize_session=False)

        # 4. 删除任务-记录映射
        if user_task_ids:
            TaskRecordsMapping.query.filter(
                TaskRecordsMapping.task_id.in_(user_task_ids)
            ).delete(synchronize_session=False)

        if user_record_ids:
            TaskRecordsMapping.query.filter(
                TaskRecordsMapping.record_id.in_(user_record_ids)
            ).delete(synchronize_session=False)

        # 5. 删除实体数据
        reset_stats["deleted_articles"] = Article.query.filter_by(author_id=user_id).delete()
        reset_stats["deleted_tags"] = Tag.query.filter_by(user_id=user_id).delete()
        reset_stats["deleted_tasks"] = GenerationTask.query.filter_by(user_id=user_id).delete()
        reset_stats["deleted_records"] = UserAudioRecord.query.filter_by(user_id=user_id).delete()

        db.session.commit()

        current_app.logger.info(f"完成数据清理阶段")
        return {
            "message": "演示数据重置成功",
            "reset_stats": reset_stats,
            "demo_data": {
                "user_id": user_id,
                "username": user.username,
                "tags_count": reset_stats["deleted_tags"],
                "articles_count": reset_stats["deleted_articles"],
                "relationships_count": reset_stats["created_relationships"]
            }
        }
    except Exception as e:
        # 回滚事务
        db.session.rollback()
        current_app.logger.error(f"重置演示数据失败: {str(e)}")
        return {"message": f"重置演示数据失败: {str(e)}"}, 500