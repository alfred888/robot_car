#!/usr/bin/env python3
import cv2
import numpy as np
from picamera2 import Picamera2
import yaml
from pathlib import Path

class Camera:
    def __init__(self):
        """初始化摄像头"""
        self.config = self._load_config()
        self.camera = None
        self._init_camera()
        
    def _load_config(self):
        """加载配置文件"""
        config_path = Path(__file__).parent / "config.yaml"
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