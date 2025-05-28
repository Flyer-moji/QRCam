# qr_encoder.py
import base64, struct, qrcode
import numpy as np
import cv2
from tqdm import tqdm
import zlib
import json
import time


def load_missing_frames(path="missing_frames.json"):
    try:
        with open(path, "r") as f:
            missing = json.load(f)  # 直接解析JSON数组
        print(f"[INFO] 加载缺失帧列表: {missing}")
        return sorted(set(missing))
    except Exception as e:
        print(f"[WARN] 无法加载缺失帧列表: {e}")
        return []

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
    img_cv = np.array(img)
    img_cv = cv2.cvtColor(img_cv, cv2.COLOR_RGB2BGR)
    return img_cv.copy()

def generate_qr_frames(file_path, chunk_size, selected_indices=None):
    chunks = read_file_to_chunks(file_path, chunk_size)
    total = len(chunks)
    frames = []

    if selected_indices is None:
        selected_indices = range(1, total + 1)

    for i in tqdm(selected_indices, desc="生成缺失帧二维码"):
        if 1 <= i <= total:
            frames.append(encode_chunk_to_qr(chunks[i - 1], i, total))
        else:
            print(f"[WARN] 无效帧编号: {i}")
    return frames

def resize_frame(frame, scale):
    h, w = frame.shape[:2]
    scale = max(min(scale, 1.0), 0.05)
    return cv2.resize(frame, (int(w * scale), int(h * scale)))

def play_full_then_missing(full_frames, chunks, missing_frame_path, fps=12):
    window_name = "QR Video"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)

    # 获取屏幕分辨率（优先tkinter）
    screen_w, screen_h = 1920, 1080
    try:
        import tkinter as tk
        root = tk.Tk()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        root.destroy()
    except:
        print("[WARN] 无法动态获取屏幕分辨率，使用默认1920x1080")

    frame_h, frame_w = full_frames[0].shape[:2]
    scale_w = (screen_w * 0.9) / frame_w
    scale_h = (screen_h * 0.9) / frame_h
    scale = min(scale_w, scale_h, 1.0)

    delay = int(1000 / fps)

    # Step 1: 播放完整帧
    first_frame = resize_frame(full_frames[0].copy(), scale)
    cv2.putText(first_frame, "Press any key to start full playback", (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
    cv2.imshow(window_name, first_frame)
    print("[INFO] 等待按键开始播放完整帧...")
    key = cv2.waitKey(0) & 0xFF
    if key == 27:  # ESC退出
        print("[INFO] 用户中止")
        cv2.destroyAllWindows()
        return

    print("[INFO] 播放完整帧中...")
    i = 0
    while i < len(full_frames):
        frame = full_frames[i]
        annotated = frame.copy()
        cv2.putText(annotated, f"Frame #{i + 1}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        resized = resize_frame(annotated, scale)
        cv2.imshow(window_name, resized)
        key = cv2.waitKey(delay) & 0xFF
        if key == 27:
            print("[INFO] 用户中止")
            cv2.destroyAllWindows()
            return
        elif key == 32:
            print("[INFO] 重置播放完整帧")
            i = 0
            continue
        else:
            i += 1

    # Step 2: 播放缺失帧（循环扫描json实时加载）
    print("[INFO] 完整帧播放结束，开始实时播放缺失帧")
    total = len(chunks)
    while load_missing_frames("missing_frames.json"):
        missing_indices = load_missing_frames("missing_frames.json")
        print(f"[INFO] 加载到 {len(missing_indices)} 个缺失帧")
        if not missing_indices:
            print("[INFO] 当前无缺失帧，等待更新...")
            time.sleep(1)
            continue

        print(f"[INFO] 播放缺失帧：{missing_indices}")
        for idx in missing_indices:
            if 1 <= idx <= total:
                frame = encode_chunk_to_qr(chunks[idx - 1], idx, total)
                cv2.putText(frame, f"Missing Frame #{idx}", (10, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
                resized = resize_frame(frame, scale)
                cv2.imshow(window_name, resized)
                key = cv2.waitKey(150) & 0xFF
                if key == 27:
                    print("[INFO] 用户中止")
                    cv2.destroyAllWindows()
                    return
            else:
                print(f"[WARN] 跳过无效帧 {idx}")
        time.sleep(0.1)

if __name__ == '__main__':

    FILE_PATH = "D:/1.png"
    MISSING_FRAME_PATH = "missing_frames.json"
    CHUNK_SIZE = 220
    FPS = 13


    full_frames = generate_qr_frames(FILE_PATH, CHUNK_SIZE)
    chunks = read_file_to_chunks(FILE_PATH, CHUNK_SIZE)
    play_full_then_missing(full_frames, chunks, MISSING_FRAME_PATH, fps=FPS)
