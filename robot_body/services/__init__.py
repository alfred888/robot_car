"""
机器人远程服务包
提供视频聊天、语音聊天和云台控制等远程服务
"""

from .video_chat_service import VideoChatService
from .audio_chat_service import AudioChatService
from .gimbal_control_service import GimbalControlService
from .remote_service_manager import RemoteServiceManager

__all__ = [
    'VideoChatService',
    'AudioChatService', 
    'GimbalControlService',
    'RemoteServiceManager'
]

__version__ = "1.0.0"