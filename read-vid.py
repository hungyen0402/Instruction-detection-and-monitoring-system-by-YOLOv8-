import cv2 as cv
import os 

video_path = r"C:\Users\hoang\Pictures\Camera Roll\WIN_20250522_16_05_29_Pro.mp4" # dia chi video 
images_folder = r"C:\Users\hoang\Documents\paint\frame2" # dia chi luu frame 

os.makedirs(images_folder, exist_ok=True) # neu folder chua ton tai thi lenh thuc thi 
cap = cv.VideoCapture(video_path)
current_frame = 0
while True:
    ret, frame = cap.read()
    if not ret:
        break
    elif current_frame % 10 == 0:
        name = os.path.join(images_folder, f"frame{current_frame}.jpg")  
        cv.imwrite(name, frame) 
    current_frame += 1

cap.release()
cv.destroyAllWindows()



