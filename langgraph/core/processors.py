"""
内容处理器

提供文本预处理和后处理功能
"""

import re
import json
from typing import List, Dict, Any, Optional
from ..utils.exceptions import ContentValidationError, ERROR_CODES
from ..utils.validators import ContentValidator


class ContentProcessor:
    """内容处理器"""
    
    def __init__(self):
        """初始化内容处理器"""
        self.validator = ContentValidator()
    
    def preprocess_transcript(self, transcript: str) -> str:
        """
        预处理语音转录文本
        
        Args:
            transcript: 原始转录文本
            
        Returns:
            处理后的文本
        """
        if not transcript:
            return ""
        
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', transcript.strip())
        
        # 移除特殊的转录标记（如果有）
        text = re.sub(r'\[.*?\]', '', text)  # 移除方括号内容
        text = re.sub(r'\(.*?\)', '', text)  # 移除圆括号内容（可能的噪音标记）
        
        # 标准化标点符号
        text = re.sub(r'[，,]\s*', '，', text)  # 统一逗号格式
        text = re.sub(r'[。.]\s*', '。', text)  # 统一句号格式
        text = re.sub(r'[？?]\s*', '？', text)  # 统一问号格式
        text = re.sub(r'[！!]\s*', '！', text)  # 统一感叹号格式
        
        # 再次清理多余空格
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text
    
    def preprocess_article_content(self, content: str) -> str:
        """
        预处理文章内容
        
        Args:
            content: 原始文章内容
            
        Returns:
            处理后的文章内容
        """
        if not content:
            return ""
        
        content = content.strip()
        
        # 标准化换行符
        content = re.sub(r'\r\n', '\n', content)
        content = re.sub(r'\r', '\n', content)
        
        # 移除多余的空行（保留段落结构）
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # 清理每行的首尾空格
        lines = [line.strip() for line in content.split('\n')]
        content = '\n'.join(lines)
        
        return content
    
    def postprocess_gpt_response(self, response: str) -> List[Dict[str, Any]]:
        """
        后处理GPT API响应
        
        Args:
            response: GPT API响应文本
            
        Returns:
            解析并验证后的结果列表
        """
        # 使用验证器解析JSON响应
        parsed_result = self.validator.validate_gpt_response(response)
        
        # 对每个结果项进行后处理
        processed_result = []
        for item in parsed_result:
            processed_item = self._postprocess_result_item(item)
            processed_result.append(processed_item)
        
        return processed_result
    
    def _postprocess_result_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        后处理单个结果项
        
        Args:
            item: 结果项
            
        Returns:
            处理后的结果项
        """
        # 深拷贝避免修改原始数据
        processed_item = item.copy()
        
        # 处理内容
        content = item["content"]
        
        # 标准化内容格式
        content = self.postprocess_article_content(content)
        
        # 验证内容
        content = self.validator.validate_article_content(content)
        
        processed_item["content"] = content
        
        return processed_item
    
    def postprocess_article_content(self, content: str) -> str:
        """
        后处理文章内容（GPT生成的内容）
        
        Args:
            content: GPT生成的文章内容
            
        Returns:
            处理后的文章内容
        """
        if not content:
            return ""
        
        content = content.strip()
        
        # 移除可能的markdown代码块标记
        content = re.sub(r'^```.*?\n', '', content, flags=re.MULTILINE)
        content = re.sub(r'\n```$', '', content, flags=re.MULTILINE)
        
        # 标准化markdown标题格式
        content = re.sub(r'^(#+)\s*(.+)$', r'\1 \2', content, flags=re.MULTILINE)
        
        # 标准化列表格式
        content = re.sub(r'^\s*[-*+]\s+', '- ', content, flags=re.MULTILINE)
        content = re.sub(r'^\s*(\d+)\.\s+', r'\1. ', content, flags=re.MULTILINE)
        
        # 标准化段落间距
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # 移除行首尾多余空格
        lines = [line.rstrip() for line in content.split('\n')]
        content = '\n'.join(lines)
        
        # 确保文章结尾没有多余换行
        content = content.rstrip('\n')
        
        return content
    
    def extract_article_metadata(self, content: str) -> Dict[str, Any]:
        """
        从文章内容中提取元数据
        
        Args:
            content: 文章内容
            
        Returns:
            提取的元数据
        """
        metadata = {
            "title": None,
            "has_headings": False,
            "has_lists": False,
            "paragraph_count": 0,
            "word_count": 0,
            "estimated_reading_time": 0
        }
        
        if not content:
            return metadata
        
        # 提取标题（第一个h1标题）
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        
        # 检查是否包含标题
        metadata["has_headings"] = bool(re.search(r'^#+\s+', content, re.MULTILINE))
        
        # 检查是否包含列表
        metadata["has_lists"] = bool(re.search(r'^\s*[-*+\d.]\s+', content, re.MULTILINE))
        
        # 计算段落数量
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        metadata["paragraph_count"] = len(paragraphs)
        
        # 计算字数（中英文混合）
        words = re.findall(r'\b\w+\b', content)  # 英文单词
        chinese_chars = re.findall(r'[\u4e00-\u9fff]', content)  # 中文字符
        metadata["word_count"] = len(words) + len(chinese_chars)
        
        # 估算阅读时间（分钟）
        # 假设中文200字/分钟，英文250词/分钟
        reading_time = (len(chinese_chars) / 200) + (len(words) / 250)
        metadata["estimated_reading_time"] = max(1, round(reading_time))
        
        return metadata
    
    def merge_article_contents(self, original_content: str, new_content: str) -> str:
        """
        合并文章内容（智能合并，避免重复）
        
        Args:
            original_content: 原始文章内容
            new_content: 新增内容
            
        Returns:
            合并后的内容
        """
        if not original_content:
            return new_content
        
        if not new_content:
            return original_content
        
        # 简单的重复检测和合并
        # 这里使用基本的字符串匹配，实际可以实现更复杂的语义匹配
        
        # 按段落分割
        original_paragraphs = [p.strip() for p in original_content.split('\n\n') if p.strip()]
        new_paragraphs = [p.strip() for p in new_content.split('\n\n') if p.strip()]
        
        # 检查重复段落
        unique_new_paragraphs = []
        for new_para in new_paragraphs:
            # 计算与原始段落的相似度
            is_duplicate = False
            for original_para in original_paragraphs:
                similarity = self._calculate_text_similarity(new_para, original_para)
                if similarity > 0.8:  # 80%相似度阈值
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                unique_new_paragraphs.append(new_para)
        
        # 合并内容
        all_paragraphs = original_paragraphs + unique_new_paragraphs
        merged_content = '\n\n'.join(all_paragraphs)
        
        return merged_content
    
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        计算两个文本的相似度（简单实现）
        
        Args:
            text1: 文本1
            text2: 文本2
            
        Returns:
            相似度分数（0-1）
        """
        if not text1 or not text2:
            return 0.0
        
        # 简单的字符匹配相似度
        text1 = text1.lower().strip()
        text2 = text2.lower().strip()
        
        if text1 == text2:
            return 1.0
        
        # 计算最长公共子序列长度
        def lcs_length(s1, s2):
            m, n = len(s1), len(s2)
            dp = [[0] * (n + 1) for _ in range(m + 1)]
            
            for i in range(1, m + 1):
                for j in range(1, n + 1):
                    if s1[i-1] == s2[j-1]:
                        dp[i][j] = dp[i-1][j-1] + 1
                    else:
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
            
            return dp[m][n]
        
        lcs_len = lcs_length(text1, text2)
        max_len = max(len(text1), len(text2))
        
        return lcs_len / max_len if max_len > 0 else 0.0