import cv2
cap = cv2.VideoCapture(1)

# 分辨率
width  = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)

# 帧率
fps = cap.get(cv2.CAP_PROP_FPS)

print(f"分辨率: {width} x {height}")
print(f"帧率: {fps}")
