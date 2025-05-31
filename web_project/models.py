from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import db

Base = db.Model

class User(UserMixin, Base):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    cameras = db.relationship('Camera', backref='owner', lazy=True)
    alerts = db.relationship('Alert', backref='user', lazy='dynamic')
    alert_settings = db.relationship('AlertSettings', backref='user', uselist=False)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'

class Camera(Base):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False)
    url = db.Column(db.String(256), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    last_alert = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    alert_sound = db.Column(db.String(128), default='alert.mp3')  # Tên file âm thanh cảnh báo
    
    detections = db.relationship('Detection', backref='camera', lazy='dynamic')
    alerts = db.relationship('Alert', backref='camera', lazy=True)
    
    def __repr__(self):
        return f'<Camera {self.name} ({self.url})>'

class Detection(Base):
    id = db.Column(db.Integer, primary_key=True)
    object_type = db.Column(db.String(64))
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'))
    confidence = db.Column(db.Float)
    bounding_box = db.Column(db.String(128)) # Format: x1, y1, x2, y2
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(256))

    alert = db.relationship('Alert', backref='detection', lazy='dynamic')

    def __repr__(self):
        return f'<Detection {self.object_type} at {self.image_path}'


class Alert(Base):
    id = db.Column(db.Integer, primary_key=True)
    detection_id = db.Column(db.Integer, db.ForeignKey('detection.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='new')  # new, viewed, dismissed
    email_sent = db.Column(db.Boolean, default=False)
    image_path = db.Column(db.String(256))
    detection_type = db.Column(db.String(64))
    camera_id = db.Column(db.Integer, db.ForeignKey('camera.id'), nullable=False)
    
    def __repr__(self):
        return f'<Alert for detection {self.detection_id}>'

class AlertSettings(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    object_types = db.Column(db.String(256))  # Comma-separated list of dangerous objects
    confidence_thresh = db.Column(db.Float, default=0.7)
    cooldown_seconds = db.Column(db.Integer, default=30)  # Thời gian chờ giữa các cảnh báo (giây)
    
    def __repr__(self):
        return f'<AlertSettings for user {self.user_id}>'

class Email(Base):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email_address = db.Column(db.String(120), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Email {self.email_address}>'

