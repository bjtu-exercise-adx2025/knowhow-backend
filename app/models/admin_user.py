from flask_login import UserMixin

from app import db, login_manager


class AdminUser(UserMixin, db.Model):
    __tablename__ = 'AdminUser'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), index=True)
    password = db.Column(db.String(128))

    def verify_password(self, password):
        """验证密码是否正确"""
        return self.password == password


@login_manager.user_loader
def load_user(user_id):  # 创建用户加载回调函数，接受用户id作为参数
    admin_user = AdminUser.query.get(int(user_id))  # 通过user id在数据库中查询
    return admin_user  # 返回用户对象
