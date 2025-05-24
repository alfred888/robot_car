from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import uvicorn
import os
import json
import base64
from PIL import Image
import io
import numpy as np
import cv2

app = FastAPI()

# 获取当前文件所在目录的绝对路径
current_dir = os.path.dirname(os.path.abspath(__file__))
templates_dir = current_dir  # 现在模板文件在同一目录下
static_dir = os.path.join(current_dir, "static")  # 静态文件目录

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/", response_class=HTMLResponse)
async def get():
    """返回测试页面"""
    with open(os.path.join(templates_dir, "test_eyes.html")) as f:
        return f.read()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """处理 WebSocket 连接"""
    await websocket.accept()
    try:
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message["type"] == "image":
                # 解码 base64 图片数据
                image_data = base64.b64decode(message["data"].split(",")[1])
                image = Image.open(io.BytesIO(image_data))
                
                # 转换为 OpenCV 格式
                image_cv = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
                
                # TODO: 这里添加实际的图像识别逻辑
                # 目前返回一个示例描述
                description = "这是一张图片，包含了一些内容。"
                
                # 发送结果
                await websocket.send_json({
                    "description": description
                })
    except Exception as e:
        print(f"WebSocket 错误: {e}")
    finally:
        await websocket.close()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080) 