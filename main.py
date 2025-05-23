import cv2
cap = cv2.VideoCapture(2)

# 分辨率
width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

# 帧率
fps = cap.get(cv2.CAP_PROP_FPS)

print("扫描可用摄像头设备...")
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f"摄像头设备 {i} 可用")
        cap.release()
    else:
        print(f"摄像头设备 {i} 不可用")

print(f"分辨率: {width} x {height}")
print(f"帧率: {fps}")
