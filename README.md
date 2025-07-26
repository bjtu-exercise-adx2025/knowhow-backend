# Project2025-Backend

## 项目结构

```
project2025-backend/
├── app/                    # Flask 后端应用
│   ├── api/               # API 接口
│   │   └── v1/           # API v1 版本
│   ├── models/           # 数据模型
│   ├── algorithm/        # 算法模块
│   ├── utils/            # 工具函数
│   ├── static/           # 静态文件
│   └── templates/        # 模板文件
├── admin/                # React 前端管理界面
│   ├── src/             # 源代码
│   ├── public/          # 静态资源
│   └── package.json     # 前端依赖配置
├── tests/               # 测试文件
├── run.py              # 应用入口
└── README.md           # 项目说明
```

## 功能特性

### 后端功能
- **用户管理**: 用户注册、登录、信息管理
- **预约管理**: 预约创建、状态跟踪、时间管理
- **健康档案**: 用户健康信息记录和管理
- **商品管理**: 商品信息、库存管理
- **订单系统**: 购物车、订单处理
- **店铺管理**: 理疗店铺信息管理
- **数据分析**: EEG 数据分析报告生成
- **RESTful API**: 完整的 API 接口支持

### 前端功能
- **现代化 UI**: 基于 React + TypeScript + Tailwind CSS
- **响应式设计**: 支持移动端和桌面端
- **组件化架构**: 可复用的 UI 组件
- **状态管理**: 高效的状态管理方案

## 技术栈

### 后端
- **Flask**: Web 框架
- **SQLAlchemy**: ORM 数据库操作
- **Flask-JWT-Extended**: JWT 认证
- **PyMySQL**: MySQL 数据库连接
- **Gunicorn**: WSGI 服务器（生产环境）

### 前端
- **React 18**: 前端框架
- **TypeScript**: 类型安全
- **Vite**: 构建工具
- **Tailwind CSS**: 样式框架
- **Radix UI**: 组件库
- **React Router**: 路由管理
- **Axios**: HTTP 客户端

### 数据库
- **MySQL**: 主数据库

## 环境要求

- Python 3.8+
- Node.js 16.0+
- MySQL 5.7+
- pnpm/npm/yarn

## 安装和配置

### 1. 克隆项目

```bash
git clone <repository-url>
cd project2025-backend
```

### 2. 快速环境设置（推荐）

```bash
# 一键设置环境
./setup_environment.sh
```

### 3. 手动环境配置

#### 创建虚拟环境
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows
```

#### 安装 Python 依赖
```bash
pip install -r requirements.txt
```

#### 数据库配置
1. 创建 MySQL 数据库
```sql
CREATE DATABASE eeg CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. 修改数据库连接配置（`app/config.py`）
```python
SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://username:password@localhost/eeg'
```

### 4. 前端环境配置

```bash
cd admin
pnpm install  # 或 npm install
```

## 开发环境运行

### 启动后端服务

```bash
# 激活虚拟环境
source venv/bin/activate

# 运行开发服务器
python run.py
```

后端服务将在 `https://127.0.0.1:8888` 启动

### 启动前端服务

```bash
cd admin
pnpm run dev  # 或 npm run dev
```

前端服务将在 `http://localhost:5173` 启动

### 访问地址

- **后端 API**: https://127.0.0.1:8888
- **前端管理界面**: 
  - 开发环境: http://localhost:5173
  - 生产环境: https://127.0.0.1:8888/admin
- **API 文档**: https://127.0.0.1:8888/api/docs

> **注意**: `/admin` 路由会自动检测是否存在构建后的前端文件：
> - 如果存在 `admin/dist/` 目录，则服务静态文件（生产环境）
> - 如果不存在，则重定向到 React 开发服务器（开发环境）

## 生产环境部署

### 1. 构建前端

```bash
# 方法一：使用构建脚本
./build_admin.sh

# 方法二：手动构建
cd admin
pnpm install
pnpm run build
cd ..
```

构建产物将生成在 `admin/dist/` 目录

### 2. 配置生产环境

修改 `app/config.py` 中的配置：
```python
class ProductionConfig(Config):
    DEBUG = False
    SQLALCHEMY_POOL_SIZE = 20
    # 其他生产环境配置
```

### 3. 使用启动脚本（推荐）

```bash
# 生产环境启动
./start_production.sh

# 开发环境启动
./start_development.sh
```

### 4. 手动启动 Gunicorn

```bash
# 使用配置文件启动（推荐）
gunicorn -c gunicorn.conf.py run:app

# 或使用命令行参数启动
nohup gunicorn --bind 0.0.0.0:8888 --timeout 120 --workers 4 run:app &
```

### 5. 使用 Nginx 反向代理（推荐）

创建 Nginx 配置文件：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8888;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /path/to/your/app/static/;
    }
}
```

### 6. 使用 systemd 管理服务

创建服务文件 `/etc/systemd/system/project2025-backend.service`：
```ini
[Unit]
Description=Project 2025 System
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/project2025-backend
Environment=PATH=/path/to/project2025-backend/venv/bin
ExecStart=/path/to/project2025-backend/venv/bin/gunicorn --bind 0.0.0.0:8888 run:app
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl enable project2025-backend
sudo systemctl start project2025-backend
sudo systemctl status project2025-backend
```


## 测试

### 运行单元测试
```bash
python tests/test.py
```

## 日志

应用日志文件位于 `app/logs/app.log`，支持日志轮转和级别控制。

## 安全配置

- JWT 令牌认证
- 密码加密存储
- 请求频率限制
- CORS 配置
- SQL 注入防护

### 日志查看

```bash
# 查看应用日志
tail -f app/logs/app.log

# 查看系统服务日志
sudo journalctl -u project2025-backend -f
```