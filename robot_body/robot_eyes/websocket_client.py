#!/usr/bin/env python3
import asyncio
import websockets
import json
import yaml
from pathlib import Path

class WebSocketClient:
    def __init__(self):
        """初始化 WebSocket 客户端"""
        self.config = self._load_config()
        self.websocket = None
        self.connected = False
        self.callback = None
        
    def _load_config(self):
        """加载配置文件"""
        config_path = Path(__file__).parent / "config.yaml"
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    async def connect(self):
        """连接到服务器"""
        try:
            self.websocket = await websockets.connect(self.config['websocket']['server_url'])
            self.connected = True
            print("已连接到服务器")
            return True
        except Exception as e:
            print(f"连接服务器失败: {e}")
            self.connected = False
            return False
    
    async def send_frame(self, frame_data):
        """发送图像帧到服务器"""
        if not self.connected or not self.websocket:
            return False
        
        try:
            await self.websocket.send(frame_data)
            return True
        except Exception as e:
            print(f"发送图像失败: {e}")
            self.connected = False
            return False
    
    async def receive_results(self):
        """接收服务器返回的识别结果"""
        if not self.connected or not self.websocket:
            return
        
        try:
            result = await self.websocket.recv()
            if self.callback:
                await self.callback(json.loads(result))
        except Exception as e:
            print(f"接收结果失败: {e}")
            self.connected = False
    
    def set_callback(self, callback):
        """设置结果回调函数"""
        self.callback = callback
    
    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False 