#!/usr/bin/env python3
"""
双向语音聊天服务 - 支持远程APP与机器人进行实时语音对话
包含语音识别、语音合成和音频流传输功能
"""

import asyncio
import json
import logging
import threading
import time
import wave
import io
import base64
from typing import Dict, Optional
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
import sounddevice as sd
import numpy as np
import speech_recognition as sr
import pyttsx3
from pydub import AudioSegment
from pydub.playback import play
import queue


logger = logging.getLogger('audio_chat')


class AudioBuffer:
    """音频缓冲区类"""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1):
        self.sample_rate = sample_rate
        self.channels = channels
        self.buffer = queue.Queue()
        self.is_recording = False
        
    def add_audio_data(self, data: np.ndarray):
        """添加音频数据到缓冲区"""
        if self.is_recording:
            self.buffer.put(data.copy())
    
    def get_audio_data(self) -> Optional[np.ndarray]:
        """从缓冲区获取音频数据"""
        try:
            return self.buffer.get_nowait()
        except queue.Empty:
            return None
    
    def clear_buffer(self):
        """清空缓冲区"""
        while not self.buffer.empty():
            try:
                self.buffer.get_nowait()
            except queue.Empty:
                break
    
    def start_recording(self):
        """开始录音"""
        self.is_recording = True
        self.clear_buffer()
    
    def stop_recording(self):
        """停止录音"""
        self.is_recording = False


class SpeechProcessor:
    """语音处理器 - 处理语音识别和合成"""
    
    def __init__(self):
        # 语音识别器
        self.recognizer = sr.Recognizer()
        self.recognizer.energy_threshold = 300
        self.recognizer.dynamic_energy_threshold = True
        
        # 语音合成器
        self.tts_engine = pyttsx3.init()
        self.tts_engine.setProperty('rate', 180)
        self.tts_engine.setProperty('volume', 0.9)
        
        # 设置中文语音（如果可用）
        voices = self.tts_engine.getProperty('voices')
        for voice in voices:
            if 'chinese' in voice.name.lower() or 'zh' in voice.id.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
        
        logger.info("语音处理器初始化完成")
    
    def recognize_speech(self, audio_data: np.ndarray, sample_rate: int = 16000) -> Optional[str]:
        """识别语音"""
        try:
            # 将numpy数组转换为AudioData格式
            audio_bytes = (audio_data * 32767).astype(np.int16).tobytes()
            audio_data_sr = sr.AudioData(audio_bytes, sample_rate, 2)
            
            # 使用Google语音识别（中文）
            text = self.recognizer.recognize_google(audio_data_sr, language='zh-CN')
            logger.info(f"识别到语音: {text}")
            return text
            
        except sr.UnknownValueError:
            logger.debug("无法识别语音")
            return None
        except sr.RequestError as e:
            logger.error(f"语音识别服务错误: {e}")
            return None
        except Exception as e:
            logger.error(f"语音识别错误: {e}")
            return None
    
    def synthesize_speech(self, text: str) -> Optional[bytes]:
        """合成语音"""
        try:
            # 创建临时文件存储音频
            temp_file = io.BytesIO()
            
            # 使用pyttsx3生成语音
            self.tts_engine.save_to_file(text, 'temp_speech.wav')
            self.tts_engine.runAndWait()
            
            # 读取生成的音频文件
            with open('temp_speech.wav', 'rb') as f:
                audio_data = f.read()
            
            logger.info(f"合成语音: {text}")
            return audio_data
            
        except Exception as e:
            logger.error(f"语音合成错误: {e}")
            return None
    
    def speak_text(self, text: str):
        """直接播放文本语音"""
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
        except Exception as e:
            logger.error(f"语音播放错误: {e}")


class AudioChatService:
    """双向语音聊天服务类"""
    
    def __init__(self, port: int = 8002):
        self.port = port
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # 音频配置
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        
        # 音频缓冲区
        self.audio_buffer = AudioBuffer(self.sample_rate, self.channels)
        
        # 语音处理器
        self.speech_processor = SpeechProcessor()
        
        # 连接管理
        self.active_clients: Dict[str, dict] = {}
        
        # 音频流状态
        self.is_streaming = False
        self.audio_stream = None
        
        self._setup_routes()
        self._setup_socketio_handlers()
        self._setup_audio_stream()
        
        logger.info("双向语音聊天服务初始化完成")
    
    def _setup_routes(self):
        """设置HTTP路由"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                "status": "healthy",
                "service": "audio_chat",
                "clients": len(self.active_clients),
                "streaming": self.is_streaming
            })
        
        @self.app.route('/clients', methods=['GET'])
        def get_clients():
            """获取活跃客户端"""
            clients = []
            for client_id, info in self.active_clients.items():
                clients.append({
                    "client_id": client_id,
                    "connected_time": info.get('connected_time'),
                    "is_talking": info.get('is_talking', False)
                })
            return jsonify({"clients": clients})
        
        @self.app.route('/speak', methods=['POST'])
        def speak_text():
            """让机器人说话"""
            try:
                data = request.json
                text = data.get('text', '')
                
                if not text:
                    return jsonify({"error": "缺少文本内容"}), 400
                
                # 异步播放语音
                def speak_async():
                    self.speech_processor.speak_text(text)
                    # 广播语音事件
                    self.socketio.emit('robot_speaking', {'text': text}, broadcast=True)
                
                threading.Thread(target=speak_async, daemon=True).start()
                
                return jsonify({"status": "success", "message": "开始语音播放"})
                
            except Exception as e:
                logger.error(f"语音播放错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/recognize', methods=['POST'])
        def recognize_audio():
            """识别音频中的语音"""
            try:
                data = request.json
                audio_base64 = data.get('audio', '')
                
                if not audio_base64:
                    return jsonify({"error": "缺少音频数据"}), 400
                
                # 解码base64音频数据
                audio_bytes = base64.b64decode(audio_base64)
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                
                # 识别语音
                text = self.speech_processor.recognize_speech(audio_array, self.sample_rate)
                
                if text:
                    return jsonify({"status": "success", "text": text})
                else:
                    return jsonify({"status": "no_speech", "text": ""})
                
            except Exception as e:
                logger.error(f"语音识别错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/audio/config', methods=['POST'])
        def set_audio_config():
            """设置音频配置"""
            try:
                data = request.json
                sample_rate = data.get('sample_rate', self.sample_rate)
                channels = data.get('channels', self.channels)
                chunk_size = data.get('chunk_size', self.chunk_size)

                # 更新配置
                self.sample_rate = sample_rate
                self.channels = channels
                self.chunk_size = chunk_size

                # 重新设置音频缓冲区
                self.audio_buffer = AudioBuffer(sample_rate, channels)

                return jsonify({
                    "status": "success",
                    "config": {
                        "sample_rate": self.sample_rate,
                        "channels": self.channels,
                        "chunk_size": self.chunk_size
                    }
                })

            except Exception as e:
                logger.error(f"设置音频配置错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/audio/config', methods=['GET'])
        def get_audio_config():
            """获取音频配置"""
            return jsonify({
                "sample_rate": self.sample_rate,
                "channels": self.channels,
                "chunk_size": self.chunk_size,
                "supported_formats": ["PCM", "WAV"],
                "supported_languages": ["zh-CN", "en-US", "ja-JP"]
            })

        @self.app.route('/tts/voices', methods=['GET'])
        def get_available_voices():
            """获取可用的TTS语音"""
            try:
                voices = []
                for voice in self.speech_processor.tts_engine.getProperty('voices'):
                    voices.append({
                        "id": voice.id,
                        "name": voice.name,
                        "languages": getattr(voice, 'languages', []),
                        "gender": getattr(voice, 'gender', 'unknown')
                    })

                return jsonify({
                    "voices": voices,
                    "current_voice": self.speech_processor.tts_engine.getProperty('voice')
                })

            except Exception as e:
                logger.error(f"获取语音列表错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/tts/voice', methods=['POST'])
        def set_tts_voice():
            """设置TTS语音"""
            try:
                data = request.json
                voice_id = data.get('voice_id')
                rate = data.get('rate', 180)
                volume = data.get('volume', 0.9)

                if voice_id:
                    self.speech_processor.tts_engine.setProperty('voice', voice_id)

                self.speech_processor.tts_engine.setProperty('rate', rate)
                self.speech_processor.tts_engine.setProperty('volume', volume)

                return jsonify({
                    "status": "success",
                    "voice_id": voice_id,
                    "rate": rate,
                    "volume": volume
                })

            except Exception as e:
                logger.error(f"设置TTS语音错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/conversation/history', methods=['GET'])
        def get_conversation_history():
            """获取对话历史（简单示例）"""
            # 这里可以实现对话历史存储
            return jsonify({
                "conversations": [],
                "total_count": 0,
                "message": "对话历史功能待实现"
            })
    
    def _setup_socketio_handlers(self):
        """设置SocketIO事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = request.sid
            self.active_clients[client_id] = {
                'connected_time': time.time(),
                'is_talking': False
            }
            logger.info(f"音频客户端连接: {client_id}")
            emit('connected', {'client_id': client_id})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            if client_id in self.active_clients:
                del self.active_clients[client_id]
            logger.info(f"音频客户端断开: {client_id}")
        
        @self.socketio.on('start_talking')
        def handle_start_talking():
            """开始说话"""
            client_id = request.sid
            if client_id in self.active_clients:
                self.active_clients[client_id]['is_talking'] = True
                self.audio_buffer.start_recording()
                emit('talk_started', {'status': 'recording'})
                logger.info(f"客户端开始说话: {client_id}")
        
        @self.socketio.on('stop_talking')
        def handle_stop_talking():
            """停止说话"""
            client_id = request.sid
            if client_id in self.active_clients:
                self.active_clients[client_id]['is_talking'] = False
                self.audio_buffer.stop_recording()
                
                # 处理录音数据
                self._process_recorded_audio(client_id)
                
                emit('talk_stopped', {'status': 'processing'})
                logger.info(f"客户端停止说话: {client_id}")
        
        @self.socketio.on('audio_data')
        def handle_audio_data(data):
            """接收音频数据"""
            client_id = request.sid
            try:
                # 解码音频数据
                audio_base64 = data.get('audio', '')
                audio_bytes = base64.b64decode(audio_base64)
                audio_array = np.frombuffer(audio_bytes, dtype=np.int16).astype(np.float32) / 32767.0
                
                # 添加到缓冲区
                self.audio_buffer.add_audio_data(audio_array)
                
            except Exception as e:
                logger.error(f"处理音频数据错误: {e}")
        
        @self.socketio.on('send_message')
        def handle_send_message(data):
            """发送语音消息"""
            client_id = request.sid
            text = data.get('text', '')
            
            if text:
                # 让机器人说话
                def speak_and_notify():
                    self.speech_processor.speak_text(text)
                    emit('message_played', {'text': text}, room=client_id)
                
                threading.Thread(target=speak_and_notify, daemon=True).start()
                logger.info(f"客户端发送消息: {text}")
    
    def _setup_audio_stream(self):
        """设置音频流"""
        def audio_callback(indata, frames, time, status):
            """音频回调函数"""
            if status:
                logger.warning(f"音频流状态: {status}")
            
            # 将音频数据添加到缓冲区
            self.audio_buffer.add_audio_data(indata[:, 0])
        
        try:
            self.audio_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                callback=audio_callback,
                blocksize=self.chunk_size
            )
            logger.info("音频流设置完成")
        except Exception as e:
            logger.error(f"音频流设置错误: {e}")
    
    def _process_recorded_audio(self, client_id: str):
        """处理录音音频"""
        def process():
            try:
                # 收集缓冲区中的所有音频数据
                audio_chunks = []
                while True:
                    chunk = self.audio_buffer.get_audio_data()
                    if chunk is None:
                        break
                    audio_chunks.append(chunk)
                
                if not audio_chunks:
                    return
                
                # 合并音频数据
                audio_data = np.concatenate(audio_chunks)
                
                # 识别语音
                text = self.speech_processor.recognize_speech(audio_data, self.sample_rate)
                
                if text:
                    # 发送识别结果
                    self.socketio.emit('speech_recognized', {
                        'text': text,
                        'client_id': client_id
                    }, room=client_id)
                    
                    # 可以在这里添加自动回复逻辑
                    # self._auto_reply(text, client_id)
                
            except Exception as e:
                logger.error(f"处理录音错误: {e}")
        
        threading.Thread(target=process, daemon=True).start()
    
    def _auto_reply(self, user_text: str, client_id: str):
        """自动回复逻辑（可选）"""
        # 简单的回复逻辑示例
        reply_map = {
            "你好": "你好！很高兴见到你！",
            "再见": "再见！期待下次见面！",
            "谢谢": "不客气！",
            "机器人": "我是你的机器人朋友！"
        }
        
        reply = None
        for key, value in reply_map.items():
            if key in user_text:
                reply = value
                break
        
        if not reply:
            reply = "我听到了，但是还不知道怎么回答。"
        
        # 延迟回复
        def delayed_reply():
            time.sleep(1)
            self.speech_processor.speak_text(reply)
            self.socketio.emit('robot_reply', {
                'text': reply,
                'original_text': user_text
            }, room=client_id)
        
        threading.Thread(target=delayed_reply, daemon=True).start()
    
    def start_service(self):
        """启动语音聊天服务"""
        def run_service():
            logger.info(f"启动双向语音聊天服务，端口: {self.port}")
            
            # 启动音频流
            if self.audio_stream:
                self.audio_stream.start()
                self.is_streaming = True
            
            self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False)
        
        service_thread = threading.Thread(target=run_service, daemon=True)
        service_thread.start()
        return service_thread
    
    def stop_service(self):
        """停止语音聊天服务"""
        # 停止音频流
        if self.audio_stream:
            self.audio_stream.stop()
            self.audio_stream.close()
            self.is_streaming = False
        
        # 清理客户端连接
        self.active_clients.clear()
        
        logger.info("双向语音聊天服务已停止")


if __name__ == "__main__":
    # 测试代码
    service = AudioChatService(8002)
    service.start_service()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop_service()