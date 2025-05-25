import asyncio
import websockets
import json
import base64
from datetime import datetime

class WebSocketClient:
    def __init__(self, uri="ws://192.168.0.69:5000"):
        """初始化 WebSocket 客户端"""
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.last_result = None
        self.callback = None

    async def connect(self):
        """连接到 WebSocket 服务器"""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print(f"已连接到服务器: {self.uri}")
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
            # 将图像数据编码为 base64
            frame_base64 = base64.b64encode(frame_data).decode('utf-8')
            
            # 构建消息
            message = {
                "type": "image",
                "data": frame_base64,
                "timestamp": datetime.now().isoformat()
            }
            
            # 发送消息
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            print(f"发送图像失败: {e}")
            self.connected = False
            return False

    async def receive_results(self):
        """接收服务器返回的结果"""
        if not self.connected or not self.websocket:
            return None

        try:
            while True:
                response = await self.websocket.recv()
                result = json.loads(response)
                self.last_result = result
                
                # 如果有回调函数，则调用它
                if self.callback:
                    await self.callback(result)
                
                return result
        except Exception as e:
            print(f"接收结果失败: {e}")
            self.connected = False
            return None

    def set_callback(self, callback):
        """设置结果回调函数"""
        self.callback = callback

    async def close(self):
        """关闭 WebSocket 连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False 