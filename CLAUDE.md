# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Environment Setup
- **Setup environment**: `./setup_environment.sh` - Creates venv, installs dependencies
- **Start development**: `./start_development.sh` - Runs Flask dev server on https://127.0.0.1:8888
- **Start production**: `./start_production.sh` - Builds frontend and runs Gunicorn server

### Manual Commands  
- **Run development server**: `python run.py` (requires venv activation)
- **Build frontend**: `./build_admin.sh`
- **Install backend deps**: `pip install -r requirements.txt`
- **Install frontend deps**: `cd admin && pnpm install`

### Testing
- **Run tests**: `python tests/test.py`

### Process Management
- **Stop development**: `pkill -f "python run.py"`
- **Stop production**: `pkill -f gunicorn`

## Architecture Overview

This is a Flask-based backend API with a React frontend admin interface. The application uses a modular structure with clear separation between API endpoints, models, and utilities.

### Key Components

**Flask Application Factory Pattern**
- Main app creation in `app/__init__.py` using `create_app()`
- Configuration in `app/config.py` with separate dev/production configs
- Extensions initialized in `app/extensions.py` (SQLAlchemy, JWT, LoginManager)

**API Structure**
- RESTful API with Flask-RESTX for documentation at `/api/docs`
- Versioned API endpoints under `/api/v1/`
- Main API blueprint in `app/api/__init__.py` with sub-blueprints for v1

**Database Models**
- SQLAlchemy ORM models in `app/models/`
- Key models: User, Article, Tag, AdminUser, GenerationTask, UserAudioRecord
- MySQL database with connection pooling configured

**Authentication**
- JWT-based authentication via Flask-JWT-Extended
- Admin authentication separate from user authentication
- Login session management with Flask-Login

**Frontend Integration**
- React admin interface in `/admin` directory
- Production: Serves built static files from `admin/dist/`
- Development: Redirects `/admin` routes to React dev server on localhost:5173
- Asset routing handles `/assets/`, `/vite.svg`, etc.

**Utilities**
- LLM integration via `app/utils/llm_service.py` using OpenAI-compatible API (Qwen model)
- OSS (Object Storage Service) integration for file uploads
- Logging configuration in `app/utils/log_utils.py`
- Security utilities in `app/utils/security.py`

### Database Configuration
- Uses MySQL with PyMySQL driver
- Connection string configured in `app/config.py`
- Database reset function in `run.py` creates default admin user (username: admin, password: admin)

### Deployment
- Development: Single-threaded Flask dev server with SSL
- Production: Gunicorn WSGI server with configurable workers
- Frontend build process generates static files served by Flask
- Environment variables and secrets stored in configuration files

### Important Notes
- The application runs on port 8888 by default
- SSL is enabled in development mode using adhoc certificates
- Database credentials and API keys are hardcoded in config.py (consider using environment variables)
- Frontend assets are served directly by Flask in production mode

## API v1 接口文档

### 接口结构
API v1 位于 `app/api/v1/` 目录下，包含以下主要模块：

**Blueprint 注册**
- 主蓝图：`v1_bp` (url_prefix='/v1')
- 子蓝图：user, admin_auth, article
- 每个子蓝图独立管理其路由和数据库操作

### 用户管理接口 (user.py)

**基础 CRUD 操作**
```python
# 获取用户列表
GET /api/v1/users
# 查询：User.query.all()
# 返回：[user.to_dict() for user in users]

# 创建用户
POST /api/v1/users
# 操作：User() -> db.session.add() -> db.session.commit()
# 密码加密：user.set_hashed_password(password)

# 获取单个用户
GET /api/v1/users/<int:user_id>
# 查询：User.query.get(user_id)
# 返回：user.to_dict()

# 更新用户信息
PUT /api/v1/users/<int:user_id>
# 查询：User.query.get(user_id)
# 操作：修改属性 -> db.session.commit()

# 删除用户
DELETE /api/v1/users/<int:user_id>
# 查询：User.query.get(user_id)
# 操作：db.session.delete(user) -> db.session.commit()
```

**头像管理**
```python
# 上传头像
POST /api/v1/users/<int:user_id>/avatar
# 查询：User.query.get(user_id)
# 操作：OSS文件上传 -> 更新user.avatar_url -> db.session.commit()

# 删除头像
DELETE /api/v1/users/<int:user_id>/avatar
# 查询：User.query.get(user_id)
# 操作：OSS文件删除 -> 清空user.avatar_url -> db.session.commit()
```

### 管理员认证接口 (admin_auth.py)

**Session 管理**
```python
# 管理员登录
POST /api/v1/admin_auth/login
# 查询：AdminUser.query.filter_by(username=username).first()
# 验证：admin_user.verify_password(password)
# 操作：login_user(admin_user, remember=remember)

# 管理员登出
GET /api/v1/admin_auth/logout
# 操作：logout_user()
```

### 文章管理接口 (article.py)

**文字记录处理**
```python
# 创建文字记录
POST /api/v1/articles/text-record
# 数据库操作流程：
# 1. 查询用户：User.query.get(user_id)
# 2. 创建音频记录：UserAudioRecord() -> db.session.add() -> db.session.flush()
# 3. 创建生成任务：GenerationTask() -> db.session.add() -> db.session.flush()
# 4. 创建任务映射：TaskRecordsMapping() -> db.session.add()
# 5. LLM生成标题标签
# 6. 创建文章和标签：create_article_and_tags()
# 7. 事务提交：db.session.commit()
```

**任务查询**
```python
# 按用户和月份查询任务
GET /api/v1/articles/tasks?user_id=<id>&year=<year>&month=<month>
# 查询：GenerationTask.query.filter() 使用 extract() 函数按月份筛选
# 排序：order_by(GenerationTask.created_at.desc())

# 查询单个任务状态
GET /api/v1/articles/tasks/<int:task_id>
# 查询：GenerationTask.query.get(task_id)
# 返回：包含状态描述的任务详情
```

## 数据库模型操作模式

### 核心模型关系

**User 模型** (`app/models/user.py`)
```python
# 关系定义
audio_records = db.relationship("UserAudioRecord", backref="user", lazy="dynamic")
generation_tasks = db.relationship("GenerationTask", backref="user", lazy="dynamic")
articles = db.relationship("Article", backref="author", lazy="dynamic")

# 常用操作
user.set_hashed_password(password)  # 密码加密
user.verify_password(password)      # 密码验证
user.set_username_by_time()         # 自动生成用户名
```

**Article 模型** (`app/models/article.py`)
```python
# 外键关系
author_id -> users.id
source_task_id -> generation_tasks.id

# 多对多关系（通过ArticleTag中间表）
tags = db.relationship("Tag", secondary="article_tags", backref="articles", lazy="dynamic")

# 文章引用关系（ArticleRelationship表）
citing_article_id -> articles.id    # 引用方
referenced_article_id -> articles.id # 被引用方
```

**Tag 模型** (`app/models/tag.py`)
```python
# 用户关联
user_id -> users.id
# 约束：每个用户的标签名唯一
__table_args__ = (db.UniqueConstraint("name", name="uk_name"),)
```

**GenerationTask 模型** (`app/models/generation_task.py`)
```python
# 任务状态字段
summary_status: 0-pending, 1-processing, 2-completed
langgraph_status: 0-pending, 1-processing, 2-completed, 3-failed

# 关系定义
audio_records = db.relationship("UserAudioRecord", secondary="task_records_mapping")
article = db.relationship("Article", backref="source_task", uselist=False)
```

**UserAudioRecord 模型** (`app/models/user_audio_record.py`)
```python
# 主要字段
transcript  # 语音转录文字内容
user_id     # 所属用户

# 通过TaskRecordsMapping表关联到GenerationTask
```

### 常用数据库操作模式

**查询操作**
```python
# 基础查询
User.query.get(user_id)                    # 主键查询
User.query.filter_by(email=email).first() # 条件查询
User.query.all()                           # 全量查询

# 关联查询
user.articles.all()                        # 通过关系获取关联数据
article.tags.all()                         # 多对多关系查询

# 复杂查询
GenerationTask.query.filter(
    GenerationTask.user_id == user_id,
    extract("year", GenerationTask.created_at) == year,
    extract("month", GenerationTask.created_at) == month
).order_by(GenerationTask.created_at.desc()).all()
```

**写入操作**
```python
# 创建记录
user = User(email=email)
db.session.add(user)
db.session.commit()

# 批量操作使用flush()获取ID
db.session.add(record)
db.session.flush()  # 获取自增ID但不提交事务
record_id = record.id

# 事务管理
try:
    # 多个数据库操作
    db.session.commit()
except Exception as e:
    db.session.rollback()
    raise e
```

**更新删除操作**
```python
# 更新
user = User.query.get(user_id)
user.username = new_username
db.session.commit()

# 删除
user = User.query.get(user_id)
db.session.delete(user)
db.session.commit()
```

### 特殊操作函数

**文章创建流程** (`create_article_and_tags()`)
```python
# 1. 创建Article记录
article = Article(author_id=user_id, ...)
db.session.add(article)
db.session.flush()

# 2. 处理Tag（查找已有或创建新标签）
existing_tag = Tag.query.filter_by(user_id=user_id, name=tag_name).first()

# 3. 创建ArticleTag关联
article_tag = ArticleTag(article_id=article.id, tag_id=tag_id)
db.session.add(article_tag)
```

**LLM集成的数据库操作**
```python
# 获取用户已有标签用于LLM提示
tags = Tag.query.filter_by(user_id=user_id).all()
tag_names = [tag.name for tag in tags]

# LLM生成后的数据库写入
title, tags = generate_title_tags(text, user_id)
article_id = create_article_and_tags(title, tags, user_id, task_id)
```