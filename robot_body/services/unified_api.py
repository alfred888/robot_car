#!/usr/bin/env python3
"""
统一远程服务API - 为iOS app提供统一的接口入口
整合视频、音频、云台控制等所有功能
"""

import json
import logging
import threading
import time
import requests
from typing import Dict, Any, Optional
from flask import Flask, request, jsonify, Response
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import uuid
from services.auth_manager import AuthManager

logger = logging.getLogger('unified_api')


class UnifiedRemoteAPI:
    """统一远程API类"""

    def __init__(self, port: int = 8000):
        self.port = port
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        CORS(self.app)

        # 服务端口配置
        self.service_ports = {
            'video_chat': 8001,
            'audio_chat': 8002,
            'gimbal_control': 8003,
            'service_manager': 9000
        }

        # 安全认证管理器
        self.auth_manager = AuthManager()

        # 会话管理
        self.active_sessions: Dict[str, dict] = {}
        self.session_timeout = 1800  # 30分钟

        self._setup_routes()
        self._setup_socketio_handlers()

        # 启动会话清理线程
        self.cleanup_thread = threading.Thread(target=self._session_cleanup_loop, daemon=True)
        self.cleanup_thread.start()

        logger.info("统一远程API初始化完成")

    def _setup_routes(self):
        """设置HTTP路由"""

        @self.app.route('/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                "status": "healthy",
                "service": "unified_remote_api",
                "version": "1.0.0",
                "active_sessions": len(self.active_sessions),
                "services": self._check_all_services()
            })

        @self.app.route('/auth/login', methods=['POST'])
        def login():
            """登录认证"""
            try:
                data = request.json
                app_id = data.get('app_id', '')
                api_key = data.get('api_key', '')
                device_id = data.get('device_id', str(uuid.uuid4()))
                device_name = data.get('device_name', 'Unknown Device')
                device_type = data.get('device_type', 'iOS')

                # 检查失败尝试次数
                if not self.auth_manager.check_failed_attempts(device_id):
                    return jsonify({"error": "尝试次数过多，请稍后再试"}), 429

                # 验证API密钥
                success, auth_result = self.auth_manager.authenticate_api_key(app_id, api_key)
                if not success:
                    self.auth_manager.record_failed_attempt(device_id)
                    return jsonify(auth_result), 401

                # 检查访问频率限制
                if not self.auth_manager.check_rate_limit(app_id):
                    return jsonify({"error": "访问频率超限"}), 429

                # 注册设备
                self.auth_manager.register_device(device_id, device_name, device_type)

                # 创建会话
                session = self.auth_manager.create_session(
                    device_id,
                    "default",
                    auth_result['permissions']
                )

                if not session:
                    return jsonify({"error": "创建会话失败"}), 500

                # 清除失败尝试记录
                self.auth_manager.clear_failed_attempts(device_id)

                # 生成JWT令牌
                jwt_token = self.auth_manager.generate_jwt_token(
                    device_id,
                    "default",
                    auth_result['permissions']
                )

                # 记录登录日志
                self.auth_manager.log_access(
                    session.session_id,
                    '/auth/login',
                    'POST',
                    200,
                    request.remote_addr
                )

                return jsonify({
                    "success": True,
                    "session_id": session.session_id,
                    "jwt_token": jwt_token,
                    "permissions": auth_result['permissions'],
                    "services": self.service_ports,
                    "expires_in": self.auth_manager.jwt_expiry_hours * 3600
                })

            except Exception as e:
                logger.error(f"登录错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/auth/logout', methods=['POST'])
        def logout():
            """登出"""
            try:
                session_id = request.headers.get('X-Session-ID')
                if session_id in self.active_sessions:
                    del self.active_sessions[session_id]

                return jsonify({"success": True, "message": "已登出"})

            except Exception as e:
                logger.error(f"登出错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/services/discovery', methods=['GET'])
        def service_discovery():
            """服务发现"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            services = {}
            for name, port in self.service_ports.items():
                status = self._check_service_status(name, port)
                services[name] = {
                    "name": name,
                    "port": port,
                    "url": f"http://localhost:{port}",
                    "status": status,
                    "endpoints": self._get_service_endpoints(name)
                }

            return jsonify({
                "services": services,
                "discovery_time": time.time()
            })

        # 视频相关API代理
        @self.app.route('/video/stream/info', methods=['GET'])
        def video_stream_info():
            """获取视频流信息"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('video_chat', '/stream/info', request.method, request.json)

        @self.app.route('/video/stream/quality', methods=['POST'])
        def set_video_quality():
            """设置视频质量"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('video_chat', '/stream/quality', request.method, request.json)

        @self.app.route('/video/snapshot', methods=['POST'])
        def take_video_snapshot():
            """拍摄视频快照"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('video_chat', '/stream/snapshot', request.method, request.json)

        # 音频相关API代理
        @self.app.route('/audio/speak', methods=['POST'])
        def speak_text():
            """让机器人说话"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('audio_chat', '/speak', request.method, request.json)

        @self.app.route('/audio/recognize', methods=['POST'])
        def recognize_audio():
            """识别音频"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('audio_chat', '/recognize', request.method, request.json)

        @self.app.route('/audio/config', methods=['GET', 'POST'])
        def audio_config():
            """音频配置"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('audio_chat', '/audio/config', request.method, request.json)

        @self.app.route('/audio/voices', methods=['GET'])
        def get_audio_voices():
            """获取可用语音"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('audio_chat', '/tts/voices', request.method, request.json)

        # 云台控制API代理
        @self.app.route('/gimbal/position', methods=['GET', 'POST'])
        def gimbal_position():
            """云台位置控制"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('gimbal_control', '/position', request.method, request.json)

        @self.app.route('/gimbal/move', methods=['POST'])
        def gimbal_move():
            """云台移动"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('gimbal_control', '/move', request.method, request.json)

        @self.app.route('/gimbal/preset/<preset_name>', methods=['POST'])
        def gimbal_preset(preset_name):
            """云台预设位置"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('gimbal_control', f'/preset/{preset_name}', request.method, request.json)

        @self.app.route('/gimbal/presets', methods=['GET', 'POST'])
        def gimbal_presets():
            """云台预设位置管理"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('gimbal_control', '/presets', request.method, request.json)

        @self.app.route('/gimbal/scan', methods=['POST'])
        def gimbal_scan():
            """云台扫描"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('gimbal_control', '/scan', request.method, request.json)

        @self.app.route('/gimbal/gesture', methods=['POST'])
        def gimbal_gesture():
            """云台手势控制"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('gimbal_control', '/gesture', request.method, request.json)

        @self.app.route('/gimbal/calibrate', methods=['POST'])
        def gimbal_calibrate():
            """云台校准"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            return self._proxy_request('gimbal_control', '/calibrate', request.method, request.json)

        # 综合控制API
        @self.app.route('/robot/status', methods=['GET'])
        def robot_status():
            """获取机器人整体状态"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            try:
                status = {
                    "timestamp": time.time(),
                    "services": {},
                    "system": {}
                }

                # 获取各服务状态
                for name, port in self.service_ports.items():
                    try:
                        if name == 'service_manager':
                            response = requests.get(f"http://localhost:{port}/system", timeout=3)
                            if response.status_code == 200:
                                status["system"] = response.json()
                        else:
                            response = requests.get(f"http://localhost:{port}/health", timeout=3)
                            if response.status_code == 200:
                                status["services"][name] = response.json()
                    except:
                        status["services"][name] = {"status": "offline"}

                return jsonify(status)

            except Exception as e:
                logger.error(f"获取机器人状态错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/robot/control', methods=['POST'])
        def robot_control():
            """综合控制接口"""
            if not self._validate_session():
                return jsonify({"error": "会话无效"}), 401

            try:
                data = request.json
                command = data.get('command', '')
                params = data.get('params', {})

                result = self._execute_robot_command(command, params)
                return jsonify(result)

            except Exception as e:
                logger.error(f"机器人控制错误: {e}")
                return jsonify({"error": str(e)}), 500

        # 安全管理接口
        @self.app.route('/admin/auth/sessions', methods=['GET'])
        def get_auth_sessions():
            """获取所有认证会话（管理员接口）"""
            if not self._validate_admin_access():
                return jsonify({"error": "管理员权限不足"}), 403

            return jsonify({
                "sessions": self.auth_manager.get_all_sessions(),
                "total": len(self.auth_manager.active_sessions)
            })

        @self.app.route('/admin/auth/devices', methods=['GET'])
        def get_auth_devices():
            """获取所有注册设备（管理员接口）"""
            if not self._validate_admin_access():
                return jsonify({"error": "管理员权限不足"}), 403

            return jsonify({
                "devices": self.auth_manager.get_all_devices(),
                "total": len(self.auth_manager.registered_devices)
            })

        @self.app.route('/admin/auth/stats', methods=['GET'])
        def get_auth_stats():
            """获取认证统计信息（管理员接口）"""
            if not self._validate_admin_access():
                return jsonify({"error": "管理员权限不足"}), 403

            return jsonify(self.auth_manager.get_stats())

        @self.app.route('/admin/auth/logs', methods=['GET'])
        def get_access_logs():
            """获取访问日志（管理员接口）"""
            if not self._validate_admin_access():
                return jsonify({"error": "管理员权限不足"}), 403

            limit = request.args.get('limit', 100, type=int)
            logs = self.auth_manager.access_logs[-limit:]

            return jsonify({
                "logs": logs,
                "total": len(self.auth_manager.access_logs),
                "limit": limit
            })

        @self.app.route('/admin/auth/cleanup', methods=['POST'])
        def cleanup_auth():
            """清理过期会话（管理员接口）"""
            if not self._validate_admin_access():
                return jsonify({"error": "管理员权限不足"}), 403

            self.auth_manager.cleanup_expired_sessions()
            return jsonify({
                "success": True,
                "message": "已清理过期会话"
            })

    def _setup_socketio_handlers(self):
        """设置SocketIO事件处理器"""

        @self.socketio.on('connect')
        def handle_connect():
            client_id = request.sid
            logger.info(f"统一API客户端连接: {client_id}")
            emit('connected', {'client_id': client_id})

        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            logger.info(f"统一API客户端断开: {client_id}")

        @self.socketio.on('authenticate')
        def handle_authenticate(data):
            """WebSocket认证"""
            try:
                session_id = data.get('session_id', '')
                if session_id in self.active_sessions:
                    self.active_sessions[session_id]['last_activity'] = time.time()
                    emit('authenticated', {'success': True})
                else:
                    emit('authenticated', {'success': False, 'error': '会话无效'})
            except Exception as e:
                emit('authenticated', {'success': False, 'error': str(e)})

    def _validate_session(self) -> bool:
        """验证会话"""
        # 尝试从不同地方获取认证信息
        session_id = request.headers.get('X-Session-ID')
        jwt_token = request.headers.get('Authorization', '').replace('Bearer ', '')

        # 优先使用JWT令牌验证
        if jwt_token:
            payload = self.auth_manager.verify_jwt_token(jwt_token)
            if payload:
                # 记录访问日志
                self.auth_manager.log_access(
                    f"jwt_{payload['device_id']}",
                    request.endpoint or '',
                    request.method,
                    200,
                    request.remote_addr
                )
                return True

        # 回退到会话ID验证
        if session_id:
            session = self.auth_manager.validate_session(session_id)
            if session:
                # 记录访问日志
                self.auth_manager.log_access(
                    session_id,
                    request.endpoint or '',
                    request.method,
                    200,
                    request.remote_addr
                )
                return True

        return False

    def _validate_admin_access(self) -> bool:
        """验证管理员访问权限"""
        # 这里可以实现更复杂的管理员验证逻辑
        admin_token = request.headers.get('X-Admin-Token')
        return admin_token == 'admin_secret_token_2024'  # 简单示例

    def _get_permissions(self, app_id: str) -> list:
        """获取权限列表"""
        permission_map = {
            'ios_app_v1': ['video', 'audio', 'gimbal', 'system'],
            'test_client': ['video', 'audio']
        }
        return permission_map.get(app_id, [])

    def _check_all_services(self) -> dict:
        """检查所有服务状态"""
        services = {}
        for name, port in self.service_ports.items():
            services[name] = self._check_service_status(name, port)
        return services

    def _check_service_status(self, service_name: str, port: int) -> str:
        """检查单个服务状态"""
        try:
            response = requests.get(f"http://localhost:{port}/health", timeout=3)
            return "online" if response.status_code == 200 else "error"
        except:
            return "offline"

    def _get_service_endpoints(self, service_name: str) -> list:
        """获取服务端点"""
        endpoints = {
            'video_chat': [
                '/health', '/connections', '/offer', '/answer', '/candidate',
                '/stream/quality', '/stream/info', '/stream/snapshot'
            ],
            'audio_chat': [
                '/health', '/clients', '/speak', '/recognize',
                '/audio/config', '/tts/voices', '/tts/voice'
            ],
            'gimbal_control': [
                '/health', '/position', '/move', '/preset', '/presets',
                '/stop', '/limits', '/tracking', '/calibrate', '/scan', '/gesture'
            ],
            'service_manager': [
                '/health', '/services', '/discovery', '/system'
            ]
        }
        return endpoints.get(service_name, [])

    def _proxy_request(self, service_name: str, endpoint: str, method: str, data: Any) -> Response:
        """代理请求到指定服务"""
        try:
            port = self.service_ports.get(service_name)
            if not port:
                return jsonify({"error": f"未知服务: {service_name}"}), 404

            url = f"http://localhost:{port}{endpoint}"

            if method == 'GET':
                response = requests.get(url, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, timeout=10)
            else:
                return jsonify({"error": f"不支持的HTTP方法: {method}"}), 405

            return Response(
                response.content,
                status=response.status_code,
                headers=dict(response.headers)
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"代理请求错误: {e}")
            return jsonify({"error": f"服务请求失败: {str(e)}"}), 503
        except Exception as e:
            logger.error(f"代理请求异常: {e}")
            return jsonify({"error": str(e)}), 500

    def _execute_robot_command(self, command: str, params: dict) -> dict:
        """执行机器人综合命令"""
        try:
            if command == 'say_and_look':
                # 说话并转向指定方向
                text = params.get('text', '')
                direction = params.get('direction', 'center')

                # 先转向
                if direction != 'center':
                    gimbal_data = {'preset': direction}
                    self._proxy_request('gimbal_control', f'/preset/{direction}', 'POST', gimbal_data)

                # 然后说话
                if text:
                    audio_data = {'text': text}
                    self._proxy_request('audio_chat', '/speak', 'POST', audio_data)

                return {"success": True, "message": f"执行: {command}"}

            elif command == 'patrol':
                # 巡逻模式
                scan_type = params.get('type', 'horizontal')
                gimbal_data = {'type': scan_type}
                self._proxy_request('gimbal_control', '/scan', 'POST', gimbal_data)

                return {"success": True, "message": "开始巡逻"}

            elif command == 'interactive_mode':
                # 交互模式 - 回到中心位置
                self._proxy_request('gimbal_control', '/preset/home', 'POST', {})
                audio_data = {'text': '我准备好与您交流了！'}
                self._proxy_request('audio_chat', '/speak', 'POST', audio_data)

                return {"success": True, "message": "进入交互模式"}

            else:
                return {"success": False, "error": f"未知命令: {command}"}

        except Exception as e:
            logger.error(f"执行机器人命令错误: {e}")
            return {"success": False, "error": str(e)}

    def _session_cleanup_loop(self):
        """会话清理循环"""
        while True:
            try:
                current_time = time.time()
                expired_sessions = []

                for session_id, session_info in self.active_sessions.items():
                    if current_time - session_info['last_activity'] > self.session_timeout:
                        expired_sessions.append(session_id)

                for session_id in expired_sessions:
                    del self.active_sessions[session_id]
                    logger.info(f"清理过期会话: {session_id}")

                time.sleep(300)  # 每5分钟检查一次

            except Exception as e:
                logger.error(f"会话清理错误: {e}")
                time.sleep(60)

    def start_service(self):
        """启动统一API服务"""
        def run_service():
            logger.info(f"启动统一远程API服务，端口: {self.port}")
            self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False)

        service_thread = threading.Thread(target=run_service, daemon=True)
        service_thread.start()
        return service_thread

    def stop_service(self):
        """停止统一API服务"""
        self.active_sessions.clear()
        logger.info("统一远程API服务已停止")


if __name__ == "__main__":
    # 测试代码
    api = UnifiedRemoteAPI(8000)
    api.start_service()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        api.stop_service()