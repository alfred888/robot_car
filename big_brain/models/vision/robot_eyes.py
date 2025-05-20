#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import websockets
import json
import sys
import base64
from PIL import Image
import io
import os

async def see_image(image_path, model="fastvlm"):
    """
    发送图片到视觉服务并获取描述
    
    Args:
        image_path: 图片路径
        model: 视觉模型名称（默认为fastvlm）
    
    Returns:
        str: 图片描述
    """
    try:
        # 读取图片
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 连接WebSocket服务
        uri = "ws://localhost:5000/ws"
        async with websockets.connect(uri) as websocket:
            # 发送图片数据
            await websocket.send(image_data)
            
            # 接收描述结果
            response = await websocket.recv()
            result = json.loads(response)
            
            return result['content']
            
    except Exception as e:
        print(f"错误: {str(e)}", file=sys.stderr)
        return None

def main():
    if len(sys.argv) < 2:
        print("用法: python see_client.py <图片路径> [模型名称]")
        sys.exit(1)
    
    image_path = sys.argv[1]
    model = sys.argv[2] if len(sys.argv) > 2 else "fastvlm"
    
    if not os.path.exists(image_path):
        print(f"错误: 图片文件不存在: {image_path}", file=sys.stderr)
        sys.exit(1)
    
    # 运行异步函数
    description = asyncio.run(see_image(image_path, model))
    
    if description:
        print(description)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main() 