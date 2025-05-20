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
    
    def __init__(self, 
                 wake_word: str = "乐迪乐迪",
                 response: str = "我在",
                 language: str = "zh-CN",
                 energy_threshold: int = 300,
                 pause_threshold: float = 0.8):
        """
        初始化唤醒词监听器
        
        Args:
            wake_word: 唤醒词
            response: 唤醒后的响应语
            language: 语音识别语言
            energy_threshold: 语音能量阈值
            pause_threshold: 语音停顿阈值
        """
        self.wake_word = wake_word
        self.response = response
        self.language = language
        self.energy_threshold = energy_threshold
        self.pause_threshold = pause_threshold
        
        # 检查麦克风
        self._check_microphone()
        
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = energy_threshold
        self.recognizer.pause_threshold = pause_threshold
        
        self.is_listening = False
        self.audio_queue = queue.Queue()
        self.callback: Optional[Callable] = None
        
        # 初始化pygame用于播放音频
        pygame.mixer.init()
    
    def _check_microphone(self) -> None:
        """
        检查麦克风是否正常工作
        
        Raises:
            MicrophoneError: 当麦克风不可用或工作不正常时抛出
        """
        try:
            # 检查系统是否识别到麦克风设备
            result = subprocess.run(['arecord', '-l'], 
                                 capture_output=True, 
                                 text=True)
            if 'card' not in result.stdout:
                raise MicrophoneError("未检测到麦克风设备")
            
            # 测试麦克风录音
            test_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            test_file.close()
            
            try:
                # 尝试录制1秒的音频
                subprocess.run(['arecord', '-d', '1', '-f', 'cd', test_file.name],
                             capture_output=True,
                             check=True)
                
                # 检查录音文件大小
                if os.path.getsize(test_file.name) == 0:
                    raise MicrophoneError("麦克风录音测试失败")
                
                logger.info("麦克风检测正常")
            finally:
                # 清理测试文件
                os.unlink(test_file.name)
                
        except subprocess.CalledProcessError as e:
            raise MicrophoneError(f"麦克风测试失败: {str(e)}")
        except Exception as e:
            raise MicrophoneError(f"麦克风检查出错: {str(e)}")
    
    def _get_available_microphones(self) -> List[str]:
        """
        获取可用的麦克风设备列表
        
        Returns:
            List[str]: 可用麦克风设备列表
        """
        try:
            result = subprocess.run(['arecord', '-l'], 
                                 capture_output=True, 
                                 text=True)
            devices = []
            for line in result.stdout.split('\n'):
                if 'card' in line:
                    devices.append(line.strip())
            return devices
        except Exception as e:
            logger.error(f"获取麦克风设备列表失败: {str(e)}")
            return []
        
    def _play_response(self):
        """播放响应语音"""
        try:
            # 使用gTTS生成语音文件
            tts = gTTS(text=self.response, lang=self.language)
            
            # 创建临时文件
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                temp_filename = fp.name
            
            # 保存语音文件
            tts.save(temp_filename)
            
            # 播放语音
            pygame.mixer.music.load(temp_filename)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(10)
            
            # 删除临时文件
            os.unlink(temp_filename)
            
        except Exception as e:
            logger.error(f"播放响应语音时出错: {str(e)}")
    
    def _listen_loop(self):
        """监听循环"""
        try:
            with sr.Microphone() as source:
                logger.info("正在调整环境噪声...")
                self.recognizer.adjust_for_ambient_noise(source)
                logger.info("开始监听唤醒词...")
                
                while self.is_listening:
                    try:
                        audio = self.recognizer.listen(source)
                        self.audio_queue.put(audio)
                    except Exception as e:
                        logger.error(f"监听时出错: {str(e)}")
                        # 如果出现错误，等待一段时间后重试
                        time.sleep(1)
                        continue
        except Exception as e:
            logger.error(f"麦克风初始化失败: {str(e)}")
            self.is_listening = False
    
    def _process_audio(self):
        """处理音频数据"""
        while self.is_listening:
            try:
                audio = self.audio_queue.get(timeout=1)
                try:
                    text = self.recognizer.recognize_google(
                        audio, 
                        language=self.language
                    )
                    logger.info(f"识别到: {text}")
                    
                    if self.wake_word in text:
                        logger.info("检测到唤醒词!")
                        self._play_response()
                        if self.callback:
                            self.callback()
                            
                except sr.UnknownValueError:
                    pass
                except sr.RequestError as e:
                    logger.error(f"无法从Google Speech Recognition服务获取结果: {str(e)}")
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"处理音频时出错: {str(e)}")
                continue
    
    def start(self, callback: Optional[Callable] = None):
        """
        启动监听
        
        Args:
            callback: 检测到唤醒词后的回调函数
        """
        if self.is_listening:
            logger.warning("监听器已经在运行")
            return
            
        self.is_listening = True
        self.callback = callback
        
        # 启动监听线程
        self.listen_thread = threading.Thread(target=self._listen_loop)
        self.listen_thread.daemon = True
        self.listen_thread.start()
        
        # 启动处理线程
        self.process_thread = threading.Thread(target=self._process_audio)
        self.process_thread.daemon = True
        self.process_thread.start()
        
        logger.info("唤醒词监听器已启动")
    
    def stop(self):
        """停止监听"""
        if not self.is_listening:
            return
            
        self.is_listening = False
        if hasattr(self, 'listen_thread'):
            self.listen_thread.join(timeout=1)
        if hasattr(self, 'process_thread'):
            self.process_thread.join(timeout=1)
            
        logger.info("唤醒词监听器已停止")

def main():
    """主函数"""
    try:
        # 显示可用的麦克风设备
        listener = WakeWordListener()
        devices = listener._get_available_microphones()
        if devices:
            print("可用的麦克风设备:")
            for device in devices:
                print(f"  - {device}")
        else:
            print("未检测到可用的麦克风设备")
            return
        
        def on_wake():
            print("机器人被唤醒!")
        
        listener.start(callback=on_wake)
        print("按Ctrl+C停止监听...")
        while True:
            time.sleep(1)
    except MicrophoneError as e:
        print(f"错误: {str(e)}")
    except KeyboardInterrupt:
        listener.stop()
        print("\n监听已停止")
    except Exception as e:
        print(f"发生错误: {str(e)}")

if __name__ == "__main__":
    main() 