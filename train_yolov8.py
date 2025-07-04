from ultralytics import YOLO

if __name__ == '__main__':
    model = YOLO("runs/detect/train8/weights/best.pt")

    results = model.train(
    data=r"C:\Users\hoang\Documents\TTCS\bank robbery.v1i.yolov8\data.yaml",  # đường dẫn đến file data.yaml của dữ liệu mới
    epochs=100, # ở lần 1 đã train 50 epochs rồi, bây giờ sẽ train từ 51 tới 100       
    imgsz=640,
    batch=4,
    device=0,
    )