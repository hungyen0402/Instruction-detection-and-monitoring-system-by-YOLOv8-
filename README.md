# Ứng dụng YOLOv8 cho Giám sát An ninh

Dự án này sử dụng YOLOv8 để phát hiện và cảnh báo các hoạt động bất thường trong hệ thống giám sát an ninh.

## Tính năng chính

- Phát hiện đối tượng sử dụng YOLOv8
- Hệ thống cảnh báo real-time
- Giao diện web để quản lý camera
- Gửi email cảnh báo
- Lưu trữ và xem lại các cảnh báo

## Cấu trúc project

```
TTCS/
├── web_project/          # Flask web application
│   ├── app.py           # Main application file
│   ├── routes.py        # Route handlers
│   ├── models.py        # Database models
│   ├── camera.py        # Camera management
│   ├── templates/       # HTML templates
│   ├── static/          # Static files (CSS, JS, images)
│   └── requirements.txt # Python dependencies
├── train_yolov8.py      # Training script
├── read-vid.py          # Video processing script
└── requirements.txt     # Main project dependencies
```

## Cài đặt

### Yêu cầu hệ thống
- Python 3.8+
- OpenCV
- PyTorch
- Flask

### Bước 1: Clone repository
```bash
git clone <your-repository-url>
cd TTCS
```

### Bước 2: Tạo virtual environment
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate
```

### Bước 3: Cài đặt dependencies
```bash
pip install -r requirements.txt
cd web_project
pip install -r requirements.txt
```

### Bước 4: Tải model YOLOv8
Bạn cần tải các file model sau và đặt vào thư mục gốc:
- `yolov8n.pt` (YOLOv8 nano model)
- `best.pt` (trained model)

Có thể tải từ: https://github.com/hungyen0402/Instruction-detection-and-monitoring-system-by-YOLOv8-/tags

### Bước 5: Khởi tạo database
```bash
cd web_project
python run_migration.py
```

### Bước 6: Chạy ứng dụng
```bash
cd web_project
python app.py
```

Truy cập: http://localhost:5000

## Sử dụng

1. **Thêm camera**: Vào trang "Add Camera" để thêm camera mới
2. **Cấu hình cảnh báo**: Vào "Alert Settings" để cấu hình email và âm thanh cảnh báo
3. **Xem cảnh báo**: Dashboard sẽ hiển thị các cảnh báo real-time

## Training model

Để train model mới:

```bash
python train_yolov8.py
```

## Lưu ý

- Các file model (.pt) được push lên release và dataset không được push lên GitHub do kích thước lớn
- Database files (.db) được ignore để tránh conflict
- Virtual environment (venv/) không được push lên GitHub

## Tác giả

Hoàng Đức Hùng 
