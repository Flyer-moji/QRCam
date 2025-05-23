# receiver.py
import cv2
import base64, struct, zlib
from collections import OrderedDict

def try_xor_repair(group_chunks, group_size):
    if len(group_chunks) == group_size:  # 全部接收，不需修复
        return group_chunks
    if len(group_chunks) == group_size - 1:  # 缺1帧，可尝试修复
        max_len = max(len(c) for c in group_chunks.values())
        padded = {i: c.ljust(max_len, b'\x00') for i, c in group_chunks.items()}
        xor_sum = bytearray(max_len)
        missing_id = list(set(range(group_size)) - set(group_chunks.keys()))[0]
        for i in range(group_size):
            if i != missing_id and i in padded:
                xor_sum = bytes(x ^ y for x, y in zip(xor_sum, padded[i]))
        group_chunks[missing_id] = xor_sum
        return group_chunks
    return None  # 丢失过多，无法修复

def decode_qr(frame):
    detector = cv2.QRCodeDetector()
    data, points, _ = detector.detectAndDecode(frame)
    if data:
        return data
    return None

def parse_payload(payload_b64):
    try:
        raw = base64.b64decode(payload_b64)
        total = struct.unpack("I", raw[0:4])[0]
        frame_id = struct.unpack("I", raw[4:8])[0]
        crc_recv = struct.unpack("I", raw[-4:])[0]
        data_chunk = raw[8:-4]
        crc_calc = zlib.crc32(raw[:-4])
        is_valid = (crc_calc == crc_recv)
        return total, frame_id, data_chunk, is_valid
    except Exception as e:
        print(f"[ERROR] Payload解析异常: {e}")
        return None, None, None, False

def buffer_frame(received_dict, frame_id, data_chunk):
    # 如果没收到过，缓存；如果收到过，保持旧数据（避免覆盖）
    if frame_id not in received_dict:
        received_dict[frame_id] = data_chunk

def reconstruct_file(received_dict):
    file_bytes = b""
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
    cap = cv2.VideoCapture(2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return

    received_dict = OrderedDict()
    total = None  # 初始化总帧数
    print("[INFO] 摄像头已启动，按 's' 保存文件，按 'q' 退出程序")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.imshow("QR Receiver", frame)

        payload = decode_qr(frame)
        if payload:
            tf, frame_id, data_chunk, valid = parse_payload(payload)
            if valid:
                if total is None:
                    total = tf
                    print(f"[INFO] 识别到总帧数: {total}")
                buffer_frame(received_dict, frame_id, data_chunk)
                print(f"[INFO] 成功接收帧 {frame_id}，已缓存帧数: {len(received_dict)}/{total}")
            else:
                print("[WARN] CRC校验失败，丢弃此帧")

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            print("[INFO] 保存文件请求收到，开始拼接和保存...")
            file_bytes = reconstruct_file(received_dict)
            save_file("received_output.png", file_bytes)
        elif key == ord('q'):
            print("[INFO] 退出程序")
            break

        # 如果收到所有帧，自动保存并退出（可选）
        if total is not None and all(i in received_dict for i in range(1, total + 1)):
            print("[INFO] 所有帧已接收完毕，自动保存文件")
            file_bytes = reconstruct_file(received_dict)
            save_file("received_output.png", file_bytes)
            break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
