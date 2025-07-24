from datetime import timedelta


class Config:
    # 修改SQLALCHEMY_DATABASE_URI
    db_user_name = "***REMOVED_SECRET***"
    db_password = "***REMOVED_DB_PASSWORD***"
    db_host = "rm-2ze9140q8270wnd20no.mysql.rds.aliyuncs.com"
    db_name = "***REMOVED_SECRET***"

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{db_user_name}:{db_password}@{db_host}/{db_name}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = "***REMOVED_SECRET***"
    JWT_TOKEN_LOCATION = ["headers", "cookies"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_COOKIE_CSRF_PROTECT = False
    # 新增MySQL连接池配置
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_RECYCLE = 3600
    # FLASK-LOGIN配置
    SECRET_KEY = "***REMOVED_SECRET***"
    FLASK_ADMIN_SWATCH = "default"  # Or any valid theme name
    ADMIN_BASE_TEMPLATE = "admin/master.html"  # Explicitly set base template

    # OSS配置
    OSS_ACCESS_KEY_ID = "***REMOVED_OSS_ACCESS_KEY_ID***"  # 请填入您的AccessKey ID
    OSS_ACCESS_KEY_SECRET = (
        "***REMOVED_OSS_ACCESS_KEY_SECRET***"  # 请填入您的AccessKey Secret
    )
    OSS_ENDPOINT = "https://oss-cn-beijing.aliyuncs.com"  # 例如: https://oss-cn-hangzhou.aliyuncs.com
    OSS_BUCKET_NAME = "lanji-release"  # 您的Bucket名称


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    SQLALCHEMY_POOL_SIZE = 20
