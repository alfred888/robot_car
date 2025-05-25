import asyncio
import websockets
import json
import logging
import yaml
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WebSocketClient:
    def __init__(self):
        self.config = self._load_config()

        self.server_url = self.config["websocket"]["server_url"]
        self.reconnect_interval = self.config["websocket"].get("reconnect_interval", 5)
        self.ping_interval = self.config["websocket"].get("ping_interval", 30)

        self.websocket = None
        self.connected = False
        self.callback = None
        self.max_retries = 5

    def _load_config(self):
        """加载配置文件"""
        config_path = Path(__file__).parent.parent / "config" / "pi_config.yaml"
        if config_path.exists():
            logger.info(f"加载配置文件: {config_path}")
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        else:
            logger.error("❌ 未找到配置文件")
            raise FileNotFoundError("配置文件不存在: pi_config.yaml")


    async def connect(self):
        """连接到 WebSocket 服务器"""
        try:
            self.websocket = await websockets.connect(self.server_url, ping_interval=self.ping_interval)
            self.connected = True
            logger.info(f"✅ 成功连接到服务器: {self.server_url}")
            return True
        except Exception as e:
            logger.error(f"❌ 无法连接到服务器: {e}")
            self.connected = False
            return False

    async def send_frame(self, frame_data):
        """发送图像帧到服务器"""
        if not self.connected or not self.websocket:
            success = await self.connect()
            if not success:
                logger.error("⚠️ 发送失败：未连接到服务器")
                return False

        try:
            await self.websocket.send(frame_data)
            logger.info("📤 图像帧已发送")
            return True
        except Exception as e:
            logger.error(f"❌ 发送图像帧失败: {e}")
            self.connected = False
            await self.reconnect()
            return False

    async def receive_result(self):
        """接收服务器返回的识别结果"""
        if not self.connected or not self.websocket:
            success = await self.connect()
            if not success:
                return None

        try:
            result = await self.websocket.recv()
            logger.info(f"📥 收到返回结果: {result}")
            if self.callback:
                await self.callback(json.loads(result))
            return json.loads(result)
        except Exception as e:
            logger.error(f"❌ 接收结果失败: {e}")
            self.connected = False
            await self.reconnect()
            return None

    def set_callback(self, callback):
        """设置回调函数处理识别结果"""
        self.callback = callback

    async def reconnect(self):
        """尝试自动重连"""
        for attempt in range(self.max_retries):
            logger.info(f"🔄 第 {attempt + 1} 次尝试重新连接...")
            await asyncio.sleep(self.reconnect_interval)
            if await self.connect():
                return True
        logger.error("❌ 超过最大重连次数，连接失败")
        return False

    async def close(self):
        """关闭连接"""
        if self.websocket:
            await self.websocket.close()
            self.connected = False
            logger.info("🔌 WebSocket 连接已关闭")


# 可选：测试主函数
async def main():
    client = WebSocketClient()
    await client.connect()
    await client.send_frame(b"test_frame_data")

if __name__ == "__main__":
    asyncio.run(main())