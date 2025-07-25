"""
Prompt模板管理

提供用于文章内容分析的prompt模板和格式化功能
"""

from typing import List, Dict, Any


class PromptManager:
    """Prompt模板管理器"""
    
    # 主要的分析prompt模板
    ANALYSIS_PROMPT_TEMPLATE = """📋 分析任务：
新内容：{new_text}

现有文章：
{formatted_articles}

请分析新内容与现有文章的关系：
1. 如果新内容可以补充或修改现有文章，请更新相应文章的内容
2. 如果新内容是全新主题，或现有文章中没有任何相关内容，请创建ID为"new"的新文章
3. 如果现有文章和原来的内容完全重合，或有含义一样的内容，则返回空数组[]
4. 重要：只返回确实需要修改或创建的文章，不要返回未修改的原文章

**引用标记规则：**
- 当新内容引用、补充或与现有文章相关时，在相关语段、概念、数据后添加引用标记
- 引用格式：`[[cite:{{article_id}}]]`，其中article_id是被引用文章的ID
- 引用示例：
  - "根据之前的研究[[cite:5]]，我们发现..."
  - "这与机器学习的基本原理[[cite:12]]一致"
  - "如前所述[[cite:8]]，深度学习模型需要大量数据"
- 引用应该自然地融入文本，不影响阅读体验
- 只有在内容确实相关或引用时才添加引用标记
- **重要：文章不能引用自己，如果是更新现有文章，不要添加对该文章本身ID的引用**

Return 必须是有效的JSON数组，每个元素包含id、title、summary、content字段：
- 修改的文章：[{{"id": "1", "title": "文章标题", "summary": "文章摘要", "content": "updated content with [[cite:5]] references"}}]
- 新文章：[{{"id": "new", "title": "新文章标题", "summary": "新文章摘要", "content": "new content with [[cite:3]] references"}}] 
- 无需修改：[]

注意：
- title: 简洁明确的文章标题（10-30字）
- summary: 文章核心内容摘要（50-150字）
- content: 完整的文章内容（Markdown格式），包含适当的引用标记"""

    # 文章格式化模板
    ARTICLE_FORMAT_TEMPLATE = """```
ID: {id}
Content: {content}
```"""
    
    # 系统消息模板
    SYSTEM_MESSAGE_TEMPLATE = """你是一个专业的内容分析助手。你的任务是分析新的文本内容与现有文章的关系，并决定是否需要更新现有文章或创建新文章。

重要原则：
1. 仔细比较新内容与现有文章的相关性和重复性
2. 只有在新内容能够补充、改进或修正现有文章时才进行更新
3. 只有在新内容是全新主题且与现有文章无关时才创建新文章
4. 如果新内容与现有文章完全重复或无实质性补充，返回空数组
5. 返回的JSON格式必须严格正确，不包含任何额外的文本说明

引用标记使用规范：
1. 当内容与现有文章相关时，必须在相关部分添加引用标记 [[cite:id]]
2. 引用标记应该放在相关语句、概念或数据之后
3. 引用要自然融入文本，保持良好的阅读体验
4. 不要过度引用，只在确实相关时使用
5. 引用格式严格按照 [[cite:数字ID]] 的格式
6. **严禁自引用：文章不能引用自己的ID，更新现有文章时不要引用该文章本身**

返回格式要求：
- 每个元素必须包含：id、title、summary、content 四个字段
- title: 简洁明确的文章标题（10-30字）
- summary: 文章核心内容摘要（50-150字）
- content: 完整的文章内容（Markdown格式），包含适当的引用标记

请始终返回有效的JSON数组格式。"""
    
    def __init__(self):
        """初始化Prompt管理器"""
        pass
    
    def format_analysis_prompt(self, new_text: str, existing_articles: List[Dict[str, Any]]) -> str:
        """
        格式化分析prompt
        
        Args:
            new_text: 新的文本内容
            existing_articles: 现有文章列表，每个元素包含id和content字段
            
        Returns:
            格式化后的prompt字符串
        """
        # 格式化现有文章
        formatted_articles = self._format_articles(existing_articles)
        
        # 填充模板
        return self.ANALYSIS_PROMPT_TEMPLATE.format(
            new_text=new_text.strip(),
            formatted_articles=formatted_articles
        )
    
    def _format_articles(self, articles: List[Dict[str, Any]]) -> str:
        """
        格式化文章列表为文本形式
        
        Args:
            articles: 文章列表
            
        Returns:
            格式化后的文章文本
        """
        if not articles:
            return "（无现有文章）"
        
        formatted_articles = []
        for article in articles:
            article_text = self.ARTICLE_FORMAT_TEMPLATE.format(
                id=article["id"],
                content=article["content"][:1000] + "..." if len(article["content"]) > 1000 else article["content"]  # 限制长度
            )
            formatted_articles.append(article_text)
        
        return "\n\n".join(formatted_articles)
    
    def get_system_message(self) -> str:
        """
        获取系统消息
        
        Returns:
            系统消息字符串
        """
        return self.SYSTEM_MESSAGE_TEMPLATE
    
    def create_chat_messages(self, new_text: str, existing_articles: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """
        创建用于GPT API的消息格式
        
        Args:
            new_text: 新的文本内容
            existing_articles: 现有文章列表
            
        Returns:
            OpenAI Chat API格式的消息列表
        """
        return [
            {
                "role": "system",
                "content": self.get_system_message()
            },
            {
                "role": "user", 
                "content": self.format_analysis_prompt(new_text, existing_articles)
            }
        ]
    
    def create_simple_prompt(self, new_text: str, existing_articles: List[Dict[str, Any]]) -> str:
        """
        创建简单的单一prompt（适用于不支持多轮对话的API）
        
        Args:
            new_text: 新的文本内容
            existing_articles: 现有文章列表
            
        Returns:
            完整的prompt字符串
        """
        system_msg = self.get_system_message()
        user_msg = self.format_analysis_prompt(new_text, existing_articles)
        
        return f"{system_msg}\n\n{user_msg}"
    
    def validate_prompt_inputs(self, new_text: str, existing_articles: List[Dict[str, Any]]) -> bool:
        """
        验证prompt输入的有效性
        
        Args:
            new_text: 新的文本内容
            existing_articles: 现有文章列表
            
        Returns:
            输入是否有效
        """
        # 检查新文本
        if not isinstance(new_text, str) or not new_text.strip():
            return False
        
        # 检查文章列表格式
        if not isinstance(existing_articles, list):
            return False
        
        for article in existing_articles:
            if not isinstance(article, dict):
                return False
            if "id" not in article or "content" not in article:
                return False
            if not isinstance(article["content"], str):
                return False
        
        return True
    
    def get_prompt_token_estimate(self, new_text: str, existing_articles: List[Dict[str, Any]]) -> int:
        """
        估算prompt的token数量（粗略估计）
        
        Args:
            new_text: 新的文本内容
            existing_articles: 现有文章列表
            
        Returns:
            估算的token数量
        """
        full_prompt = self.create_simple_prompt(new_text, existing_articles)
        
        # 粗略估计：英文单词约为1个token，中文字符约为1-2个token
        # 这里使用简单的字符数除以2作为估计
        return len(full_prompt) // 2