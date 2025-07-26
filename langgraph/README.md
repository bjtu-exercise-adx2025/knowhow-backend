# LangGraph 模块使用指南

LangGraph 是一个基于 GPT 模型的智能文章内容分析和处理模块，用于分析语音转录文本与现有文章的关系，并自动决定是否创建新文章或更新现有文章。

## 核心功能

- 🎯 **智能内容分析**: 使用GPT模型分析语音转录文本与现有文章的关系
- 📝 **自动更新决策**: 智能判断是更新现有文章还是创建新文章
- 🔄 **批量处理**: 支持批量处理多个转录文本与文章的组合
- 🗄️ **数据库集成**: 与项目现有SQLAlchemy模型无缝集成
- ⚙️ **灵活配置**: 支持多种GPT模型和参数配置
- 🔍 **Debug支持**: 完整的调试日志和配置管理
- 🚨 **错误处理**: 详细的错误码分类和异常处理机制

## 在后端接口中的集成使用

### 1. 导入模块

```python
from langgraph import ArticleProcessorService
```

### 2. 在 Flask 路由中使用

#### 基本集成示例（推荐在 app/api/v1/article.py 中添加）

```python
from langgraph import ArticleProcessorService
from flask import request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

@article_bp.route('/intelligent-processing', methods=['POST'])
@jwt_required()
def intelligent_article_processing():
    """智能文章处理接口"""
    try:
        data = request.get_json()
        
        # 获取参数
        transcript_id = data.get('transcript_id')
        article_ids = data.get('article_ids', [])
        user_id = get_jwt_identity()  # 从JWT获取当前用户ID
        
        # 创建LangGraph服务实例
        service = ArticleProcessorService()
        
        # 处理内容
        result = service.process_transcript_with_articles(
            transcript_id=transcript_id,
            article_ids=article_ids,
            user_id=user_id
        )
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": "文章智能处理完成",
                "data": result['data']
            }), 200
        else:
            return jsonify({
                "success": False,
                "message": result['error_message'],
                "error_code": result['error_code']
            }), 400
            
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"智能处理失败: {str(e)}"
        }), 500
```

#### 批量处理接口示例

```python
@article_bp.route('/batch-intelligent-processing', methods=['POST'])
@jwt_required()
def batch_intelligent_processing():
    """批量智能文章处理接口"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # 获取批量处理数据
        # 格式: [{"transcript_id": 1, "article_ids": [1, 2]}, ...]
        transcript_article_pairs = data.get('pairs', [])
        
        # 创建LangGraph服务
        service = ArticleProcessorService()
        
        # 批量处理
        result = service.batch_process_transcripts(
            transcript_article_pairs=transcript_article_pairs,
            user_id=user_id
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"批量处理失败: {str(e)}"
        }), 500
```

### 3. 服务状态检查接口

```python
@article_bp.route('/langgraph-status', methods=['GET'])
@jwt_required()
def langgraph_service_status():
    """检查LangGraph服务状态"""
    try:
        service = ArticleProcessorService()
        status = service.get_service_status()
        
        return jsonify({
            "success": True,
            "data": status
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"状态检查失败: {str(e)}"
        }), 500
```

### 4. 集成到现有的文字记录处理流程

可以在现有的 `POST /api/v1/articles/text-record` 接口中集成 LangGraph：

```python
@article_bp.route('/text-record', methods=['POST'])
@jwt_required()
def create_text_record():
    """创建文字记录（集成LangGraph智能处理）"""
    try:
        data = request.get_json()
        user_id = get_jwt_identity()
        
        # 原有的文字记录创建逻辑...
        
        # 如果需要智能处理
        if data.get('enable_intelligent_processing', False):
            transcript_id = data.get('transcript_id')
            related_article_ids = data.get('related_articles', [])
            
            if transcript_id:
                # 使用LangGraph进行智能处理
                service = ArticleProcessorService()
                langgraph_result = service.process_transcript_with_articles(
                    transcript_id=transcript_id,
                    article_ids=related_article_ids,
                    user_id=user_id
                )
                
                # 在响应中包含LangGraph处理结果
                response_data = {
                    # ... 原有响应数据
                    "intelligent_processing": langgraph_result
                }
                
                return jsonify(response_data), 200
        
        # 原有的返回逻辑...
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
```

## API 请求和响应格式

### 1. 单个转录文本处理

**请求格式**：
```json
POST /api/v1/articles/intelligent-processing
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "transcript_id": 15,
  "article_ids": [1, 44, 67]
}
```

**成功响应**：
```json
{
  "success": true,
  "message": "文章智能处理完成",
  "data": {
    "created_count": 1,
    "updated_count": 2,
    "total_processed": 3,
    "created_articles": [
      {
        "new_id": 123,
        "content_length": 1500
      }
    ],
    "updated_articles": [
      {
        "id": 44,
        "content_length": 2000
      },
      {
        "id": 67,
        "content_length": 1800
      }
    ],
    "analysis_items_count": 3
  }
}
```

**错误响应**：
```json
{
  "success": false,
  "message": "Transcript with ID 15 not found",
  "error_code": "DB_TRANSCRIPT_NOT_FOUND"
}
```

### 2. 批量处理

**请求格式**：
```json
POST /api/v1/articles/batch-intelligent-processing
Content-Type: application/json
Authorization: Bearer <jwt_token>

{
  "pairs": [
    {"transcript_id": 15, "article_ids": [1, 44]},
    {"transcript_id": 16, "article_ids": [67, 89, 123]},
    {"transcript_id": 17, "article_ids": []}
  ]
}
```

**响应格式**：
```json
{
  "success": true,
  "message": "Batch processing completed",
  "overall_stats": {
    "total_pairs": 3,
    "successful_pairs": 2,
    "failed_pairs": 1,
    "total_created": 2,
    "total_updated": 4
  },
  "individual_results": [
    {
      "index": 0,
      "transcript_id": 15,
      "article_ids": [1, 44],
      "result": {
        "success": true,
        "data": {...}
      }
    }
  ]
}
```

## 配置管理

### 1. 默认配置文件 (`langgraph/config.json`)

```json
{
  "models": {
    "default": {
      "url": "https://ai-proxy.chatwise.app/openrouter/api/v1",
      "api_key": "***REMOVED_API_KEY***",
      "model_name": "google/gemini-2.5-pro"
    }
  },
  "settings": {
    "timeout": 30,
    "max_retries": 3,
    "temperature": 0.1,
    "max_tokens": 4000
  },
  "debug": {
    "enabled": true,
    "log_level": "DEBUG",
    "log_to_file": true,
    "log_file": "langgraph_debug.log",
    "log_to_console": true,
    "log_requests": true,
    "log_responses": true,
    "log_database_queries": true,
    "log_processing_steps": true
  }
}
```

### 2. 在接口中使用自定义配置

```python
# 使用环境变量配置（推荐用于生产环境）
import os

@article_bp.route('/custom-processing', methods=['POST'])
def custom_processing():
    # 创建临时配置
    custom_config = {
        "models": {
            "production": {
                "url": os.getenv('GPT_API_URL'),
                "api_key": os.getenv('GPT_API_KEY'),
                "model_name": os.getenv('GPT_MODEL_NAME', 'gpt-4')
            }
        },
        "settings": {
            "timeout": int(os.getenv('GPT_TIMEOUT', 60)),
            "max_retries": int(os.getenv('GPT_MAX_RETRIES', 3))
        },
        "debug": {
            "enabled": os.getenv('DEBUG', 'false').lower() == 'true'
        }
    }
    
    # 写入临时配置文件
    import json
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(custom_config, f)
        temp_config_path = f.name
    
    try:
        # 使用自定义配置创建服务
        service = ArticleProcessorService(
            config_path=temp_config_path,
            model_name="production"
        )
        
        # 处理逻辑...
        
    finally:
        # 清理临时文件
        os.unlink(temp_config_path)
```

### 3. 动态更新模型配置

```python
@article_bp.route('/update-model-config', methods=['POST'])
@jwt_required() 
def update_model_configuration():
    """动态更新GPT模型配置"""
    try:
        data = request.get_json()
        
        service = ArticleProcessorService()
        
        result = service.update_model_config(
            model_name=data.get('model_name'),
            url=data.get('url'),
            api_key=data.get('api_key'),
            model_api_name=data.get('model_api_name')
        )
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": str(e)
        }), 500
```

## 在接口中的错误处理

### 1. 常见错误码处理

```python
@article_bp.route('/robust-processing', methods=['POST'])
@jwt_required()
def robust_processing():
    """带完整错误处理的处理接口"""
    try:
        data = request.get_json()
        transcript_id = data.get('transcript_id')
        article_ids = data.get('article_ids', [])
        user_id = get_jwt_identity()
        
        service = ArticleProcessorService()
        result = service.process_transcript_with_articles(
            transcript_id=transcript_id,
            article_ids=article_ids,
            user_id=user_id
        )
        
        if result['success']:
            return jsonify({
                "success": True,
                "message": "处理成功",
                "data": result['data']
            }), 200
        else:
            # 根据错误码返回不同的HTTP状态码
            error_code = result.get('error_code')
            
            if error_code == 'DB_TRANSCRIPT_NOT_FOUND':
                return jsonify({
                    "success": False,
                    "message": "转录记录不存在",
                    "error_code": error_code
                }), 404
            elif error_code == 'DB_ARTICLE_NOT_FOUND':
                return jsonify({
                    "success": False,
                    "message": "指定的文章不存在",
                    "error_code": error_code
                }), 404
            elif error_code == 'GPT_API_UNAUTHORIZED':
                return jsonify({
                    "success": False,
                    "message": "GPT服务配置错误",
                    "error_code": error_code
                }), 500
            elif error_code == 'GPT_API_TIMEOUT':
                return jsonify({
                    "success": False,
                    "message": "GPT服务超时，请稍后重试",
                    "error_code": error_code
                }), 503
            else:
                return jsonify({
                    "success": False,
                    "message": result['error_message'],
                    "error_code": error_code
                }), 400
                
    except Exception as e:
        # 记录未预期的错误
        import traceback
        traceback.print_exc()
        
        return jsonify({
            "success": False,
            "message": "服务暂时不可用",
            "error_code": "INTERNAL_SERVER_ERROR"
        }), 500
```

### 2. 错误码对照表

| 错误码 | 描述 | HTTP状态码 | 处理建议 |
|--------|------|------------|----------|
| `DB_CONNECTION_FAILED` | 数据库连接失败 | 500 | 检查数据库服务状态 |
| `DB_TRANSCRIPT_NOT_FOUND` | 转录记录不存在 | 404 | 验证转录ID有效性 |
| `DB_ARTICLE_NOT_FOUND` | 文章不存在 | 404 | 验证文章ID列表 |
| `GPT_API_UNAUTHORIZED` | GPT API认证失败 | 500 | 检查API密钥配置 |
| `GPT_API_TIMEOUT` | GPT API超时 | 503 | 增加超时时间或重试 |
| `GPT_API_QUOTA_EXCEEDED` | API配额超限 | 429 | 等待配额重置或升级 |
| `INVALID_JSON_RESPONSE` | GPT返回格式无效 | 500 | 检查模型和提示词配置 |
| `PROCESSING_FAILED` | 处理失败 | 400 | 检查输入参数 |

## Flask 应用上下文管理

### 1. 确保在应用上下文中使用

```python
from app import create_app
from flask import has_app_context

@article_bp.route('/context-aware-processing', methods=['POST'])
def context_aware_processing():
    """确保在正确的应用上下文中使用LangGraph"""
    
    # LangGraph会自动处理应用上下文，但也可以手动确保
    if not has_app_context():
        app = create_app()
        with app.app_context():
            service = ArticleProcessorService()
            # 处理逻辑...
    else:
        service = ArticleProcessorService()
        # 处理逻辑...
```

### 2. 异步处理（推荐用于大量数据）

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from app import create_app

def process_in_context(transcript_id, article_ids, user_id):
    """在Flask应用上下文中处理"""
    app = create_app()
    with app.app_context():
        service = ArticleProcessorService()
        return service.process_transcript_with_articles(
            transcript_id, article_ids, user_id
        )

@article_bp.route('/async-processing', methods=['POST'])
@jwt_required()
def async_processing():
    """异步处理接口"""
    try:
        data = request.get_json()
        transcript_id = data.get('transcript_id')
        article_ids = data.get('article_ids', [])
        user_id = get_jwt_identity()
        
        # 提交到线程池异步处理
        executor = ThreadPoolExecutor(max_workers=1)
        future = executor.submit(
            process_in_context, 
            transcript_id, article_ids, user_id
        )
        
        # 可以选择等待结果或返回任务ID
        # 这里演示直接等待结果
        result = future.result(timeout=120)  # 2分钟超时
        
        return jsonify(result), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"异步处理失败: {str(e)}"
        }), 500
```

## 性能优化和监控

### 1. 缓存优化

```python
from functools import lru_cache
from flask_caching import Cache

# 假设已配置Flask-Caching
cache = Cache()

class CachedArticleProcessor:
    def __init__(self):
        self.service = ArticleProcessorService()
    
    @cache.memoize(timeout=300)  # 缓存5分钟
    def get_articles_cached(self, article_ids_tuple):
        """缓存文章内容"""
        return self.service.db_ops.get_articles_by_ids(list(article_ids_tuple))
    
    def process_with_cache(self, transcript_id, article_ids, user_id):
        # 使用缓存获取文章，减少数据库查询
        articles = self.get_articles_cached(tuple(sorted(article_ids)))
        # 继续处理...

@article_bp.route('/cached-processing', methods=['POST'])
@jwt_required()
def cached_processing():
    """使用缓存优化的处理接口"""
    processor = CachedArticleProcessor()
    # 使用优化后的处理器...
```

### 2. 请求监控和日志

```python
import time
from app.utils.log_utils import get_logger

logger = get_logger(__name__)

@article_bp.route('/monitored-processing', methods=['POST'])
@jwt_required()
def monitored_processing():
    """带监控的处理接口"""
    start_time = time.time()
    user_id = get_jwt_identity()
    
    try:
        data = request.get_json()
        transcript_id = data.get('transcript_id')
        article_ids = data.get('article_ids', [])
        
        # 记录请求开始
        logger.info(f"LangGraph处理开始 - 用户: {user_id}, 转录: {transcript_id}, 文章数: {len(article_ids)}")
        
        service = ArticleProcessorService()
        result = service.process_transcript_with_articles(
            transcript_id=transcript_id,
            article_ids=article_ids,
            user_id=user_id
        )
        
        # 记录处理结果和耗时
        process_time = time.time() - start_time
        
        if result['success']:
            data_info = result['data']
            logger.info(
                f"LangGraph处理成功 - 耗时: {process_time:.2f}s, "
                f"新建: {data_info['created_count']}, 更新: {data_info['updated_count']}"
            )
        else:
            logger.error(
                f"LangGraph处理失败 - 耗时: {process_time:.2f}s, "
                f"错误: {result['error_message']}"
            )
        
        return jsonify(result), 200 if result['success'] else 400
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"LangGraph处理异常 - 耗时: {process_time:.2f}s, 异常: {str(e)}")
        
        return jsonify({
            "success": False,
            "message": "处理过程中发生异常"
        }), 500
```

## 测试和调试

### 1. 基本功能测试

```python
# 创建测试接口用于验证功能
@article_bp.route('/test-langgraph', methods=['POST'])
@jwt_required()
def test_langgraph():
    """LangGraph功能测试接口"""
    try:
        # 检查服务状态
        service = ArticleProcessorService()
        status = service.get_service_status()
        
        if status['database']['status'] != 'connected':
            return jsonify({
                "success": False,
                "message": "数据库连接失败",
                "status": status
            }), 500
        
        if status['gpt_model']['status'] != 'configured':
            return jsonify({
                "success": False,
                "message": "GPT模型配置错误",
                "status": status
            }), 500
        
        # 使用测试数据
        test_result = service.process_transcript_with_articles(
            transcript_id=15,  # 确保这个ID在测试数据库中存在
            article_ids=[1, 44],  # 确保这些ID在测试数据库中存在
            user_id=2
        )
        
        return jsonify({
            "success": True,
            "message": "LangGraph功能测试完成",
            "service_status": status,
            "test_result": test_result
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"测试失败: {str(e)}"
        }), 500
```

### 2. Debug模式启用

```python
@article_bp.route('/enable-debug', methods=['POST'])
@jwt_required()
def enable_debug_mode():
    """启用LangGraph调试模式"""
    try:
        service = ArticleProcessorService()
        
        # 启用详细调试
        service.gpt_config.update_debug_config({
            "enabled": True,
            "log_level": "DEBUG",
            "log_to_console": True,
            "log_requests": True,
            "log_responses": True,
            "log_database_queries": True,
            "log_processing_steps": True
        })
        
        # 获取当前debug配置
        debug_config = service.gpt_config.get_debug_config()
        
        return jsonify({
            "success": True,
            "message": "调试模式已启用",
            "debug_config": debug_config
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "message": f"启用调试模式失败: {str(e)}"
        }), 500
```

## 部署和生产环境注意事项

### 1. 环境变量配置（推荐）

```bash
# 在生产环境中设置环境变量
export LANGGRAPH_GPT_API_URL="https://api.openai.com/v1"
export LANGGRAPH_GPT_API_KEY="sk-your-production-key"
export LANGGRAPH_GPT_MODEL="gpt-4"
export LANGGRAPH_DEBUG_ENABLED="false"
export LANGGRAPH_LOG_LEVEL="INFO"
```

在接口中使用环境变量：

```python
import os

def create_production_service():
    """创建生产环境的LangGraph服务"""
    config = {
        "models": {
            "production": {
                "url": os.getenv('LANGGRAPH_GPT_API_URL'),
                "api_key": os.getenv('LANGGRAPH_GPT_API_KEY'),
                "model_name": os.getenv('LANGGRAPH_GPT_MODEL', 'gpt-4')
            }
        },
        "settings": {
            "timeout": int(os.getenv('LANGGRAPH_TIMEOUT', '60')),
            "max_retries": int(os.getenv('LANGGRAPH_MAX_RETRIES', '3')),
            "temperature": float(os.getenv('LANGGRAPH_TEMPERATURE', '0.1'))
        },
        "debug": {
            "enabled": os.getenv('LANGGRAPH_DEBUG_ENABLED', 'false').lower() == 'true',
            "log_level": os.getenv('LANGGRAPH_LOG_LEVEL', 'INFO')
        }
    }
    
    # 创建临时配置文件
    import tempfile
    import json
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        json.dump(config, f)
        return ArticleProcessorService(config_path=f.name, model_name="production")
```

### 2. 错误监控和告警

```python
# 集成到现有的错误监控系统
import logging
from app.utils.monitoring import send_alert  # 假设有监控系统

@article_bp.route('/production-processing', methods=['POST'])
@jwt_required()
def production_processing():
    """生产环境处理接口"""
    try:
        # 处理逻辑...
        service = create_production_service()
        result = service.process_transcript_with_articles(...)
        
        # 监控失败率
        if not result['success']:
            error_code = result.get('error_code')
            
            # 对关键错误发送告警
            if error_code in ['GPT_API_UNAUTHORIZED', 'DB_CONNECTION_FAILED']:
                send_alert(
                    title="LangGraph关键错误",
                    message=f"错误码: {error_code}, 消息: {result['error_message']}",
                    level="critical"
                )
        
        return jsonify(result)
        
    except Exception as e:
        # 记录到错误日志
        logging.error(f"LangGraph处理异常: {str(e)}", exc_info=True)
        
        # 发送告警
        send_alert(
            title="LangGraph未处理异常",
            message=str(e),
            level="error"
        )
        
        return jsonify({"success": False, "message": "服务异常"}), 500
```

### 3. 并发和资源限制

```python
from threading import Semaphore
from functools import wraps

# 限制并发GPT API调用
langgraph_semaphore = Semaphore(3)  # 最多3个并发调用

def limit_langgraph_concurrency(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        langgraph_semaphore.acquire()
        try:
            return f(*args, **kwargs)
        finally:
            langgraph_semaphore.release()
    return decorated_function

@article_bp.route('/rate-limited-processing', methods=['POST'])
@jwt_required()
@limit_langgraph_concurrency
def rate_limited_processing():
    """限制并发的处理接口"""
    # 处理逻辑...
```

## 最佳实践总结

### 1. 安全性
- 🔐 **API密钥管理**: 使用环境变量存储敏感信息，避免硬编码
- 🛡️ **权限验证**: 所有LangGraph接口都应使用JWT认证
- 📝 **输入验证**: 验证所有用户输入，防止注入攻击

### 2. 性能优化
- ⚡ **并发控制**: 限制同时进行的GPT API调用数量
- 💾 **缓存策略**: 对频繁访问的文章内容使用缓存
- 🔄 **异步处理**: 对于耗时操作使用异步处理

### 3. 监控和日志
- 📊 **性能监控**: 记录处理时间和成功率
- 🐛 **错误追踪**: 详细记录错误信息和堆栈跟踪
- 📈 **业务指标**: 跟踪文章创建/更新数量等业务指标

### 4. 容错性
- 🔁 **重试机制**: 对临时失败进行自动重试
- 🚨 **降级策略**: 在服务不可用时提供备选方案
- ⚠️ **告警机制**: 对关键错误及时发送告警

## 故障排除

### 常见问题

1. **"模块导入失败"**
   ```bash
   # 确保项目根目录在Python路径中
   export PYTHONPATH="${PYTHONPATH}:/path/to/project2025-backend"
   ```

2. **"数据库连接失败"**
   ```python
   # 测试数据库连接
   service = ArticleProcessorService()
   status = service.get_service_status()
   print(status['database']['status'])
   ```

3. **"GPT API调用失败"**
   ```python
   # 验证API配置
   service.gpt_config.validate_model_config("default")
   ```

4. **"Flask应用上下文错误"**
   ```python
   # 确保在应用上下文中调用
   from flask import has_app_context
   if not has_app_context():
       with app.app_context():
           # 使用LangGraph
   ```

### 调试步骤

1. **启用Debug模式**: 在配置中设置 `"debug": {"enabled": true}`
2. **检查日志文件**: 查看 `langgraph_debug.log` 文件
3. **验证服务状态**: 调用 `get_service_status()` 方法
4. **测试单个组件**: 分别测试数据库连接和GPT API调用

---

**技术支持**: 如有问题请联系开发团队或查看项目文档  
**版本**: LangGraph v1.0.0  
**更新日期**: 2024年