#!/usr/bin/env python3
"""
视频聊天服务 - 基于WebRTC的双向视频通话服务
支持远程APP与机器人进行实时视频对话
"""

import asyncio
import json
import uuid
import logging
import threading
import time
from typing import Dict, Set
from aiortc import RTCPeerConnection, RTCSessionDescription, VideoStreamTrack, RTCConfiguration, RTCIceServer
from aiortc.contrib.media import MediaPlayer, MediaRelay
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
import cv2
import numpy as np
from base_action.cv_ctrl import OpencvFuncs


logger = logging.getLogger('video_chat')


class RobotVideoTrack(VideoStreamTrack):
    """机器人视频轨道 - 提供机器人摄像头画面"""
    
    def __init__(self, cv_ctrl: OpencvFuncs):
        super().__init__()
        self.cv_ctrl = cv_ctrl
        
    async def recv(self):
        """接收并返回视频帧"""
        pts, time_base = await self.next_timestamp()
        
        # 获取机器人摄像头帧
        frame_bytes = self.cv_ctrl.frame_process()
        
        # 将JPEG字节转换为OpenCV格式
        nparr = np.frombuffer(frame_bytes, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # 转换为RGB格式（WebRTC需要）
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # 创建av.VideoFrame
        from av import VideoFrame
        av_frame = VideoFrame.from_ndarray(frame, format='rgb24')
        av_frame.pts = pts
        av_frame.time_base = time_base
        
        return av_frame


class VideoChatService:
    """视频聊天服务类"""
    
    def __init__(self, cv_ctrl: OpencvFuncs, port: int = 8001):
        self.cv_ctrl = cv_ctrl
        self.port = port
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # WebRTC配置
        self.ice_servers = [
            RTCIceServer(urls=["stun:stun.l.google.com:19302"])
        ]
        self.rtc_config = RTCConfiguration(iceServers=self.ice_servers)
        
        # 连接管理
        self.peer_connections: Dict[str, RTCPeerConnection] = {}
        self.max_connections = 5
        
        # 媒体中继
        self.media_relay = MediaRelay()
        
        self._setup_routes()
        self._setup_socketio_handlers()
        
        logger.info("视频聊天服务初始化完成")
    
    def _setup_routes(self):
        """设置HTTP路由"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                "status": "healthy",
                "service": "video_chat",
                "connections": len(self.peer_connections)
            })
        
        @self.app.route('/connections', methods=['GET'])
        def get_connections():
            """获取当前连接信息"""
            connections = []
            for peer_id, pc in self.peer_connections.items():
                state = str(pc.connectionState)
                connections.append({
                    "peer_id": peer_id,
                    "state": state
                })
            return jsonify({"connections": connections})
        
        @self.app.route('/offer', methods=['POST'])
        def handle_offer():
            """处理WebRTC offer"""
            try:
                data = request.json
                return asyncio.run(self._handle_offer_async(data))
            except Exception as e:
                logger.error(f"处理offer错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/answer', methods=['POST'])
        def handle_answer():
            """处理WebRTC answer"""
            try:
                data = request.json
                return asyncio.run(self._handle_answer_async(data))
            except Exception as e:
                logger.error(f"处理answer错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/candidate', methods=['POST'])
        def handle_candidate():
            """处理ICE candidate"""
            try:
                data = request.json
                return asyncio.run(self._handle_candidate_async(data))
            except Exception as e:
                logger.error(f"处理candidate错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/stream/quality', methods=['POST'])
        def set_stream_quality():
            """设置视频流质量"""
            try:
                data = request.json
                quality = data.get('quality', 'medium')
                fps = data.get('fps', 30)
                resolution = data.get('resolution', {'width': 640, 'height': 480})

                # 更新CV控制器的视频参数
                if hasattr(self.cv_ctrl, 'set_video_quality'):
                    if quality == 'low':
                        self.cv_ctrl.set_video_quality(50)
                    elif quality == 'medium':
                        self.cv_ctrl.set_video_quality(75)
                    elif quality == 'high':
                        self.cv_ctrl.set_video_quality(90)

                return jsonify({
                    "status": "success",
                    "quality": quality,
                    "fps": fps,
                    "resolution": resolution
                })
            except Exception as e:
                logger.error(f"设置视频质量错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/stream/info', methods=['GET'])
        def get_stream_info():
            """获取视频流信息"""
            return jsonify({
                "active_connections": len(self.peer_connections),
                "max_connections": self.max_connections,
                "supported_formats": ["H264", "VP8", "VP9"],
                "supported_resolutions": [
                    {"width": 320, "height": 240, "name": "QVGA"},
                    {"width": 640, "height": 480, "name": "VGA"},
                    {"width": 1280, "height": 720, "name": "HD"},
                    {"width": 1920, "height": 1080, "name": "FHD"}
                ]
            })

        @self.app.route('/stream/snapshot', methods=['POST'])
        def take_snapshot():
            """拍摄快照"""
            try:
                # 获取当前帧
                frame_bytes = self.cv_ctrl.frame_process()

                # 保存快照
                timestamp = int(time.time())
                filename = f"snapshot_{timestamp}.jpg"

                # 这里可以保存到指定目录
                # 返回快照信息
                return jsonify({
                    "status": "success",
                    "filename": filename,
                    "timestamp": timestamp,
                    "size": len(frame_bytes)
                })
            except Exception as e:
                logger.error(f"拍摄快照错误: {e}")
                return jsonify({"error": str(e)}), 500
    
    def _setup_socketio_handlers(self):
        """设置SocketIO事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = request.sid
            logger.info(f"客户端连接: {client_id}")
            emit('connected', {'client_id': client_id})
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            logger.info(f"客户端断开: {client_id}")
            self._cleanup_peer_connection(client_id)
        
        @self.socketio.on('webrtc_offer')
        def handle_webrtc_offer(data):
            """处理WebRTC offer信令"""
            client_id = request.sid
            offer_data = {
                'client_id': client_id,
                'offer': data['offer']
            }
            
            # 异步处理offer
            def process_offer():
                try:
                    result = asyncio.run(self._handle_offer_async(offer_data))
                    emit('webrtc_answer', result, room=client_id)
                except Exception as e:
                    logger.error(f"处理offer错误: {e}")
                    emit('error', {'message': str(e)}, room=client_id)
            
            threading.Thread(target=process_offer, daemon=True).start()
        
        @self.socketio.on('webrtc_candidate')
        def handle_webrtc_candidate(data):
            """处理ICE candidate信令"""
            client_id = request.sid
            candidate_data = {
                'client_id': client_id,
                'candidate': data['candidate']
            }
            
            # 异步处理candidate
            def process_candidate():
                try:
                    asyncio.run(self._handle_candidate_async(candidate_data))
                except Exception as e:
                    logger.error(f"处理candidate错误: {e}")
                    emit('error', {'message': str(e)}, room=client_id)
            
            threading.Thread(target=process_candidate, daemon=True).start()
    
    async def _handle_offer_async(self, data):
        """异步处理WebRTC offer"""
        client_id = data.get('client_id')
        offer_sdp = data.get('offer', {})
        
        if not client_id or not offer_sdp:
            raise ValueError("缺少client_id或offer数据")
        
        # 检查连接数限制
        if len(self.peer_connections) >= self.max_connections:
            # 移除最旧的连接
            oldest_id = next(iter(self.peer_connections))
            await self._cleanup_peer_connection(oldest_id)
        
        # 创建新的PeerConnection
        pc = RTCPeerConnection(self.rtc_config)
        self.peer_connections[client_id] = pc
        
        # 设置连接状态变化处理
        @pc.on("connectionstatechange")
        async def on_connectionstatechange():
            logger.info(f"连接状态变化 [{client_id}]: {pc.connectionState}")
            if pc.connectionState == "failed" or pc.connectionState == "closed":
                await self._cleanup_peer_connection(client_id)
        
        # 添加机器人视频轨道
        robot_video = RobotVideoTrack(self.cv_ctrl)
        pc.addTrack(robot_video)
        
        # 设置远程描述
        offer = RTCSessionDescription(
            sdp=offer_sdp.get('sdp'),
            type=offer_sdp.get('type')
        )
        await pc.setRemoteDescription(offer)
        
        # 创建answer
        answer = await pc.createAnswer()
        await pc.setLocalDescription(answer)
        
        logger.info(f"创建WebRTC连接 [{client_id}]")
        
        return {
            "answer": {
                "sdp": pc.localDescription.sdp,
                "type": pc.localDescription.type
            }
        }
    
    async def _handle_answer_async(self, data):
        """异步处理WebRTC answer"""
        client_id = data.get('client_id')
        answer_sdp = data.get('answer', {})
        
        if client_id not in self.peer_connections:
            raise ValueError(f"未找到客户端连接: {client_id}")
        
        pc = self.peer_connections[client_id]
        answer = RTCSessionDescription(
            sdp=answer_sdp.get('sdp'),
            type=answer_sdp.get('type')
        )
        
        await pc.setRemoteDescription(answer)
        logger.info(f"设置远程描述 [{client_id}]")
        
        return {"status": "success"}
    
    async def _handle_candidate_async(self, data):
        """异步处理ICE candidate"""
        client_id = data.get('client_id')
        candidate_data = data.get('candidate', {})
        
        if client_id not in self.peer_connections:
            logger.warning(f"未找到客户端连接处理candidate: {client_id}")
            return
        
        pc = self.peer_connections[client_id]
        
        if candidate_data.get('candidate'):
            from aiortc import RTCIceCandidate
            candidate = RTCIceCandidate(
                component=candidate_data.get('component', 1),
                foundation=candidate_data.get('foundation', ''),
                ip=candidate_data.get('ip', ''),
                port=candidate_data.get('port', 0),
                priority=candidate_data.get('priority', 0),
                protocol=candidate_data.get('protocol', 'udp'),
                type=candidate_data.get('type', 'host')
            )
            await pc.addIceCandidate(candidate)
            logger.debug(f"添加ICE candidate [{client_id}]")
    
    async def _cleanup_peer_connection(self, client_id: str):
        """清理PeerConnection"""
        if client_id in self.peer_connections:
            pc = self.peer_connections[client_id]
            await pc.close()
            del self.peer_connections[client_id]
            logger.info(f"清理连接 [{client_id}]")
    
    def start_service(self):
        """启动视频聊天服务"""
        def run_service():
            logger.info(f"启动视频聊天服务，端口: {self.port}")
            self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False)
        
        service_thread = threading.Thread(target=run_service, daemon=True)
        service_thread.start()
        return service_thread
    
    def stop_service(self):
        """停止视频聊天服务"""
        # 关闭所有连接
        for client_id in list(self.peer_connections.keys()):
            asyncio.run(self._cleanup_peer_connection(client_id))
        
        logger.info("视频聊天服务已停止")


if __name__ == "__main__":
    # 测试代码
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    from base_action.cv_ctrl import OpencvFuncs
    from base_action.base_ctrl import BaseController
    
    # 创建测试实例
    base = BaseController('/dev/ttyAMA0', 115200)
    cv_ctrl = OpencvFuncs('.', base)
    
    # 启动服务
    service = VideoChatService(cv_ctrl, 8001)
    service.start_service()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop_service()