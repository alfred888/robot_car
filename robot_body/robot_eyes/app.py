#!/usr/bin/env python3
import os
import sys
import asyncio
import threading
from flask import Flask, render_template, Response
from flask_sock import Sock
from camera import Camera
from websocket_client import WebSocketClient
import cv2

app = Flask(__name__)
sock = Sock(app)

# 全局变量
camera = None
ws_client = None


def init_camera():
    """初始化摄像头"""
    global camera
    try:
        camera = Camera()
        print("摄像头初始化成功")
    except Exception as e:
        print(f"摄像头初始化失败: {e}")
        sys.exit(1)


async def init_websocket():
    """初始化 WebSocket 客户端"""
    global ws_client
    ws_client = WebSocketClient()
    await ws_client.connect()


async def process_frame():
    """持续读取摄像头帧并通过 WebSocket 发送,每8秒发送一次"""
    while True:
        if camera:
            frame = camera.read_frame()
            if frame is not None:
                frame_data = camera.encode_frame(frame)
                if frame_data:
                    await ws_client.send_frame(frame_data)
        await asyncio.sleep(8)  # 每8秒发送一次


def start_async_loop():
    """在后台线程中运行异步事件循环"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(init_websocket())
    loop.run_until_complete(process_frame())


def generate_frames():
    """生成视频流（用于浏览器查看）"""
    global camera
    while True:
        try:
            frame = camera.read_frame()
            if frame is not None:
                ret, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (
                    b'--frame\r\n'
                    b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
                )
        except Exception as e:
            print(f"生成视频帧时出错: {e}")
            continue


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


if __name__ == "__main__":
    init_camera()
    threading.Thread(target=start_async_loop, daemon=True).start()
    app.run(host='0.0.0.0', port=80)