from flask_mail import Message
from flask import current_app, render_template
from threading import Thread
from datetime import datetime, timedelta
from models import db, Camera
from flask_mail import Mail

mail = Mail()

def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_alert_email(user_email, camera_name, detection_type, confidence, image_path):
    """Gửi email cảnh báo khi phát hiện đối tượng nguy hiểm"""
    app = current_app._get_current_object()
    subject = f'Cảnh báo an ninh - Camera {camera_name}'
    
    msg = Message(subject,
                 sender=app.config['MAIL_USERNAME'],
                 recipients=[user_email])
                 
    msg.html = render_template('email/alert.html',
                             camera_name=camera_name,
                             detection_type=detection_type,
                             confidence=confidence,
                             timestamp=datetime.now())
                             
    # Đính kèm ảnh
    with app.open_resource(image_path) as fp:
        msg.attach('detection.jpg', 'image/jpeg', fp.read())
    
    Thread(target=send_async_email, args=(app, msg)).start()

def can_send_alert(camera, now=None):
    if now is None:
        now = datetime.utcnow()
    
    # Kiểm tra cooldown period
    cooldown = timedelta(seconds=camera.owner.alert_settings.cooldown_seconds)
    if camera.last_alert is None or now - camera.last_alert > cooldown:
        camera.last_alert = now
        return True
    return False 