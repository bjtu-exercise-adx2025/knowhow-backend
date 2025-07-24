from datetime import timedelta


class Config:
    # 修改SQLALCHEMY_DATABASE_URI
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://routhleck:malaoshit@8.216.85.231/eeg'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = '***REMOVED_SECRET***'
    JWT_TOKEN_LOCATION = ['headers', 'cookies']
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_CSRF_PROTECT = False
    # 新增MySQL连接池配置
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_RECYCLE = 3600
    # FLASK-LOGIN配置
    SECRET_KEY = '***REMOVED_SECRET***'
    FLASK_ADMIN_SWATCH = 'default'  # Or any valid theme name
    ADMIN_BASE_TEMPLATE = 'admin/master.html'  # Explicitly set base template


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    SQLALCHEMY_POOL_SIZE = 20
