# send_main.py
# 发送端程序入口
from qr_encoder import generate_qr_frames_with_fec, play_qr_frames


#file_path = input("请输入需要发送的文件路径:（绝对路径） ")
#print(f"[INFO] 路径: {file_path}")

frames = generate_qr_frames_with_fec("D:/1.png", chunk_size=180)
play_qr_frames(frames)