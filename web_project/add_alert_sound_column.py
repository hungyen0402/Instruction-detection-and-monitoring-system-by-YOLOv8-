from flask import Flask
from extensions import db
from models import User, Camera, Alert, AlertSettings, Email
from config import Config
from sqlalchemy import text

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

if __name__ == '__main__':
    with app.app_context():
        # Thêm cột alert_sound vào bảng camera
        with db.engine.connect() as conn:
            conn.execute(text('ALTER TABLE camera ADD COLUMN alert_sound VARCHAR(128) DEFAULT "alert.mp3"'))
            conn.commit()
        print("Đã thêm cột alert_sound vào bảng camera") 