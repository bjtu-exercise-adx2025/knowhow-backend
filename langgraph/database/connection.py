"""
数据库连接管理

提供与项目主数据库的连接管理，复用现有的SQLAlchemy实例
"""

import sys
import os
from typing import Optional

# 添加项目根目录到Python路径，以便导入项目模块
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.extensions import db
from ..utils.exceptions import DatabaseOperationError, ERROR_CODES


class DatabaseConnection:
    """数据库连接管理器"""
    
    def __init__(self):
        """
        初始化数据库连接管理器
        复用项目现有的SQLAlchemy实例
        """
        self.db = db
        self._connection_tested = False
    
    def test_connection(self) -> bool:
        """
        测试数据库连接是否正常
        
        Returns:
            连接是否正常
        """
        try:
            # 检查是否在Flask应用上下文中
            from flask import has_app_context
            
            if not has_app_context():
                # 尝试创建应用上下文
                try:
                    from app import create_app
                    app = create_app()
                    with app.app_context():
                        from sqlalchemy import text
                        result = self.db.session.execute(text('SELECT 1')).fetchone()
                        self._connection_tested = True
                        return result is not None
                except Exception:
                    # 如果无法创建应用上下文，返回False但不抛出异常
                    self._connection_tested = False
                    return False
            else:
                # 在应用上下文中，直接测试连接
                from sqlalchemy import text
                result = self.db.session.execute(text('SELECT 1')).fetchone()
                self._connection_tested = True
                return result is not None
                
        except Exception as e:
            raise DatabaseOperationError(
                f"Database connection test failed: {str(e)}",
                ERROR_CODES["DB_CONNECTION_FAILED"]
            )
    
    def get_session(self):
        """
        获取数据库会话
        
        Returns:
            SQLAlchemy会话对象
        """
        if not self._connection_tested:
            self.test_connection()
        
        return self.db.session
    
    def execute_query(self, query: str, params: Optional[dict] = None):
        """
        执行原生SQL查询
        
        Args:
            query: SQL查询语句
            params: 查询参数
            
        Returns:
            查询结果
        """
        try:
            from sqlalchemy import text
            session = self.get_session()
            if params:
                result = session.execute(text(query), params)
            else:
                result = session.execute(text(query))
            return result
        except Exception as e:
            raise DatabaseOperationError(
                f"Query execution failed: {str(e)}",
                ERROR_CODES["DB_OPERATION_FAILED"],
                {"query": query, "params": params}
            )
    
    def commit(self):
        """提交事务"""
        try:
            self.db.session.commit()
        except Exception as e:
            self.db.session.rollback()
            raise DatabaseOperationError(
                f"Transaction commit failed: {str(e)}",
                ERROR_CODES["DB_TRANSACTION_FAILED"]
            )
    
    def rollback(self):
        """回滚事务"""
        try:
            self.db.session.rollback()
        except Exception as e:
            raise DatabaseOperationError(
                f"Transaction rollback failed: {str(e)}",
                ERROR_CODES["DB_TRANSACTION_FAILED"]
            )
    
    def close(self):
        """关闭数据库连接"""
        try:
            self.db.session.close()
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to close database connection: {str(e)}",
                ERROR_CODES["DB_CONNECTION_FAILED"]
            )