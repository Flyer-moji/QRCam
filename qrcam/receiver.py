# receiver.py
import json
import cv2
import base64, struct, zlib
from collections import OrderedDict
from config import MISSING_FRAME_PATH, SAVE_FILE_PATH

def decode_qr(frame):
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(frame)
    if data:
        return data
    return None

def parse_payload(payload_b64):
    #解析 QR 数据帧载荷
    try:
        raw = base64.b64decode(payload_b64)
        total = struct.unpack("I", raw[0:4])[0]
        frame_id = struct.unpack("I", raw[4:8])[0]
        crc_recv = struct.unpack("I", raw[-4:])[0]
        data_chunk = raw[8:-4]
        crc_calc = zlib.crc32(raw[:-4])#crc校验
        is_valid = (crc_calc == crc_recv)
        return total, frame_id, data_chunk, is_valid
    except Exception as e:
        print(f"[ERROR] Payload解析异常: {e}")
        return None, None, None, False

def buffer_frame(received_dict, frame_id, data_chunk):
    # 如果没收到过，缓存；如果收到过，保持旧数据（避免覆盖）
    if frame_id not in received_dict:
        received_dict[frame_id] = data_chunk
def update_missing_frames_file(total, received_dict, filename=MISSING_FRAME_PATH):
    if total is None:
        return
    missing = [i for i in range(1, total + 1) if i not in received_dict]#遍历查询缺失帧
    with open(filename, 'w') as f:#写
        json.dump(missing, f, indent=2)
    print(f"\n[INFO] *** 实时更新缺失帧文件，当前缺失帧数: {len(missing)}，写入 {filename}\n")


def reconstruct_file(received_dict):
    file_bytes = b"" #空的字节串
    max_frame_id = max(received_dict.keys())
    for i in range(1, max_frame_id + 1):
        if i in received_dict:
            file_bytes += received_dict[i]
        else:
            print(f"[ERROR] 丢失帧{i}，文件可能不完整")
    return file_bytes

def save_file(filename, file_bytes):
    with open(filename, "wb") as f:
        f.write(file_bytes)
    print(f"[INFO] 文件已保存到 {filename}")

def main():
    cap = cv2.VideoCapture(0)#多摄像头需要查看自己的摄像头编号
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)#分辨率
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)#帧率

    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return

    received_dict = OrderedDict()#创建有序字典，接收到的帧按顺序存入key_i:chunk_i
    total = None  # 初始化总帧数
    print("[INFO] 摄像头已启动，按 's' 保存文件，按 'esc' 退出程序")
    last_write_count = 0  # 记录上次写入文件时的帧缓存数
    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.imshow("QR Receiver", frame)#实时画面

        payload = decode_qr(frame)
        if payload:
            tf, frame_id, data_chunk, valid = parse_payload(payload)#解析
            if valid:
                if total is None:
                    total = tf
                    print(f"[INFO] 识别到总帧数: {total}")
                buffer_frame(received_dict, frame_id, data_chunk)#缓存
                print(f"[INFO] 成功接收帧 {frame_id}，已缓存帧数: {len(received_dict)}/{total}")
                if len(received_dict) - last_write_count >= 50 or len(received_dict) == total:#写丢失帧编号
                    update_missing_frames_file(total, received_dict)
                    last_write_count = len(received_dict)#更新周期设50
            else:
                print("[WARN] CRC校验失败，丢弃此帧")

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            print("[INFO] 保存文件请求收到，开始拼接和保存...")
            file_bytes = reconstruct_file(received_dict)
            save_file("received_output.png", file_bytes)
            # 保存缺失帧文件，确保最新
            if total is not None:
                update_missing_frames_file(total, received_dict)
        elif key == 27:
            print("[INFO] 退出程序")
            break

        # 如果收到所有帧，自动保存并退出
        if total is not None and all(i in received_dict for i in range(1, total + 1)):
            print("[INFO] 所有帧已接收完毕，自动保存文件")
            file_bytes = reconstruct_file(received_dict)#重构
            save_file(SAVE_FILE_PATH, file_bytes)#写文件
            update_missing_frames_file(total, received_dict) #为0，用于清空文件结束程序
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
