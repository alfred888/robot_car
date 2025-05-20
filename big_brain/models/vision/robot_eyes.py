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

def load_model_config(model_name):
    """
    加载模型配置
    
    Args:
        model_name: 模型名称
    
    Returns:
        dict: 模型配置
    """
    config_path = os.path.join(os.path.dirname(__file__), 'vision_models_config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        if model_name not in config['models']:
            print(f"错误: 未找到模型配置: {model_name}", file=sys.stderr)
            sys.exit(1)
            
        return config['models'][model_name]
    except Exception as e:
        print(f"错误: 加载配置文件失败: {str(e)}", file=sys.stderr)
        sys.exit(1)

def get_websocket_url(model_config):
    """
    获取WebSocket URL
    
    Args:
        model_config: 模型配置
    
    Returns:
        str: WebSocket URL
    """
    ws_config = model_config['websocket']
    return f"ws://{ws_config['host']}:{ws_config['port']}{ws_config['path']}"

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
        # 加载模型配置
        model_config = load_model_config(model)
        
        # 读取图片
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 获取WebSocket URL
        uri = get_websocket_url(model_config)
        
        # 连接WebSocket服务
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
        print("用法: python robot_eyes.py <图片路径> [模型名称]")
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