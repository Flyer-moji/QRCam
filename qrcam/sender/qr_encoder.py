#qr_encoder.py
import base64, struct, qrcode
import numpy as np
from PIL import Image, ImageDraw
import cv2
from tqdm import tqdm
import zlib

def xor_chunks(chunks):
    from functools import reduce
    from operator import xor
    max_len = max(len(c) for c in chunks)
    padded = [c.ljust(max_len, b'\x00') for c in chunks]
    parity = bytearray(max_len)
    for b in zip(*padded):
        parity = bytes(x ^ y for x, y in zip(parity, b))
    return parity

def read_file_to_chunks(filename, chunk_size):
    with open(filename, 'rb') as f:
        data = f.read()
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    print(f"[INFO] 文件大小: {len(data)} 字节, 被切分为 {len(chunks)} 块")
    return chunks

def encode_chunk_to_qr(chunk, index, total):
    header = struct.pack("II", total, index)
    data = header + chunk
    crc = struct.pack("I", zlib.crc32(data))
    payload = base64.b64encode(data + crc)

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_L)
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    return np.array(img)[:, :, ::-1]

def generate_qr_frames_with_fec(file_path, chunk_size, group_size=4):
    chunks = read_file_to_chunks(file_path, chunk_size)
    frames = []
    total = len(chunks)
    group_id = 0

    for i in range(0, total, group_size):
        group = chunks[i:i + group_size]
        parity = xor_chunks(group)
        all_chunks = group + [parity]
        for j, chunk in enumerate(all_chunks):
            index = i + j + 1
            payload = encode_chunk_to_qr(chunk, index, total + total // group_size)
            frames.append(payload)
        group_id += 1

    return frames

def resize_frame(frame, scale):
    h, w = frame.shape[:2]
    scale = max(min(scale, 1.0), 0.05)
    return cv2.resize(frame, (int(w * scale), int(h * scale)))

def get_screen_size():
    # 这里使用 OpenCV 获取主屏幕分辨率
    # 注意：有些系统可能需要用其他库比如tkinter或pygetwindow获取多显示器支持
    screen_w = 1920
    screen_h = 1080
    try:
        # OpenCV 4.5+ 可以用下面方法：
        screen_w = int(cv2.getWindowImageRect("")[2])
        screen_h = int(cv2.getWindowImageRect("")[3])
    except:
        pass
    return screen_w, screen_h

def play_qr_frames(frames, fps=8):
    if not frames:
        print("[ERROR] 没有可播放的帧")
        return

    window_name = "QR Video"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    screen_w = 1920
    screen_h = 1080
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        root.destroy()
    except:
        print("[WARN] 无法动态获取屏幕分辨率，使用默认1920x1080")

    frame_h, frame_w = frames[0].shape[:2]

    scale_w = (screen_w * 0.9) / frame_w
    scale_h = (screen_h * 0.9) / frame_h
    scale = min(scale_w, scale_h, 1.0)

    print(f"[INFO] 屏幕分辨率：{screen_w}x{screen_h}，二维码原始大小：{frame_w}x{frame_h}")
    print(f"[INFO] 自动计算缩放比例为：{scale:.3f}")

    delay = int(1000 / fps)

    first_frame = resize_frame(frames[0].copy(), scale)
    cv2.putText(first_frame, "Press any key to start playback", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imshow(window_name, first_frame)

    print("[INFO] 等待按键开始播放...")
    cv2.waitKey(0)

    print(f"[INFO] 播放中，帧率: {fps}，按 空格 键重置，按 ESC 键退出...")

    while True:
        i = 0
        while i < len(frames):
            frame = frames[i]
            annotated = frame.copy()
            cv2.putText(annotated, f"Frame #{i + 1}", (10, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
            resized = resize_frame(annotated, scale)
            cv2.imshow(window_name, resized)

            key = cv2.waitKey(delay) & 0xFF
            if key == 27:  # ESC退出
                cv2.destroyAllWindows()
                return
            elif key == 32:  # 空格键重置
                print("[INFO] 重置播放，从头开始")
                i = 0
                continue  # 跳过 i += 1，直接显示第0帧
            else:
                i += 1


if __name__ == '__main__':
    img = Image.new('RGB', (200, 200), color='white')
    draw = ImageDraw.Draw(img)
    draw.ellipse((50, 50, 150, 150), fill='black')
    img.save('test_image.png')

    frames = generate_qr_frames("test_image.png", chunk_size=72)

    play_qr_frames(frames)
