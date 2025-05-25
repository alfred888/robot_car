#!/usr/bin/env python3
import os
import sys
import subprocess
from pathlib import Path

def setup_virtual_env():
    """设置和激活虚拟环境（仅支持 macOS 和 Ubuntu）"""
    # 获取当前脚本所在目录
    current_dir = Path(__file__).parent.absolute()
    
    # 虚拟环境目录
    venv_dir = current_dir / "venv"
    
    try:
        # 检查虚拟环境是否存在
        if not venv_dir.exists():
            print("创建虚拟环境...")
            # 尝试使用 python3.9
            try:
                subprocess.run(["python3.9", "-m", "venv", str(venv_dir)], check=True)
            except subprocess.CalledProcessError:
                print("python3.9 不可用，尝试使用 python3.8...")
                try:
                    subprocess.run(["python3.8", "-m", "venv", str(venv_dir)], check=True)
                except subprocess.CalledProcessError:
                    print("python3.8 不可用，尝试使用 python3...")
                    subprocess.run(["python3", "-m", "venv", str(venv_dir)], check=True)
        
        # 获取虚拟环境中的 Python 解释器路径
        python_path = venv_dir / "bin" / "python"
        
        # 如果当前不在虚拟环境中，则重新启动脚本
        if sys.executable != str(python_path):
            print(f"激活虚拟环境: {venv_dir}")
            # 安装依赖
            try:
                # 先升级 pip
                subprocess.run([str(python_path), "-m", "pip", "install", "--upgrade", "pip"], check=True)
                # 安装依赖
                subprocess.run([str(python_path), "-m", "pip", "install", "-r", "requirements.txt"], check=True)
            except subprocess.CalledProcessError as e:
                print(f"安装依赖失败: {e}")
                print("尝试使用 --no-deps 选项安装...")
                subprocess.run([str(python_path), "-m", "pip", "install", "--no-deps", "-r", "requirements.txt"], check=True)
            
            # 使用虚拟环境的 Python 重新运行脚本
            os.execv(str(python_path), [str(python_path), __file__] + sys.argv[1:])
    except Exception as e:
        print(f"设置虚拟环境时出错: {e}")
        sys.exit(1)

# 在导入其他模块之前设置虚拟环境
setup_virtual_env()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import cv2
import subprocess
import os
from datetime import datetime
import asyncio
import json
import uvicorn
from typing import List, Dict
import threading
import queue
import time
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import RotatingFileHandler
import torch
from transformers import AutoProcessor, AutoModelForVision2Seq
import base64
from io import BytesIO
from PIL import Image
import io
from predict import predict
import argparse
import websockets

app = FastAPI()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 日志配置
LOG_DIR = os.path.expanduser("~/logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "server.log")

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# FastVLM 模型路径
MODEL_PATH = os.path.expanduser("~/models/llava-fastvithd_0.5b_stage3")
PROMPT = "用简短的语言描述图片内容"

# 全局变量
description_queue = queue.Queue()
is_model_loading = True
active_connections: List[WebSocket] = []
model = None
processor = None

# 创建图片保存目录
IMAGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captured_images")
os.makedirs(IMAGE_DIR, exist_ok=True)

def print_progress(message):
    """打印带时间戳的进度信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}")

def save_image(image_data, filepath):
    """保存图片数据到文件"""
    # 将二进制数据转换为numpy数组
    nparr = np.frombuffer(image_data, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 保存图片
    cv2.imwrite(filepath, img)
    
    # 获取文件大小
    file_size = os.path.getsize(filepath) / 1024  # 转换为KB
    print_progress(f"📊 接收到的图片大小: {file_size:.1f}KB")
    
    return img

def describe_image(image_path):
    """调用 FastVLM 模型描述图像内容"""
    global is_model_loading
    
    cmd = [
        "python", "predict.py",
        "--model-path", MODEL_PATH,
        "--image-file", image_path,
        "--prompt", PROMPT
    ]
    
    print_progress(f"🔍 正在描述图片: {image_path}")
    print_progress(f"📝 使用的提示词: {PROMPT}")
    
    if is_model_loading:
        print_progress("⏳ 首次运行，模型正在加载中...")
        is_model_loading = False
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    description = result.stdout.strip()
    error = result.stderr.strip()
    
    if error:
        print_progress(f"❌ 错误信息:")
        print("=" * 50)
        print(error)
        print("=" * 50)
        return f"处理出错: {error}"
    
    if not description:
        print_progress("⚠️ 警告: 模型没有返回任何描述")
        return "模型没有返回任何描述"
    
    print_progress("✨ 描述结果:")
    print("=" * 50)
    print(description)
    print("=" * 50)
    print()
    
    return description

async def process_image(websocket, image_data):
    """处理接收到的图片数据"""
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"received_image_{timestamp}.jpg"
        filepath = os.path.join(IMAGE_DIR, filename)
        
        # 保存图片
        save_image(image_data, filepath)
        print_progress(f"📸 图片已保存到: {filepath}")
        
        # 确保文件存在
        if not os.path.exists(filepath):
            print_progress(f"❌ 图片文件保存失败: {filepath}")
            return
        
        # 在后台线程中运行描述任务
        loop = asyncio.get_event_loop()
        description = await loop.run_in_executor(None, describe_image, filepath)
        
        # 发送描述结果回树莓派
        await websocket.send_json({
            "type": "description",
            "content": description,
            "timestamp": timestamp
        })
        
        # 删除临时文件
        try:
            os.remove(filepath)
            print_progress(f"🗑️ 临时文件已删除: {filepath}")
        except Exception as e:
            print_progress(f"⚠️ 删除临时文件失败: {e}")
            
    except Exception as e:
        print_progress(f"❌ 处理图片时出错: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接处理"""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("🔌 新的WebSocket连接已建立")
    
    try:
        while True:
            # 接收图片数据
            image_data = await websocket.receive_bytes()
            logger.info("📥 收到图片数据")
            
            # 处理图片
            await process_image(websocket, image_data)
            
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info("🔌 WebSocket连接已断开")
    except Exception as e:
        logger.error(f"❌ 处理过程出错: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)

# 挂载静态文件
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def get():
    """返回主页"""
    with open("templates/index.html") as f:
        return f.read()

def load_model():
    """加载模型"""
    global model, processor
    try:
        logger.info("🔄 正在加载模型...")
        model = AutoModelForVision2Seq.from_pretrained("microsoft/git-base-coco")
        processor = AutoProcessor.from_pretrained("microsoft/git-base-coco")
        logger.info("✅ 模型加载完成")
    except Exception as e:
        logger.error(f"❌ 模型加载失败: {e}")
        raise

@app.on_event("startup")
async def startup_event():
    """服务启动时加载模型"""
    load_model()

class ImageDescriptionServer:
    def __init__(self, model_path, host="0.0.0.0", port=5000):
        self.model_path = model_path
        self.host = host
        self.port = port
        logger.info(f"初始化服务器: host={host}, port={port}")
        logger.info(f"模型路径: {model_path}")

    async def handle_client(self, websocket):
        client_id = id(websocket)
        logger.info(f"新客户端连接: {client_id}")
        try:
            async for message in websocket:
                try:
                    if isinstance(message, bytes):
                        # 记录接收到的二进制数据大小
                        logger.info(f"收到二进制图片数据，大小: {len(message)} bytes")
                        
                        # 直接处理二进制图片数据
                        image_data = message
                        temp_path = f"temp_{client_id}.jpg"
                        with open(temp_path, "wb") as f:
                            f.write(image_data)
                        logger.info(f"保存临时图片: {temp_path}")

                        # 验证图片文件是否有效
                        try:
                            with Image.open(temp_path) as img:
                                logger.info(f"图片尺寸: {img.size}, 模式: {img.mode}")
                        except Exception as e:
                            logger.error(f"图片文件无效: {str(e)}")
                            continue

                        # 准备推理参数
                        args = argparse.Namespace(
                            model_path=self.model_path,
                            model_base="llava",
                            image_file=temp_path,
                            prompt="Describe the image.",
                            conv_mode="qwen_2",
                            temperature=0.2,
                            top_p=None,
                            num_beams=1
                        )

                        # 执行推理
                        logger.info(f"开始推理: client_id={client_id}")
                        try:
                            description = predict(args)
                            logger.info(f"推理完成: {description}")

                            # 发送结果
                            response = {
                                "type": "description",
                                "content": description
                            }
                            await websocket.send(json.dumps(response))
                            logger.info(f"已发送结果到客户端 {client_id}")
                        except Exception as e:
                            logger.error(f"推理过程出错: {str(e)}")
                            await websocket.send(json.dumps({
                                "type": "error",
                                "content": f"推理失败: {str(e)}"
                            }))

                        # 清理临时文件
                        try:
                            os.remove(temp_path)
                            logger.info(f"已删除临时文件: {temp_path}")
                        except Exception as e:
                            logger.error(f"删除临时文件失败: {str(e)}")
                    else:
                        logger.error(f"收到非二进制消息，已忽略。消息类型: {type(message)}")
                except Exception as e:
                    logger.error(f"处理客户端 {client_id} 消息时出错: {str(e)}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "content": str(e)
                    }))

        except websockets.exceptions.ConnectionClosed:
            logger.info(f"客户端 {client_id} 断开连接")
        except Exception as e:
            logger.error(f"处理客户端 {client_id} 连接时出错: {str(e)}")

    async def start(self):
        server = await websockets.serve(
            self.handle_client,
            self.host,
            self.port
        )
        logger.info(f"服务器启动成功: ws://{self.host}:{self.port}")
        await server.wait_closed()

if __name__ == "__main__":
    # 设置参数
    parser = argparse.ArgumentParser()
    parser.add_argument("--model-path", type=str, default="./checkpoints/fastvlm_0.5b_stage3")
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5000)
    args = parser.parse_args()

    # 创建并启动服务器
    server = ImageDescriptionServer(args.model_path, args.host, args.port)
    asyncio.run(server.start()) 