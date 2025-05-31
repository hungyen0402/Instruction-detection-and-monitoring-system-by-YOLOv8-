from flask import Flask
from flask_migrate import Migrate
from extensions import db
from models import User, Camera, Alert, AlertSettings, Email
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)
migrate = Migrate(app, db)

if __name__ == '__main__':
    with app.app_context():
        # Tạo tất cả bảng nếu chưa tồn tại
        db.create_all()
        
        # Chạy migration
        from alembic import command
        from alembic.config import Config as AlembicConfig
        
        alembic_cfg = AlembicConfig("alembic.ini")
        command.upgrade(alembic_cfg, "head") 