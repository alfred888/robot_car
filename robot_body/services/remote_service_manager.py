#!/usr/bin/env python3
"""
远程服务管理器 - 统一管理所有远程服务
提供服务发现、健康检查、负载均衡和统一API入口
"""

import json
import logging
import threading
import time
import requests
from typing import Dict, List, Optional
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import psutil

# 导入服务类
from services.video_chat_service import VideoChatService
from services.audio_chat_service import AudioChatService
from services.gimbal_control_service import GimbalControlService


logger = logging.getLogger('service_manager')


class ServiceInfo:
    """服务信息类"""
    
    def __init__(self, name: str, service_instance, port: int, description: str = ""):
        self.name = name
        self.service_instance = service_instance
        self.port = port
        self.description = description
        self.status = "stopped"
        self.thread = None
        self.start_time = None
        self.last_health_check = None
        self.health_status = "unknown"
        
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "port": self.port,
            "description": self.description,
            "status": self.status,
            "start_time": self.start_time,
            "last_health_check": self.last_health_check,
            "health_status": self.health_status
        }


class RemoteServiceManager:
    """远程服务管理器类"""
    
    def __init__(self, base_controller, cv_controller, port: int = 9000):
        self.base_controller = base_controller
        self.cv_controller = cv_controller
        self.port = port
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # 服务注册表
        self.services: Dict[str, ServiceInfo] = {}
        self.health_check_interval = 30  # 健康检查间隔（秒）
        self.health_check_thread = None
        self.is_running = False
        
        # 系统信息
        self.system_info = {
            "cpu_percent": 0.0,
            "memory_percent": 0.0,
            "disk_usage": 0.0,
            "network_connections": 0
        }
        
        self._register_services()
        self._setup_routes()
        self._setup_socketio_handlers()
        
        logger.info("远程服务管理器初始化完成")
    
    def _register_services(self):
        """注册所有服务"""
        try:
            # 视频聊天服务
            video_service = VideoChatService(self.cv_controller, 8001)
            self.services["video_chat"] = ServiceInfo(
                name="video_chat",
                service_instance=video_service,
                port=8001,
                description="视频聊天服务 - 提供双向视频通话功能"
            )
            
            # 语音聊天服务
            audio_service = AudioChatService(8002)
            self.services["audio_chat"] = ServiceInfo(
                name="audio_chat",
                service_instance=audio_service,
                port=8002,
                description="语音聊天服务 - 提供双向语音对话功能"
            )
            
            # 云台控制服务
            gimbal_service = GimbalControlService(self.base_controller, 8003)
            self.services["gimbal_control"] = ServiceInfo(
                name="gimbal_control",
                service_instance=gimbal_service,
                port=8003,
                description="云台控制服务 - 提供精确的云台方向控制"
            )
            
            logger.info(f"注册了 {len(self.services)} 个服务")
            
        except Exception as e:
            logger.error(f"注册服务错误: {e}")
    
    def _setup_routes(self):
        """设置HTTP路由"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """管理器健康检查"""
            return jsonify({
                "status": "healthy",
                "service": "remote_service_manager",
                "services_count": len(self.services),
                "running_services": len([s for s in self.services.values() if s.status == "running"]),
                "system_info": self.system_info
            })
        
        @self.app.route('/services', methods=['GET'])
        def get_services():
            """获取所有服务信息"""
            services_info = {}
            for name, service in self.services.items():
                services_info[name] = service.to_dict()
            
            return jsonify({
                "services": services_info,
                "total_count": len(self.services),
                "running_count": len([s for s in self.services.values() if s.status == "running"])
            })
        
        @self.app.route('/services/<service_name>', methods=['GET'])
        def get_service_info(service_name):
            """获取特定服务信息"""
            if service_name not in self.services:
                return jsonify({"error": f"服务 '{service_name}' 不存在"}), 404
            
            service = self.services[service_name]
            return jsonify(service.to_dict())
        
        @self.app.route('/services/<service_name>/start', methods=['POST'])
        def start_service(service_name):
            """启动服务"""
            try:
                result = self.start_service_by_name(service_name)
                if result["success"]:
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                    
            except Exception as e:
                logger.error(f"启动服务错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/services/<service_name>/stop', methods=['POST'])
        def stop_service(service_name):
            """停止服务"""
            try:
                result = self.stop_service_by_name(service_name)
                if result["success"]:
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                    
            except Exception as e:
                logger.error(f"停止服务错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/services/<service_name>/restart', methods=['POST'])
        def restart_service(service_name):
            """重启服务"""
            try:
                result = self.restart_service_by_name(service_name)
                if result["success"]:
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                    
            except Exception as e:
                logger.error(f"重启服务错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/services/start_all', methods=['POST'])
        def start_all_services():
            """启动所有服务"""
            try:
                results = self.start_all_services()
                return jsonify(results)
                
            except Exception as e:
                logger.error(f"启动所有服务错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/services/stop_all', methods=['POST'])
        def stop_all_services():
            """停止所有服务"""
            try:
                results = self.stop_all_services()
                return jsonify(results)
                
            except Exception as e:
                logger.error(f"停止所有服务错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/system', methods=['GET'])
        def get_system_info():
            """获取系统信息"""
            self._update_system_info()
            return jsonify(self.system_info)
        
        @self.app.route('/discovery', methods=['GET'])
        def service_discovery():
            """服务发现 - 返回所有运行中服务的地址"""
            running_services = {}
            for name, service in self.services.items():
                if service.status == "running":
                    running_services[name] = {
                        "name": name,
                        "port": service.port,
                        "url": f"http://localhost:{service.port}",
                        "description": service.description,
                        "health": service.health_status
                    }
            
            return jsonify({
                "services": running_services,
                "discovery_time": time.time()
            })
    
    def _setup_socketio_handlers(self):
        """设置SocketIO事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = request.sid
            logger.info(f"管理器客户端连接: {client_id}")
            
            # 发送当前服务状态
            services_status = {}
            for name, service in self.services.items():
                services_status[name] = service.to_dict()
            
            emit('connected', {
                'client_id': client_id,
                'services': services_status,
                'system_info': self.system_info
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            logger.info(f"管理器客户端断开: {client_id}")
        
        @self.socketio.on('get_services_status')
        def handle_get_services_status():
            """获取服务状态"""
            services_status = {}
            for name, service in self.services.items():
                services_status[name] = service.to_dict()
            
            emit('services_status', services_status)
        
        @self.socketio.on('start_service')
        def handle_start_service(data):
            """启动服务"""
            service_name = data.get('service_name')
            if service_name:
                result = self.start_service_by_name(service_name)
                emit('service_action_result', {
                    'action': 'start',
                    'service_name': service_name,
                    **result
                })
        
        @self.socketio.on('stop_service')
        def handle_stop_service(data):
            """停止服务"""
            service_name = data.get('service_name')
            if service_name:
                result = self.stop_service_by_name(service_name)
                emit('service_action_result', {
                    'action': 'stop',
                    'service_name': service_name,
                    **result
                })
    
    def start_service_by_name(self, service_name: str) -> dict:
        """按名称启动服务"""
        if service_name not in self.services:
            return {"success": False, "error": f"服务 '{service_name}' 不存在"}
        
        service = self.services[service_name]
        
        if service.status == "running":
            return {"success": False, "error": f"服务 '{service_name}' 已在运行"}
        
        try:
            # 启动服务
            service.thread = service.service_instance.start_service()
            service.status = "running"
            service.start_time = time.time()
            
            logger.info(f"服务 '{service_name}' 已启动")
            
            # 广播服务状态变化
            self.socketio.emit('service_status_changed', {
                'service_name': service_name,
                'status': 'running',
                'start_time': service.start_time
            }, broadcast=True)
            
            return {
                "success": True,
                "message": f"服务 '{service_name}' 启动成功",
                "service_info": service.to_dict()
            }
            
        except Exception as e:
            service.status = "failed"
            logger.error(f"启动服务 '{service_name}' 错误: {e}")
            return {"success": False, "error": str(e)}
    
    def stop_service_by_name(self, service_name: str) -> dict:
        """按名称停止服务"""
        if service_name not in self.services:
            return {"success": False, "error": f"服务 '{service_name}' 不存在"}
        
        service = self.services[service_name]
        
        if service.status != "running":
            return {"success": False, "error": f"服务 '{service_name}' 未在运行"}
        
        try:
            # 停止服务
            service.service_instance.stop_service()
            service.status = "stopped"
            service.start_time = None
            
            logger.info(f"服务 '{service_name}' 已停止")
            
            # 广播服务状态变化
            self.socketio.emit('service_status_changed', {
                'service_name': service_name,
                'status': 'stopped'
            }, broadcast=True)
            
            return {
                "success": True,
                "message": f"服务 '{service_name}' 停止成功",
                "service_info": service.to_dict()
            }
            
        except Exception as e:
            logger.error(f"停止服务 '{service_name}' 错误: {e}")
            return {"success": False, "error": str(e)}
    
    def restart_service_by_name(self, service_name: str) -> dict:
        """按名称重启服务"""
        if service_name not in self.services:
            return {"success": False, "error": f"服务 '{service_name}' 不存在"}
        
        # 先停止服务
        if self.services[service_name].status == "running":
            stop_result = self.stop_service_by_name(service_name)
            if not stop_result["success"]:
                return stop_result
            
            # 等待服务完全停止
            time.sleep(2)
        
        # 再启动服务
        return self.start_service_by_name(service_name)
    
    def start_all_services(self) -> dict:
        """启动所有服务"""
        results = {}
        for service_name in self.services:
            results[service_name] = self.start_service_by_name(service_name)
        
        success_count = len([r for r in results.values() if r.get("success")])
        
        return {
            "success": success_count > 0,
            "started_count": success_count,
            "total_count": len(self.services),
            "results": results
        }
    
    def stop_all_services(self) -> dict:
        """停止所有服务"""
        results = {}
        for service_name in self.services:
            if self.services[service_name].status == "running":
                results[service_name] = self.stop_service_by_name(service_name)
        
        success_count = len([r for r in results.values() if r.get("success")])
        
        return {
            "success": success_count > 0,
            "stopped_count": success_count,
            "results": results
        }
    
    def _health_check_loop(self):
        """健康检查循环"""
        while self.is_running:
            try:
                for service_name, service in self.services.items():
                    if service.status == "running":
                        self._check_service_health(service)
                
                # 更新系统信息
                self._update_system_info()
                
                # 广播健康状态
                self.socketio.emit('health_update', {
                    'services': {name: s.health_status for name, s in self.services.items()},
                    'system_info': self.system_info,
                    'timestamp': time.time()
                }, broadcast=True)
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"健康检查错误: {e}")
                time.sleep(5)
    
    def _check_service_health(self, service: ServiceInfo):
        """检查单个服务健康状态"""
        try:
            # 尝试访问服务的健康检查端点
            url = f"http://localhost:{service.port}/health"
            response = requests.get(url, timeout=5)
            
            if response.status_code == 200:
                service.health_status = "healthy"
            else:
                service.health_status = "unhealthy"
                
            service.last_health_check = time.time()
            
        except requests.exceptions.RequestException:
            service.health_status = "unreachable"
            service.last_health_check = time.time()
        except Exception as e:
            service.health_status = "error"
            service.last_health_check = time.time()
            logger.error(f"检查服务 {service.name} 健康状态错误: {e}")
    
    def _update_system_info(self):
        """更新系统信息"""
        try:
            self.system_info = {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "network_connections": len(psutil.net_connections()),
                "update_time": time.time()
            }
        except Exception as e:
            logger.error(f"更新系统信息错误: {e}")
    
    def start_manager(self):
        """启动服务管理器"""
        def run_manager():
            logger.info(f"启动远程服务管理器，端口: {self.port}")
            self.is_running = True
            
            # 启动健康检查线程
            self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
            self.health_check_thread.start()
            
            # 启动Flask应用
            self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False)
        
        manager_thread = threading.Thread(target=run_manager, daemon=True)
        manager_thread.start()
        return manager_thread
    
    def stop_manager(self):
        """停止服务管理器"""
        self.is_running = False
        
        # 停止所有服务
        self.stop_all_services()
        
        logger.info("远程服务管理器已停止")


if __name__ == "__main__":
    # 测试代码
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    from base_action.base_ctrl import BaseController
    from base_action.cv_ctrl import OpencvFuncs
    
    # 创建测试实例
    base = BaseController('/dev/ttyAMA0', 115200)
    cv_ctrl = OpencvFuncs('.', base)
    
    # 启动管理器
    manager = RemoteServiceManager(base, cv_ctrl, 9000)
    manager.start_manager()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        manager.stop_manager()