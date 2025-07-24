# 导入所有模型类
from .admin_user import AdminUser
from .article import Article, ArticleTag
from .generation_task import GenerationTask, TaskRecordsMapping
from .tag import Tag
from .user import User
from .user_audio_record import UserAudioRecord

# 导出所有模型
__all__ = [
    "User",
    "AdminUser",
    "UserAudioRecord",
    "GenerationTask",
    "TaskRecordsMapping",
    "Article",
    "ArticleTag",
    "Tag",
]
