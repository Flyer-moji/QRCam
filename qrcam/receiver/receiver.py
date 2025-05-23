import cv2
import base64
import struct
import zlib
import math
from collections import OrderedDict

GROUP_SIZE = 4  # 每组数据帧数，发送端对应

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
        is_parity = struct.unpack("B", raw[8:9])[0]  # 1字节校验标志
        data_chunk = raw[9:-4]
        crc_recv = struct.unpack("I", raw[-4:])[0]
        crc_calc = zlib.crc32(raw[:-4])
        is_valid = (crc_calc == crc_recv)
        return total, frame_id, is_parity, data_chunk, is_valid
    except Exception as e:
        print(f"[ERROR] Payload解析异常: {e}")
        return None, None, None, None, False

def buffer_frame(received_groups, frame_id, is_parity, data_chunk):
    group_id = (frame_id - 1) // (GROUP_SIZE + 1)
    frame_pos = (frame_id - 1) % (GROUP_SIZE + 1)  # 0~GROUP_SIZE，最后一个是parity

    if group_id not in received_groups:
        received_groups[group_id] = {}

    if frame_pos not in received_groups[group_id]:
        received_groups[group_id][frame_pos] = data_chunk
        print(f"[INFO] 缓存组{group_id}帧{frame_pos}（{'Parity' if is_parity else 'Data'}）")
    else:
        print(f"[DEBUG] 组{group_id}帧{frame_pos}重复接收，忽略")

def try_group_repair(received_groups):
    repaired_groups = []
    for group_id, group_chunks in list(received_groups.items()):
        expected_len = GROUP_SIZE + 1
        if len(group_chunks) == expected_len:
            continue  # 组完整
        if len(group_chunks) == GROUP_SIZE:
            max_len = max(len(c) for c in group_chunks.values())
            padded = {i: c.ljust(max_len, b'\x00') for i, c in group_chunks.items()}
            xor_sum = bytearray(max_len)
            missing_pos = list(set(range(expected_len)) - set(group_chunks.keys()))[0]
            for i in range(expected_len):
                if i != missing_pos and i in padded:
                    xor_sum = bytes(x ^ y for x, y in zip(xor_sum, padded[i]))
            # 简单验证长度一致后才修复
            if len(xor_sum) == max_len:
                received_groups[group_id][missing_pos] = xor_sum
                repaired_groups.append((group_id, missing_pos))
                print(f"[INFO] 组{group_id}修复成功，补齐帧位置{missing_pos}")
    return repaired_groups

def reconstruct_file(received_groups):
    file_bytes = b""
    # 先按组排序，再按帧序列（跳过parity帧）拼接
    total_groups = len(received_groups)
    for group_id in sorted(received_groups.keys()):
        group = received_groups[group_id]
        for frame_pos in range(GROUP_SIZE):
            if frame_pos in group:
                file_bytes += group[frame_pos]
            else:
                print(f"[ERROR] 组{group_id}缺少帧{frame_pos}，文件可能不完整")
    return file_bytes

def save_file(filename, file_bytes):
    try:
        with open(filename, "wb") as f:
            f.write(file_bytes)
        print(f"[INFO] 文件已保存到 {filename}")
    except Exception as e:
        print(f"[ERROR] 保存文件失败: {e}")

import math

def main():
    cap = cv2.VideoCapture(2)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    cap.set(cv2.CAP_PROP_FPS, 30)

    if not cap.isOpened():
        print("[ERROR] 无法打开摄像头")
        return

    received_groups = {}
    total_frames = None

    print("[INFO] 摄像头启动，按 's' 保存文件，按 'q' 退出程序")

    while True:
        ret, frame = cap.read()
        if not ret:
            continue

        cv2.imshow("QR Receiver", frame)

        payload = decode_qr(frame)
        if payload:
            tf, frame_id, is_parity, data_chunk, valid = parse_payload(payload)
            if valid:
                if total_frames is None:
                    total_frames = tf
                    print(f"[INFO] 识别到总帧数: {total_frames}")
                buffer_frame(received_groups, frame_id, is_parity, data_chunk)
                try_group_repair(received_groups)

                # 统计已接收数据帧数量（不含parity）
                received_data_count = sum(
                    len([p for p in g if p != GROUP_SIZE]) for g in received_groups.values()
                )
                # 计算总数据帧数（总帧数减去所有组的parity帧数）
                total_data_frames = total_frames - (total_frames // (GROUP_SIZE + 1))

                print(f"[INFO] 已接收数据帧数（含修复）: {received_data_count}/{total_data_frames}")

            else:
                print("[WARN] CRC校验失败，丢弃此帧")

        key = cv2.waitKey(1) & 0xFF
        if key == ord('s'):
            print("[INFO] 保存文件请求，开始拼接...")
            file_bytes = reconstruct_file(received_groups)
            save_file("received_output.png", file_bytes)
        elif key == ord('q'):
            print("[INFO] 退出程序")
            break

        # 自动保存判断（改为总数据帧数判断）
        if total_frames:
            total_data_frames = total_frames - (total_frames // (GROUP_SIZE + 1))
            received_data_count = sum(
                len([p for p in g if p != GROUP_SIZE]) for g in received_groups.values()
            )
            if received_data_count >= total_data_frames:
                print("[INFO] 所有数据帧已接收，自动保存文件")
                file_bytes = reconstruct_file(received_groups)
                save_file("received_output.png", file_bytes)
                break

    cap.release()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
