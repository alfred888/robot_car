import cv2
import numpy as np
from picamera2 import Picamera2
import time

class Camera:
    def __init__(self):
        """初始化摄像头"""
        try:
            # 尝试使用 Picamera2（树莓派专用）
            self.picam2 = Picamera2()
            self.picam2.configure(self.picam2.create_preview_configuration(
                main={"format": 'XRGB8888', "size": (640, 480)}))
            self.picam2.start()
            self.use_picamera = True
        except Exception as e:
            print(f"Picamera2 初始化失败: {e}")
            # 如果 Picamera2 失败，使用 OpenCV 摄像头
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.use_picamera = False

    def read_frame(self):
        """读取一帧图像"""
        if self.use_picamera:
            frame = self.picam2.capture_array()
            # 转换颜色空间从 XRGB 到 BGR
            frame = cv2.cvtColor(frame, cv2.COLOR_RGBA2BGR)
        else:
            ret, frame = self.cap.read()
            if not ret:
                return None
        return frame

    def encode_frame(self, frame):
        """将图像编码为 JPEG 格式"""
        if frame is None:
            return None
        _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
        return buffer.tobytes()

    def release(self):
        """释放摄像头资源"""
        if self.use_picamera:
            self.picam2.stop()
        else:
            self.cap.release() 