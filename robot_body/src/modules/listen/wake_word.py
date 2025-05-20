#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
唤醒词监听模块
用于监听麦克风输入，检测唤醒词"乐迪乐迪"
"""

import threading
import queue
import time
import logging
from typing import Optional, Callable, List
import subprocess
import os

import speech_recognition as sr
from gtts import gTTS
import tempfile
import pygame
import sounddevice as sd
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MicrophoneError(Exception):
    """麦克风错误异常类"""
    pass

class WakeWordListener:
    """唤醒词监听器类"""
    
    def __init__(self, wake_word="你好小智", device_id=2):  # 默认使用 card 2 (USB Camera)
        self.wake_word = wake_word
        self.recognizer = sr.Recognizer()
        self.audio_queue = queue.Queue()
        self.is_listening = False
        self.sample_rate = 16000
        self.channels = 1
        self.device_id = device_id
        
        # 打印音频设备信息
        logger.info("可用的音频设备:")
        devices = sd.query_devices()
        for i, device in enumerate(devices):
            if device['max_input_channels'] > 0:  # 只显示输入设备
                logger.info(f"设备 {i}: {device['name']}")
        
    def audio_callback(self, indata, frames, time, status):
        """音频回调函数，将音频数据放入队列"""
        if status:
            logger.warning(f"音频状态: {status}")
        self.audio_queue.put(indata.copy())
        
    def process_audio(self):
        """处理音频数据"""
        while self.is_listening:
            try:
                # 从队列获取音频数据
                audio_data = self.audio_queue.get()
                
                # 将音频数据转换为AudioData对象
                audio = sr.AudioData(
                    audio_data.tobytes(),
                    self.sample_rate,
                    audio_data.dtype.itemsize
                )
                
                # 使用Google语音识别
                try:
                    text = self.recognizer.recognize_google(audio, language='zh-CN')
                    logger.info(f"识别到的文字: {text}")
                    
                    # 检查是否包含唤醒词
                    if self.wake_word in text:
                        logger.info(f"检测到唤醒词: {self.wake_word}")
                        # 这里可以添加唤醒后的操作
                        
                except sr.UnknownValueError:
                    pass  # 无法识别语音
                except sr.RequestError as e:
                    logger.error(f"无法连接到Google语音识别服务: {e}")
                    
            except queue.Empty:
                continue
                
    def start_listening(self):
        """开始监听"""
        self.is_listening = True
        
        # 启动音频处理线程
        process_thread = threading.Thread(target=self.process_audio)
        process_thread.daemon = True
        process_thread.start()
        
        try:
            # 开始录音
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=self.audio_callback,
                device=self.device_id  # 指定麦克风设备
            ):
                logger.info(f"开始监听唤醒词: {self.wake_word}")
                logger.info("按 Ctrl+C 停止监听")
                
                while self.is_listening:
                    time.sleep(0.1)
                    
        except KeyboardInterrupt:
            logger.info("唤醒词监听器已停止")
        finally:
            self.is_listening = False
            
def main():
    # 创建唤醒词监听器，使用 USB Camera 的麦克风 (device_id=2)
    listener = WakeWordListener(device_id=2)
    
    # 开始监听
    listener.start_listening()

if __name__ == "__main__":
    main() 