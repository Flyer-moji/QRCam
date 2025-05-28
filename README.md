# QR Code Communication System

## 概述

本项目基于二维码实现单向文件传输，通过将文件切分为若干数据块并生成二维码帧，接收端通过摄像头实时扫描并解码帧内数据，最终重组文件。

## 核心流程：

1. 发送端将文件读取、按固定大小切分，添加帧头（总帧数、帧序号、CRC32校验）并 Base64 编码。

2. 生成二维码图像并按设定帧率播放。

3. 接收端使用 OpenCV 实时检测并解码二维码，缓存有效数据块。

4. 接收端维护 missing_frames.json 文件，记录尚未接收的帧编号。

5. 发送端读取该 JSON，按需重新生成并播放缺失帧进行补传。

## 功能特性

- 文件切分与帧头封装：支持任意二进制文件，切分为固定大小（默认为 220 字节）数据块，帧头包含总帧数和帧编号。

- CRC 校验：每帧末尾加入 CRC32 校验码，接收端校验失败则丢弃该帧。

- 实时重传机制：接收端将丢失帧写入 missing_frames.json，发送端循环读取并补传。

- 动态窗口播放：在全帧播放后进入缺失帧补传循环，支持按键中止、重新播放等交互。

## 依赖环境
```
qrcode==8.2
tqdm==4.67.1
opencv-python==4.11.0.86
numpy==2.2.6
```

## 使用说明

1. **发送端（qr_encoder.py）**

    修改config.py脚本参数：
    ```
    FILE_PATH = "path/to/your/file"
    CHUNK_SIZE = 220        # 每帧数据字节数
    FRAME_RATE = 10          # 帧率
   ··· ···
    ```
    运行脚本：

    `python` qr_encoder.py`

    1. 先按任意键播放完整帧序列，播放完毕后自动进入缺失帧补传模式。

    2. 在播放过程中按 ESC 中止，按 Space 重置完整播放。

2. **接收端（receiver.py）**

    修改或确认 JSON 路径：

    `MISSING_FRAME_PATH = "missing_frames.json"`

    运行脚本：

    `python receiver.py`

    摄像头启动后实时扫描二维码：成功解码后缓存数据并更新 `missing_frames.json`。

    按 s 键立即拼接已接收的数据并保存为 receiver/received_output.png
   ,按 ESC 退出

    当所有帧接收完成后，自动拼接并保存。

## 文件结构
    ```
    qrcam/
    ├── qr_encoder.py       # 发送端脚本，负责切分文件、生成二维码并播放
    ├── config.py           # 配置文件，修改参数
    ├── receiver.py         # 接收端脚本，负责扫码解码、缓存数据和更新缺失帧列表
    └── missing_frames.json # 缺失帧列表，由接收端实时维护
      README.md             # 项目说明文档
      requirements.txt      # 依赖包列表 
      test.py               # 测试摄像头功能脚本
      LICENSE               # 许可证
    ```
## 注意事项
- 非真正的 FEC：当前方案基于重传机制，而非在帧内添加冗余数据进行纠错。

- 单向传输：无 ACK/NAK 网络反馈，仅依赖本地 JSON 文件交换状态。

 - 性能瓶颈：文件 I/O 频繁，可能在高帧率或大文件时导致延迟。

- 环境依赖：二维码解码受光照、摄像头分辨率等因素影响。

## 未来改进方向

- 引入真正的前向纠错（如 Reed–Solomon），提升丢帧恢复能力。

- 用消息队列或网络接口替换 JSON，优化状态同步效率。

- 多线程或异步处理扫码、缓存和 I/O 提升性能。

- 动态调整二维码版本与纠错等级，自适应不同环境。

- 支持多文件批量传输和实时视频流。

## 联系方式

GitHub: Flyer-moji

邮箱: hkivela123@gmail.com

