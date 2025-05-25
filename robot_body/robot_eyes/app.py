#!/usr/bin/env python3
import os
import sys
import asyncio
import json
from pathlib import Path
from flask import Flask, render_template, Response
from flask_sock import Sock
import yaml
from camera import Camera
from websocket_client import WebSocketClient
import cv2

app = Flask(__name__)
sock = Sock(app)

# 全局变量
camera = None
ws_client = None
connected_clients = set()

def init_camera():
    """初始化摄像头"""
    global camera
    camera = Camera()

def init_websocket():
    """初始化 WebSocket 客户端"""
    global ws_client
    ws_client = WebSocketClient()

async def process_frame(frame):
    """处理图像帧"""
    if frame is None:
        return None
    
    # 编码图像
    frame_data = camera.encode_frame(frame)
    if frame_data is None:
        return None
    
    # 发送到服务器
    if ws_client and ws_client.connected:
        await ws_client.send_frame(frame_data)
    
    return frame

def generate_frames():
    """生成视频流"""
    while True:
        frame = camera.read_frame()
        if frame is not None:
            # 处理帧
            asyncio.run(process_frame(frame))
            
            # 编码为 JPEG
            ret, buffer = cv2.imencode('.jpg', frame)
            frame = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')

@app.route('/')
def index():
    """主页"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """视频流路由"""
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@sock.route('/ws')
def websocket(ws):
    """WebSocket 连接处理"""
    connected_clients.add(ws)
    try:
        while True:
            # 保持连接活跃
            ws.receive()
    except Exception as e:
        print(f"WebSocket 错误: {e}")
    finally:
        connected_clients.remove(ws)

async def broadcast_result(result):
    """广播识别结果到所有连接的客户端"""
    if result:
        message = json.dumps(result)
        for client in connected_clients:
            try:
                client.send(message)
            except Exception as e:
                print(f"发送结果失败: {e}")

async def main():
    """主函数"""
    # 初始化摄像头
    init_camera()
    
    # 初始化 WebSocket 客户端
    init_websocket()
    
    # 连接到服务器
    if await ws_client.connect():
        print("已连接到服务器")
        
        # 设置回调函数
        ws_client.set_callback(broadcast_result)
        
        # 开始接收结果
        while True:
            await ws_client.receive_results()
            await asyncio.sleep(0.1)

if __name__ == "__main__":
    # 加载配置
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    # 运行主程序
    print("启动视觉模块...")
    app.run(host=config['web']['host'], 
            port=config['web']['port'], 
            debug=config['web']['debug']) 