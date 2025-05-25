#!/usr/bin/env python3
import os
import sys
import cv2
import numpy as np
import yaml
from pathlib import Path

# 检查是否在 macOS 上运行
is_macos = sys.platform == 'darwin'

if is_macos:
    class Camera:
        def __init__(self):
            """初始化摄像头"""
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise RuntimeError("无法打开摄像头")
            print("摄像头初始化成功")
        
        def read_frame(self):
            """读取一帧图像"""
            try:
                ret, frame = self.cap.read()
                if ret:
                    return frame
                return None
            except Exception as e:
                print(f"读取图像失败: {e}")
                return None
        
        def encode_frame(self, frame):
            """将图像编码为 JPEG 格式"""
            try:
                _, buffer = cv2.imencode('.jpg', frame)
                return buffer.tobytes()
            except Exception as e:
                print(f"图像编码失败: {e}")
                return None
        
        def __del__(self):
            """清理资源"""
            if hasattr(self, 'cap'):
                self.cap.release()
else:
    from picamera2 import Picamera2
    
    class Camera:
        def __init__(self):
            """初始化摄像头"""
            self.config = self._load_config()
            self.camera = None
            self._init_camera()
        
        def _load_config(self):
            """加载 YAML 配置"""
            config_path = Path(__file__).parent.parent / "config" / "pi_config.yaml"
            if not config_path.exists():
                print(f"⚠️ 配置文件未找到: {config_path}，使用默认配置")
                return {
                    "hardware": {
                        "camera": {
                            "width": 640,
                            "height": 480,
                            "format": "RGB888"
                        }
                    }
                }
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        def _init_camera(self):
            """初始化摄像头"""
            try:
                self.camera = Picamera2()
                camera_config = self.camera.create_preview_configuration(
                    main={"size": (self.config['camera']['width'], 
                                 self.config['camera']['height']),
                          "format": self.config['camera']['format']}
                )
                self.camera.configure(camera_config)
                self.camera.start()
                print("摄像头初始化成功")
            except Exception as e:
                print(f"摄像头初始化失败: {e}")
                raise
        
        def read_frame(self):
            """读取一帧图像"""
            try:
                frame = self.camera.capture_array()
                return frame
            except Exception as e:
                print(f"读取图像失败: {e}")
                return None
        
        def encode_frame(self, frame):
            """将图像编码为 JPEG 格式"""
            try:
                _, buffer = cv2.imencode('.jpg', frame)
                return buffer.tobytes()
            except Exception as e:
                print(f"图像编码失败: {e}")
                return None
        
        def __del__(self):
            """清理资源"""
            if self.camera:
                self.camera.stop() 