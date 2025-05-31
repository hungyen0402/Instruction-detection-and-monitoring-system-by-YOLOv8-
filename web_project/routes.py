from flask import Blueprint, render_template, request, redirect, url_for, flash, Response, current_app, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from flask_socketio import emit, SocketIO
from urllib.parse import urlparse
import cv2
from extensions import db, socketio, login_manager
from models import User, Camera, Alert, AlertSettings
from camera import CameraManager
from utils import send_alert_email, can_send_alert
from utils.detector import CameraStream
import time
import numpy as np
import logging
import re
from datetime import datetime
import os

bp = Blueprint('bp', __name__)

@bp.route('/') #trang chủ
def index():
    if current_user.is_authenticated:
        return redirect(url_for('bp.dashboard'))
    return render_template('index.html')

@bp.route('/dashboard')
@login_required
def dashboard():
    cameras = Camera.query.filter_by(user_id=current_user.id).all()
    alerts = Alert.query.filter_by(user_id=current_user.id).order_by(Alert.timestamp.desc()).limit(10).all()
    return render_template('dashboard.html', cameras=cameras, alerts=alerts)

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('bp.dashboard'))
    
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form['username']).first()
        if user is None or not user.check_password(request.form['password']):
            flash('Sai tên đăng nhập hoặc mật khẩu') # thông báo 1 lần 
            return redirect(url_for('bp.login'))
        
        login_user(user, remember=request.form.get('remember_me') == 'true') # chức năng ghi nhớ đăng nhập 
        next_page = request.args.get('next')
        # phòng trường hợp kẻ xấu dẫn tới 1 trang khác 
        if not next_page or url_parse(next_page).netloc != '': # dùng url_parse để tách next_page thành các thành phần url
            next_page = url_for('bp.dashboard')
        return redirect(next_page)
    
    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('bp.index'))
        
    if request.method == 'POST':
        # Kiểm tra xác nhận mật khẩu
        if request.form['password'] != request.form['confirm_password']:
            flash('Mật khẩu xác nhận không khớp!')
            return redirect(url_for('bp.register'))
            
        # Kiểm tra username đã tồn tại chưa
        if User.query.filter_by(username=request.form['username']).first():
            flash('Tên đăng nhập đã tồn tại!')
            return redirect(url_for('bp.register'))
            
        # Kiểm tra email đã tồn tại chưa
        if User.query.filter_by(email=request.form['email']).first():
            flash('Email đã được sử dụng!')
            return redirect(url_for('bp.register'))
            
        try:
            user = User(
                username=request.form['username'],
                email=request.form['email']
            )
            user.set_password(request.form['password'])
            db.session.add(user)
            db.session.commit()
            flash('Đăng ký thành công!')
            return redirect(url_for('bp.login'))
        except Exception as e:
            db.session.rollback()
            flash('Có lỗi xảy ra khi đăng ký. Vui lòng thử lại!')
            return redirect(url_for('bp.register'))
        
    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('bp.index'))

@bp.route('/delete_alert/<int:alert_id>', methods=['DELETE'])
@login_required
def delete_alert(alert_id):
    try:
        alert = Alert.query.get_or_404(alert_id)
        
        # Kiểm tra quyền xóa (chỉ cho phép xóa cảnh báo của chính mình)
        if alert.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Không có quyền xóa cảnh báo này'}), 403
            
        # Xóa file ảnh nếu tồn tại
        if alert.image_path and os.path.exists(alert.image_path):
            try:
                os.remove(alert.image_path)
            except Exception as e:
                print(f"Lỗi xóa file ảnh: {e}")
                
        # Xóa cảnh báo khỏi database
        db.session.delete(alert)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        print(f"Lỗi xóa cảnh báo: {e}")
        return jsonify({'success': False, 'message': 'Có lỗi xảy ra khi xóa cảnh báo'}), 500

@bp.route('/add_camera', methods=['GET', 'POST'])
@login_required
def add_camera():
    if request.method == 'POST':
        # Kiểm tra tên camera trùng lặp
        if Camera.query.filter_by(name=request.form['name']).first():
            flash('Trùng tên camera')
            return redirect(url_for('bp.add_camera'))
            
        # Kiểm tra URL camera trùng lặp
        if Camera.query.filter_by(url=request.form['url']).first():
            flash('Trùng URL camera')
            return redirect(url_for('bp.add_camera'))
            
        # Kiểm tra URL camera trước khi lưu
        url = request.form['url']
        try:
            cam_index = int(url)
            cap = cv2.VideoCapture(cam_index)
        except (ValueError, TypeError):
            cap = cv2.VideoCapture(url)
        if not cap.isOpened():
            flash('Camera không khả thi. Vui lòng kiểm tra lại URL.')
            return redirect(url_for('bp.add_camera'))
        cap.release()
        
        camera = Camera(
            name=request.form['name'],
            url=url,
            user_id=current_user.id,
            alert_sound=request.form.get('alert_sound', 'alert.mp3')
        )
        db.session.add(camera)
        db.session.commit()
        flash('Camera đã được thêm thành công!')
        return redirect(url_for('bp.dashboard'))
        
    return render_template('add_camera.html')

@bp.route('/camera/<int:camera_id>', methods=['GET', 'POST'])
@login_required
def camera_detail(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    if camera.user_id != current_user.id:
        flash('Bạn không có quyền truy cập camera này')
        return redirect(url_for('bp.index'))
    
    # Lấy luồng camera từ CameraManager
    stream = CameraManager.get_stream(camera_id, socketio)
    
    if request.method == 'POST':
        try:
            # Cập nhật trạng thái camera
            is_active = request.form.get('is_active') == 'on'
            camera.is_active = is_active
            
            # Quản lý luồng video
            if is_active:
                # Nếu bật camera, lấy luồng video (tự động start nếu chưa có)
                stream = CameraManager.get_stream(camera_id, socketio)
            else:
                # Nếu tắt camera, dừng luồng video
                CameraManager.stop_stream(camera_id)
            
            db.session.commit()
            flash('Cài đặt camera đã được cập nhật!')
        except Exception as e:
            db.session.rollback()
            logging.exception(e)  # Ghi lại lỗi chi tiết
            flash('Có lỗi xảy ra khi cập nhật cài đặt. Vui lòng thử lại!')
    
    # Kiểm tra trạng thái kết nối thực tế
    is_online = stream is not None and stream.connected
    
    # Lấy danh sách cảnh báo gần đây
    alerts = Alert.query.filter_by(
        camera_id=camera_id
    ).order_by(Alert.timestamp.desc()).limit(10).all()
    
    # Kiểm tra xem có cảnh báo mới không (trong 60 giây gần nhất)
    latest_alert = Alert.query.filter_by(
        camera_id=camera_id,
    ).order_by(Alert.timestamp.desc()).first()
    
    has_new_alert = latest_alert and (datetime.utcnow() - latest_alert.timestamp).total_seconds() < 60
    
    return render_template('camera_detail.html', 
                         camera=camera, 
                         alerts=alerts, 
                         is_online=is_online,
                         has_new_alert=has_new_alert,
                         now=datetime.utcnow())  # Thêm thời gian hiện tại để tính toán thời gian cảnh báo

@bp.route('/toggle_boxes/<int:camera_id>')
@login_required
def toggle_boxes(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    if camera.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
        
    show_boxes = CameraManager.toggle_boxes(camera_id)
    return jsonify({'show_boxes': show_boxes})

def create_error_image(message):
    # Tạo ảnh đen kích thước 640x480
    img = np.zeros((480, 640, 3), dtype=np.uint8)
    
    # Thêm thông báo lỗi
    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(message, font, 1, 2)[0]
    text_x = (img.shape[1] - text_size[0]) // 2
    text_y = (img.shape[0] + text_size[1]) // 2
    
    cv2.putText(img, message, (text_x, text_y), font, 1, (255, 255, 255), 2)
    
    return img

def generate_frames(camera_id):
    stream = CameraManager.get_stream(camera_id, socketio)
    if stream is None:
        error_img = create_error_image("Không thể kết nối tới camera")
        ret, buffer = cv2.imencode('.jpg', error_img)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        return
    
    while True:
        try:
            frame = stream.get_frame()
            if frame is None or frame.size == 0:
                error_img = create_error_image("Camera bị lỗi")
                ret, buffer = cv2.imencode('.jpg', error_img)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                time.sleep(3)
                continue
            
            ret, buffer = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
        except Exception as e:
            logging.exception(e)
            error_img = create_error_image("Lỗi camera")
            ret, buffer = cv2.imencode('.jpg', error_img)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            time.sleep(3)

@bp.route('/video_feed/<int:camera_id>')
@login_required
def video_feed(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    if camera.user_id != current_user.id:
        flash('Bạn không có quyền truy cập camera này')
        return redirect(url_for('bp.index'))
    
    # Kiểm tra trạng thái active của camera
    if not camera.is_active:
        error_img = create_error_image("Camera đã bị tắt")
        ret, buffer = cv2.imencode('.jpg', error_img)
        return Response(b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n',
                      mimetype='multipart/x-mixed-replace; boundary=frame')
    
    # Khởi tạo stream với socketio
    stream = CameraManager.get_stream(camera_id, socketio)
    if stream is None:
        error_img = create_error_image("Không thể kết nối tới camera")
        ret, buffer = cv2.imencode('.jpg', error_img)
        return Response(b'--frame\r\n'
                      b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n',
                      mimetype='multipart/x-mixed-replace; boundary=frame')
        
    return Response(generate_frames(camera_id),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@socketio.on('connect', namespace='/camera')
def handle_connect():
    if not current_user.is_authenticated:
        return False
    print(f"[WebSocket] Client connected: {request.sid}")
    emit('connected', {'status': 'connected'})

@socketio.on('disconnect', namespace='/camera')
def handle_disconnect():
    print(f"[WebSocket] Client disconnected: {request.sid}")

@socketio.on('register_camera', namespace='/camera')
def handle_register_camera(data):
    if not current_user.is_authenticated:
        return False
    camera_id = data.get('camera_id')
    if camera_id:
        print(f"[WebSocket] Camera {camera_id} registered for client {request.sid}")
        return {'status': 'registered', 'camera_id': camera_id}
    return {'status': 'error', 'message': 'Invalid camera ID'}

@bp.route('/camera/<int:camera_id>/delete', methods=['POST'])
@login_required
def delete_camera(camera_id):
    # Kiểm tra lại trạng thái đăng nhập một cách tường minh
    if not current_user.is_authenticated:
        return jsonify({'success': False, 'message': 'Người dùng chưa xác thực'}), 401

    try:
        camera = Camera.query.get_or_404(camera_id)
        if camera.user_id != current_user.id:
            return jsonify({'success': False, 'message': 'Không có quyền xóa camera này'}), 403
            
        # Dừng stream camera nếu đang chạy
        CameraManager.stop_stream(camera_id)
        
        # Xóa tất cả cảnh báo liên quan đến camera
        Alert.query.filter_by(camera_id=camera_id).delete()
        
        # Xóa camera
        db.session.delete(camera)
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Camera đã được xóa thành công'})
    except Exception as e:
        db.session.rollback()
        print(f"Lỗi xóa camera: {str(e)}")
        return jsonify({'success': False, 'message': 'Có lỗi xảy ra khi xóa camera'}), 500

@bp.route('/camera/<int:camera_id>/status', methods=['GET'])
@login_required
def get_camera_status(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    if camera.user_id != current_user.id:
        abort(403)
    return jsonify({'status': camera.connection_status})

@bp.route('/camera/<int:camera_id>/status', methods=['POST'])
@login_required
def update_camera_status(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    if camera.user_id != current_user.id:
        abort(403)
    
    data = request.get_json()
    if 'status' not in data:
        return jsonify({'error': 'Status not provided'}), 400
    
    try:
        camera.connection_status = bool(data['status'])
        db.session.commit()
        return jsonify({'status': camera.connection_status})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500 

@bp.route('/api/camera/<int:camera_id>/status')
@login_required
def camera_status(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    if camera.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Không có quyền truy cập"}), 403
    
    stream = CameraManager.get_stream(camera_id)
    if stream is None or not stream.connected:
        return jsonify({"status": "error", "message": "Không thể kết nối tới camera"})
    
    return jsonify({"status": "ok", "message": "Camera hoạt động bình thường"}) 

@bp.route('/stop_stream/<int:camera_id>', methods=['POST'])
@login_required
def stop_stream(camera_id):
    camera = Camera.query.get_or_404(camera_id)
    if camera.user_id != current_user.id:
        return jsonify({'error': 'Unauthorized'}), 403
    CameraManager.stop_stream(camera_id)
    return jsonify({'status': 'stopped'})

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id)) 

@bp.route('/alert-settings')
@login_required
def alert_settings():
    alert_settings = AlertSettings.query.filter_by(user_id=current_user.id).first()
    if not alert_settings:
        alert_settings = AlertSettings(
            user_id=current_user.id,
            object_types='dangerous object,weapon',  # Default values
            confidence_thresh=0.5,
            cooldown_seconds=30
        )
        db.session.add(alert_settings)
        db.session.commit()
    
    # Convert object_types string to list for template
    selected_objects = alert_settings.object_types.split(',') if alert_settings.object_types else []
    
    return render_template('alert_settings.html', 
                         alert_settings=alert_settings,
                         selected_objects=selected_objects)

@bp.route('/update-alert-settings', methods=['POST'])
@login_required
def update_alert_settings():
    alert_settings = AlertSettings.query.filter_by(user_id=current_user.id).first()
    if not alert_settings:
        alert_settings = AlertSettings(user_id=current_user.id)
        db.session.add(alert_settings)
    
    # Get selected object types
    selected_types = []
    if request.form.get('dangerous_object'):
        selected_types.append('dangerous object')
    if request.form.get('weapon'):
        selected_types.append('weapon')
    
    # Update settings
    alert_settings.object_types = ','.join(selected_types)
    alert_settings.confidence_thresh = float(request.form.get('confidence', 0.5))
    alert_settings.cooldown_seconds = int(request.form.get('cooldown', 30))
    
    # Debug logging
    print(f"Updated alert settings:")
    print(f"Object types: {alert_settings.object_types}")
    print(f"Confidence threshold: {alert_settings.confidence_thresh}")
    print(f"Cooldown seconds: {alert_settings.cooldown_seconds}")
    
    db.session.commit()
    flash('Cài đặt cảnh báo đã được cập nhật', 'success')
    return redirect(url_for('bp.alert_settings')) 