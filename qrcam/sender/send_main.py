import base64, struct, qrcode
import numpy as np
from PIL import Image, ImageDraw
import cv2

def read_file_to_chunks(filename, chunk_size=72):  #文件读取，切片
    with open(filename, 'rb') as f:
        data = f.read()
    chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]
    print(f"[INFO] 文件大小: {len(data)} 字节, 被切分为 {len(chunks)} 块")
    return chunks

def encode_chunk_to_qr(chunk, index):
    # 帧头 = 4字节帧号（uint32）+ 数据内容（Base64）
    header = struct.pack("I", index)
    payload = base64.b64encode(header + chunk)

    qr = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q)
    #设置纠错级别为 Q（25%纠错）
    qr.add_data(payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    return np.array(img)[:, :, ::-1]
    # PIL → OpenCV BGR PIL默认是RGB，OpenCV默认是BGR，这里用 [:, :, ::-1] 反转通道顺序，方便用 OpenCV 处理

def generate_qr_frames(file_path, chunk_size=72):
    chunks = read_file_to_chunks(file_path, chunk_size)
    frames = [encode_chunk_to_qr(chunk, i + 1) for i, chunk in enumerate(chunks)]
    return frames

if __name__ == '__main__':

    img = Image.new('RGB', (200, 200), color='white')
    draw = ImageDraw.Draw(img)
    draw.ellipse((50, 50, 150, 150), fill='black')
    img.save('test_image.png')

    frames = generate_qr_frames("test_image.png", chunk_size=72)

    for i, frame in enumerate(frames):
        cv2.imshow(f"QR Frame {i + 1}", frame)
        cv2.waitKey(0)  # 按任意键看下一张
    cv2.destroyAllWindows()