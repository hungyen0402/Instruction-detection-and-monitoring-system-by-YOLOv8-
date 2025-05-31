import cv2
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import os
from threading import Thread, Lock
import time
from flask import current_app
from flask_socketio import emit
from models import db, Alert, Camera
import logging
from flask import current_app
from functools import lru_cache

class CameraStream:
    def __init__(self, camera_id, url, model_path, socketio=None):
        self.camera_id = camera_id
        self.url = url
        self.model_path = model_path
        self.socketio = socketio
        self.running = False
        self.thread = None
        self.frame_lock = Lock()
        self.latest_frame = None
        self.show_boxes = True
        self.app = None  # Lưu trữ Flask app instance
        
        # Log SocketIO initialization
        if self.socketio:
            print(f"[SocketIO] Initialized for camera {camera_id}")
        else:
            print(f"[SocketIO] Not initialized for camera {camera_id}")
        
        # Khởi tạo VideoCapture với buffer size nhỏ hơn
        try:
            cam_index = int(url)
            self.stream = cv2.VideoCapture(cam_index)
        except (ValueError, TypeError):
            self.stream = cv2.VideoCapture(url)
        
        # Cấu hình buffer size và resolution
        self.stream.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        self.stream.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.stream.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        
        self.connected = self.stream.isOpened()
        
        if not self.connected:
            print(f"[Camera] Không thể kết nối tới camera {camera_id} với URL: {url}")
            try:
                with current_app.app_context():
                    camera = Camera.query.get(camera_id)
                    if camera:
                        camera.connection_status = "Không thể kết nối"
                        db.session.commit()
            except Exception as e:
                print(f"[Camera] Lỗi cập nhật trạng thái camera: {e}")
        else:
            print(f"[Camera] Kết nối thành công tới camera {camera_id}")
            ret, frame = self.stream.read()
            if ret:
                with self.frame_lock:
                    self.latest_frame = frame
        
        # Khởi tạo model YOLO với cấu hình tối ưu
        try:
            self.model = YOLO(model_path)
            # Cấu hình model để tối ưu tốc độ
            self.model.conf = 0.5  # Ngưỡng confidence
            self.model.iou = 0.45  # IoU threshold
            self.model.max_det = 50  # Số lượng detection tối đa
        except Exception as e:
            print(f"Lỗi khởi tạo model YOLO: {e}")
            self.model = None

    def start(self):
        if not self.connected:
            return False
        
        # Lưu Flask app instance
        self.app = current_app._get_current_object()
            
        self.running = True
        self.thread = Thread(target=self._update_frame)
        self.thread.daemon = True
        self.thread.start()
        return True
        
    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        if self.stream:
            self.stream.release()
            
    def toggle_boxes(self):
        if self.model:
            self.show_boxes = not self.show_boxes
        return self.show_boxes

    @lru_cache(maxsize=32)
    def get_dangerous_objects(self, object_types):
        return [obj.strip().lower() for obj in object_types.split(',')]
        
    def _update_frame(self):
        while self.running:
            try:
                ret, frame = self.stream.read()
                if not ret:
                    print(f"[Camera] Không thể đọc frame từ camera {self.camera_id}")
                    self.stream.release()
                    self.stream = cv2.VideoCapture(self.url)
                    self.connected = self.stream.isOpened()
                    continue

                # Giảm kích thước frame trước khi xử lý
                processed_frame = cv2.resize(frame, (640, 480))

                if self.model and self.show_boxes:
                    # Sử dụng model với cấu hình tối ưu
                    results = self.model(processed_frame, verbose=False)
                    processed_frame = results[0].plot()
                    
                    # Gửi detections qua WebSocket
                    if self.socketio:
                        detections = []
                        for r in results:
                            for box in r.boxes:
                                class_id = int(box.cls[0])
                                class_name = self.model.names[class_id]
                                confidence = float(box.conf[0])
                                detections.append({
                                    'class': class_name,
                                    'confidence': confidence
                                })
                        
                        print(f"[SocketIO] Sending detections for camera {self.camera_id}: {detections}")
                        self.socketio.emit('detections', {
                            'camera_id': self.camera_id,
                            'detections': detections
                        }, namespace='/camera')
                    
                    # Kiểm tra dangerous object và gửi cảnh báo
                    for r in results:
                        for box in r.boxes:
                            class_id = int(box.cls[0])
                            class_name = self.model.names[class_id].lower()  # Chuyển về chữ thường
                            confidence = float(box.conf[0])
                            
                            # Sử dụng Flask app context đã lưu
                            with self.app.app_context():
                                try:
                                    camera = Camera.query.get(self.camera_id)
                                    if camera and camera.owner:
                                        alert_settings = camera.owner.alert_settings
                                        if alert_settings:
                                            dangerous_objects = self.get_dangerous_objects(alert_settings.object_types)
                                            print(f"\n[Alert] Checking conditions for camera {camera.id}:")
                                            print(f"[Alert] Detected: {class_name} ({confidence:.2f})")
                                            print(f"[Alert] Dangerous objects: {dangerous_objects}")
                                            print(f"[Alert] Confidence threshold: {alert_settings.confidence_thresh}")
                                            
                                            if class_name in dangerous_objects and confidence >= alert_settings.confidence_thresh:
                                                try:
                                                    print(f"[Alert] Sending alert for {class_name}")
                                                    if self.socketio:
                                                        self.socketio.emit('alert', {
                                                            'camera_id': camera.id,
                                                            'camera_name': camera.name,
                                                            'detection_type': class_name,
                                                            'confidence': confidence,
                                                            'timestamp': datetime.utcnow().strftime('%H:%M:%S %d/%m/%Y')
                                                        }, namespace='/camera')
                                                        print(f"[Alert] Alert event emitted successfully")
                                                    
                                                    # Tạo alert mới
                                                    alert = Alert(
                                                        detection_type=class_name,
                                                        camera_id=camera.id,
                                                        user_id=camera.user_id,
                                                        timestamp=datetime.utcnow()
                                                    )
                                                    
                                                    # Lưu frame khi có cảnh báo
                                                    try:
                                                        # Tạo thư mục alerts nếu chưa tồn tại
                                                        alerts_dir = os.path.join('static', 'alerts')
                                                        os.makedirs(alerts_dir, exist_ok=True)
                                                        
                                                        # Tạo tên file duy nhất dựa trên timestamp
                                                        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
                                                        filename = f"alert_{camera.id}_{timestamp}.jpg"
                                                        filepath = os.path.join(alerts_dir, filename)
                                                        
                                                        # Lưu frame với bounding box
                                                        cv2.imwrite(filepath, processed_frame)
                                                        
                                                        # Cập nhật đường dẫn ảnh cho alert
                                                        alert.image_path = filepath
                                                        print(f"[Alert] Saved alert image to {filepath}")
                                                    except Exception as e:
                                                        print(f"[Alert] Error saving alert image: {str(e)}")
                                                        logging.error(f"[Alert] Lỗi lưu ảnh cảnh báo: {str(e)}")
                                                    
                                                    db.session.add(alert)
                                                    camera.last_alert = datetime.utcnow()
                                                    print(f"[Alert] Attempting to commit alert for camera {camera.id}")
                                                    db.session.commit()
                                                    print(f"[Alert] Successfully committed alert with ID: {alert.id}")
                                                    
                                                except Exception as e:
                                                    db.session.rollback()
                                                    print(f"[Alert] Error during alert commit for camera {camera.id}: {str(e)}")
                                                    logging.error(f"[Alert] Lỗi commit cảnh báo cho camera {camera.id}: {str(e)}")
                                except Exception as e:
                                    # Catch errors during query or add before commit
                                    db.session.rollback()
                                    print(f"[Alert] Error during database operation (query/add) for camera {camera.id}: {str(e)}")
                                    logging.error(f"[Alert] Lỗi thao tác database (query/add) cho camera {camera.id}: {str(e)}")
                
                with self.frame_lock:
                    self.latest_frame = processed_frame
                    
                time.sleep(0.03)  # Giảm delay xuống 30ms để tăng FPS
                
            except Exception as e:
                print(f"[Error] Lỗi trong quá trình xử lý frame: {e}")
                time.sleep(1)
                
    def get_frame(self):
        if not self.connected:
            return None
            
        with self.frame_lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

class CameraManager:
    _instances = {}
    
    @classmethod
    def get_stream(cls, camera_id, socketio=None):
        if camera_id not in cls._instances:
            with current_app.app_context():
                camera = Camera.query.get(camera_id)
                if camera:
                    stream = CameraStream(
                        camera_id=camera_id,
                        url=camera.url,
                        model_path=current_app.config['YOLO_MODEL_PATH'],
                        socketio=socketio
                    )
                    stream.start()
                    cls._instances[camera_id] = stream
        return cls._instances.get(camera_id)
    
    @classmethod
    def stop_stream(cls, camera_id):
        if camera_id in cls._instances:
            cls._instances[camera_id].stop()
            del cls._instances[camera_id]
            
    @classmethod
    def toggle_boxes(cls, camera_id):
        if camera_id in cls._instances:
            return cls._instances[camera_id].toggle_boxes()
        return False 