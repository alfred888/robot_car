#!/usr/bin/env python3
"""
云台方向控制服务 - 提供机器人云台的精确控制
支持角度控制、速度控制、预设位置和跟踪模式
"""

import json
import logging
import threading
import time
import math
from typing import Dict, Tuple, Optional
from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, disconnect
from base_action.base_ctrl import BaseController


logger = logging.getLogger('gimbal_control')


class GimbalPosition:
    """云台位置类"""
    
    def __init__(self, pan: float = 0.0, tilt: float = 0.0):
        self.pan = pan    # 水平角度 (-180 到 180)
        self.tilt = tilt  # 垂直角度 (-90 到 90)
    
    def to_dict(self) -> dict:
        return {"pan": self.pan, "tilt": self.tilt}
    
    def __str__(self):
        return f"Pan: {self.pan:.2f}°, Tilt: {self.tilt:.2f}°"


class GimbalControlService:
    """云台控制服务类"""
    
    def __init__(self, base_controller: BaseController, port: int = 8003):
        self.base_controller = base_controller
        self.port = port
        self.app = Flask(__name__)
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # 云台状态
        self.current_position = GimbalPosition(0.0, 0.0)
        self.target_position = GimbalPosition(0.0, 0.0)
        self.is_moving = False
        self.movement_speed = 200  # 默认移动速度
        self.movement_smoothness = 10  # 移动平滑度
        
        # 云台限制
        self.pan_limits = (-180.0, 180.0)    # 水平角度限制
        self.tilt_limits = (-30.0, 30.0)     # 垂直角度限制
        self.max_speed = 500                  # 最大速度
        self.min_speed = 50                   # 最小速度
        
        # 预设位置
        self.preset_positions = {
            "home": GimbalPosition(0.0, 0.0),
            "left": GimbalPosition(-90.0, 0.0),
            "right": GimbalPosition(90.0, 0.0),
            "up": GimbalPosition(0.0, 20.0),
            "down": GimbalPosition(0.0, -20.0),
            "front_left": GimbalPosition(-45.0, 0.0),
            "front_right": GimbalPosition(45.0, 0.0),
            "back_left": GimbalPosition(-135.0, 0.0),
            "back_right": GimbalPosition(135.0, 0.0)
        }
        
        # 跟踪模式
        self.tracking_mode = False
        self.tracking_target = None
        
        # 连接管理
        self.active_clients: Dict[str, dict] = {}
        
        self._setup_routes()
        self._setup_socketio_handlers()
        
        # 启动位置更新线程
        self.position_update_thread = threading.Thread(target=self._position_update_loop, daemon=True)
        self.position_update_thread.start()
        
        logger.info("云台控制服务初始化完成")
    
    def _setup_routes(self):
        """设置HTTP路由"""
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                "status": "healthy",
                "service": "gimbal_control",
                "current_position": self.current_position.to_dict(),
                "is_moving": self.is_moving,
                "clients": len(self.active_clients)
            })
        
        @self.app.route('/position', methods=['GET'])
        def get_position():
            """获取当前云台位置"""
            return jsonify({
                "current": self.current_position.to_dict(),
                "target": self.target_position.to_dict(),
                "is_moving": self.is_moving
            })
        
        @self.app.route('/position', methods=['POST'])
        def set_position():
            """设置云台位置"""
            try:
                data = request.json
                pan = float(data.get('pan', self.current_position.pan))
                tilt = float(data.get('tilt', self.current_position.tilt))
                speed = int(data.get('speed', self.movement_speed))
                smoothness = int(data.get('smoothness', self.movement_smoothness))
                
                result = self.move_to_position(pan, tilt, speed, smoothness)
                
                if result['success']:
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                
            except Exception as e:
                logger.error(f"设置位置错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/move', methods=['POST'])
        def move_relative():
            """相对移动云台"""
            try:
                data = request.json
                pan_delta = float(data.get('pan_delta', 0.0))
                tilt_delta = float(data.get('tilt_delta', 0.0))
                speed = int(data.get('speed', self.movement_speed))
                
                new_pan = self.current_position.pan + pan_delta
                new_tilt = self.current_position.tilt + tilt_delta
                
                result = self.move_to_position(new_pan, new_tilt, speed)
                
                if result['success']:
                    return jsonify(result)
                else:
                    return jsonify(result), 400
                
            except Exception as e:
                logger.error(f"相对移动错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/preset/<preset_name>', methods=['POST'])
        def move_to_preset(preset_name):
            """移动到预设位置"""
            try:
                if preset_name not in self.preset_positions:
                    return jsonify({"error": f"未知预设位置: {preset_name}"}), 400
                
                position = self.preset_positions[preset_name]
                speed = request.json.get('speed', self.movement_speed) if request.json else self.movement_speed
                
                result = self.move_to_position(position.pan, position.tilt, speed)
                
                return jsonify({
                    "success": True,
                    "preset": preset_name,
                    "position": position.to_dict(),
                    **result
                })
                
            except Exception as e:
                logger.error(f"移动到预设位置错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/presets', methods=['GET'])
        def get_presets():
            """获取所有预设位置"""
            presets = {}
            for name, position in self.preset_positions.items():
                presets[name] = position.to_dict()
            return jsonify({"presets": presets})
        
        @self.app.route('/presets', methods=['POST'])
        def save_preset():
            """保存当前位置为预设"""
            try:
                data = request.json
                name = data.get('name', '')
                
                if not name:
                    return jsonify({"error": "预设名称不能为空"}), 400
                
                self.preset_positions[name] = GimbalPosition(
                    self.current_position.pan,
                    self.current_position.tilt
                )
                
                return jsonify({
                    "success": True,
                    "message": f"预设位置 '{name}' 已保存",
                    "position": self.current_position.to_dict()
                })
                
            except Exception as e:
                logger.error(f"保存预设错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/stop', methods=['POST'])
        def stop_movement():
            """停止云台移动"""
            try:
                self.stop_gimbal()
                return jsonify({
                    "success": True,
                    "message": "云台移动已停止",
                    "position": self.current_position.to_dict()
                })
                
            except Exception as e:
                logger.error(f"停止移动错误: {e}")
                return jsonify({"error": str(e)}), 500
        
        @self.app.route('/limits', methods=['GET'])
        def get_limits():
            """获取云台限制"""
            return jsonify({
                "pan_limits": self.pan_limits,
                "tilt_limits": self.tilt_limits,
                "max_speed": self.max_speed,
                "min_speed": self.min_speed
            })
        
        @self.app.route('/tracking', methods=['POST'])
        def set_tracking():
            """设置跟踪模式"""
            try:
                data = request.json
                enable = data.get('enable', False)
                
                if enable:
                    target_x = data.get('target_x', 0.5)  # 0-1之间的相对坐标
                    target_y = data.get('target_y', 0.5)
                    self.start_tracking(target_x, target_y)
                else:
                    self.stop_tracking()
                
                return jsonify({
                    "success": True,
                    "tracking": self.tracking_mode,
                    "target": self.tracking_target
                })
                
            except Exception as e:
                logger.error(f"设置跟踪错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/calibrate', methods=['POST'])
        def calibrate_gimbal():
            """校准云台"""
            try:
                # 云台校准流程
                logger.info("开始云台校准")

                # 移动到中心位置
                self.move_to_position(0, 0, self.movement_speed)
                time.sleep(2)

                # 测试各个方向
                test_positions = [
                    (90, 0), (-90, 0), (0, 20), (0, -20), (0, 0)
                ]

                for pan, tilt in test_positions:
                    self.move_to_position(pan, tilt, self.movement_speed)
                    time.sleep(1)

                return jsonify({
                    "success": True,
                    "message": "云台校准完成",
                    "position": self.current_position.to_dict()
                })

            except Exception as e:
                logger.error(f"云台校准错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/config', methods=['GET'])
        def get_gimbal_config():
            """获取云台配置"""
            return jsonify({
                "pan_limits": self.pan_limits,
                "tilt_limits": self.tilt_limits,
                "max_speed": self.max_speed,
                "min_speed": self.min_speed,
                "current_speed": self.movement_speed,
                "smoothness": self.movement_smoothness,
                "tracking_enabled": self.tracking_mode
            })

        @self.app.route('/config', methods=['POST'])
        def set_gimbal_config():
            """设置云台配置"""
            try:
                data = request.json

                # 更新速度设置
                if 'speed' in data:
                    speed = int(data['speed'])
                    self.movement_speed = max(self.min_speed, min(self.max_speed, speed))

                # 更新平滑度设置
                if 'smoothness' in data:
                    self.movement_smoothness = int(data['smoothness'])

                # 更新限制（小心使用）
                if 'pan_limits' in data:
                    self.pan_limits = tuple(data['pan_limits'])

                if 'tilt_limits' in data:
                    self.tilt_limits = tuple(data['tilt_limits'])

                return jsonify({
                    "success": True,
                    "config": {
                        "speed": self.movement_speed,
                        "smoothness": self.movement_smoothness,
                        "pan_limits": self.pan_limits,
                        "tilt_limits": self.tilt_limits
                    }
                })

            except Exception as e:
                logger.error(f"设置云台配置错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/scan', methods=['POST'])
        def start_scan():
            """开始扫描模式"""
            try:
                data = request.json
                scan_type = data.get('type', 'horizontal')  # horizontal, vertical, full
                speed = data.get('speed', self.movement_speed)
                range_percent = data.get('range', 0.8)  # 扫描范围百分比

                if scan_type == 'horizontal':
                    self._start_horizontal_scan(speed, range_percent)
                elif scan_type == 'vertical':
                    self._start_vertical_scan(speed, range_percent)
                elif scan_type == 'full':
                    self._start_full_scan(speed, range_percent)

                return jsonify({
                    "success": True,
                    "scan_type": scan_type,
                    "message": f"开始{scan_type}扫描"
                })

            except Exception as e:
                logger.error(f"启动扫描错误: {e}")
                return jsonify({"error": str(e)}), 500

        @self.app.route('/gesture', methods=['POST'])
        def gesture_control():
            """手势控制接口"""
            try:
                data = request.json
                gesture = data.get('gesture', '')

                gesture_map = {
                    'swipe_left': lambda: self.move_to_position(self.current_position.pan - 45, self.current_position.tilt),
                    'swipe_right': lambda: self.move_to_position(self.current_position.pan + 45, self.current_position.tilt),
                    'swipe_up': lambda: self.move_to_position(self.current_position.pan, self.current_position.tilt + 15),
                    'swipe_down': lambda: self.move_to_position(self.current_position.pan, self.current_position.tilt - 15),
                    'tap': lambda: self.move_to_position(0, 0),
                    'pinch': lambda: self.stop_gimbal(),
                    'double_tap': lambda: self._quick_scan()
                }

                if gesture in gesture_map:
                    gesture_map[gesture]()
                    return jsonify({
                        "success": True,
                        "gesture": gesture,
                        "message": f"执行手势: {gesture}"
                    })
                else:
                    return jsonify({"error": f"未知手势: {gesture}"}), 400

            except Exception as e:
                logger.error(f"手势控制错误: {e}")
                return jsonify({"error": str(e)}), 500
    
    def _setup_socketio_handlers(self):
        """设置SocketIO事件处理器"""
        
        @self.socketio.on('connect')
        def handle_connect():
            client_id = request.sid
            self.active_clients[client_id] = {
                'connected_time': time.time()
            }
            logger.info(f"云台控制客户端连接: {client_id}")
            emit('connected', {
                'client_id': client_id,
                'current_position': self.current_position.to_dict(),
                'presets': {name: pos.to_dict() for name, pos in self.preset_positions.items()}
            })
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            client_id = request.sid
            if client_id in self.active_clients:
                del self.active_clients[client_id]
            logger.info(f"云台控制客户端断开: {client_id}")
        
        @self.socketio.on('move_to')
        def handle_move_to(data):
            """处理移动到指定位置"""
            try:
                pan = float(data.get('pan', 0))
                tilt = float(data.get('tilt', 0))
                speed = int(data.get('speed', self.movement_speed))
                
                result = self.move_to_position(pan, tilt, speed)
                emit('move_result', result)
                
            except Exception as e:
                logger.error(f"处理移动命令错误: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('move_delta')
        def handle_move_delta(data):
            """处理相对移动"""
            try:
                pan_delta = float(data.get('pan_delta', 0))
                tilt_delta = float(data.get('tilt_delta', 0))
                speed = int(data.get('speed', self.movement_speed))
                
                new_pan = self.current_position.pan + pan_delta
                new_tilt = self.current_position.tilt + tilt_delta
                
                result = self.move_to_position(new_pan, new_tilt, speed)
                emit('move_result', result)
                
            except Exception as e:
                logger.error(f"处理相对移动错误: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('goto_preset')
        def handle_goto_preset(data):
            """处理前往预设位置"""
            try:
                preset_name = data.get('preset', '')
                
                if preset_name in self.preset_positions:
                    position = self.preset_positions[preset_name]
                    speed = int(data.get('speed', self.movement_speed))
                    
                    result = self.move_to_position(position.pan, position.tilt, speed)
                    emit('move_result', {
                        **result,
                        'preset': preset_name
                    })
                else:
                    emit('error', {'message': f'未知预设位置: {preset_name}'})
                
            except Exception as e:
                logger.error(f"处理预设位置错误: {e}")
                emit('error', {'message': str(e)})
        
        @self.socketio.on('stop')
        def handle_stop():
            """处理停止命令"""
            try:
                self.stop_gimbal()
                emit('stopped', {'position': self.current_position.to_dict()})
                
            except Exception as e:
                logger.error(f"处理停止命令错误: {e}")
                emit('error', {'message': str(e)})
    
    def move_to_position(self, pan: float, tilt: float, speed: int = None, smoothness: int = None) -> dict:
        """移动云台到指定位置"""
        try:
            # 应用角度限制
            pan = max(self.pan_limits[0], min(self.pan_limits[1], pan))
            tilt = max(self.tilt_limits[0], min(self.tilt_limits[1], tilt))
            
            # 应用速度限制
            if speed is None:
                speed = self.movement_speed
            speed = max(self.min_speed, min(self.max_speed, speed))
            
            if smoothness is None:
                smoothness = self.movement_smoothness
            
            # 设置目标位置
            self.target_position = GimbalPosition(pan, tilt)
            self.movement_speed = speed
            self.movement_smoothness = smoothness
            self.is_moving = True
            
            # 发送控制命令到基础控制器
            self.base_controller.gimbal_ctrl(pan, tilt, speed, smoothness)
            
            logger.info(f"移动云台到位置: {self.target_position}")
            
            # 广播位置变化
            self.socketio.emit('position_changed', {
                'current': self.current_position.to_dict(),
                'target': self.target_position.to_dict(),
                'is_moving': self.is_moving
            }, broadcast=True)
            
            return {
                "success": True,
                "message": "云台开始移动",
                "target_position": self.target_position.to_dict(),
                "speed": speed,
                "smoothness": smoothness
            }
            
        except Exception as e:
            logger.error(f"移动云台错误: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def stop_gimbal(self):
        """停止云台移动"""
        try:
            self.is_moving = False
            # 这里可以发送停止命令到基础控制器
            # self.base_controller.gimbal_stop()
            
            logger.info("云台移动已停止")
            
            # 广播停止事件
            self.socketio.emit('movement_stopped', {
                'position': self.current_position.to_dict()
            }, broadcast=True)
            
        except Exception as e:
            logger.error(f"停止云台错误: {e}")
    
    def start_tracking(self, target_x: float, target_y: float):
        """开始跟踪模式"""
        self.tracking_mode = True
        self.tracking_target = {'x': target_x, 'y': target_y}
        logger.info(f"开始跟踪目标: {self.tracking_target}")
    
    def stop_tracking(self):
        """停止跟踪模式"""
        self.tracking_mode = False
        self.tracking_target = None
        logger.info("停止跟踪模式")

    def _start_horizontal_scan(self, speed: int, range_percent: float):
        """开始水平扫描"""
        def scan():
            try:
                pan_range = (self.pan_limits[1] - self.pan_limits[0]) * range_percent
                left_limit = -pan_range / 2
                right_limit = pan_range / 2

                # 扫描循环
                for _ in range(3):  # 扫描3次
                    self.move_to_position(left_limit, self.current_position.tilt, speed)
                    time.sleep(2)
                    self.move_to_position(right_limit, self.current_position.tilt, speed)
                    time.sleep(2)

                # 回到中心
                self.move_to_position(0, self.current_position.tilt, speed)

            except Exception as e:
                logger.error(f"水平扫描错误: {e}")

        threading.Thread(target=scan, daemon=True).start()

    def _start_vertical_scan(self, speed: int, range_percent: float):
        """开始垂直扫描"""
        def scan():
            try:
                tilt_range = (self.tilt_limits[1] - self.tilt_limits[0]) * range_percent
                bottom_limit = -tilt_range / 2
                top_limit = tilt_range / 2

                # 扫描循环
                for _ in range(3):  # 扫描3次
                    self.move_to_position(self.current_position.pan, bottom_limit, speed)
                    time.sleep(2)
                    self.move_to_position(self.current_position.pan, top_limit, speed)
                    time.sleep(2)

                # 回到中心
                self.move_to_position(self.current_position.pan, 0, speed)

            except Exception as e:
                logger.error(f"垂直扫描错误: {e}")

        threading.Thread(target=scan, daemon=True).start()

    def _start_full_scan(self, speed: int, range_percent: float):
        """开始全方位扫描"""
        def scan():
            try:
                # 定义扫描点
                scan_points = [
                    (0, 0),      # 中心
                    (90, 0),     # 右
                    (90, 20),    # 右上
                    (0, 20),     # 上
                    (-90, 20),   # 左上
                    (-90, 0),    # 左
                    (-90, -20),  # 左下
                    (0, -20),    # 下
                    (90, -20),   # 右下
                    (0, 0)       # 回到中心
                ]

                for pan, tilt in scan_points:
                    # 应用范围限制
                    pan *= range_percent
                    tilt *= range_percent
                    self.move_to_position(pan, tilt, speed)
                    time.sleep(1.5)

            except Exception as e:
                logger.error(f"全方位扫描错误: {e}")

        threading.Thread(target=scan, daemon=True).start()

    def _quick_scan(self):
        """快速扫描"""
        self._start_horizontal_scan(self.max_speed, 0.5)
    
    def _position_update_loop(self):
        """位置更新循环"""
        while True:
            try:
                # 如果正在移动，更新当前位置
                if self.is_moving:
                    # 简单的插值更新（实际应该从硬件读取）
                    pan_diff = self.target_position.pan - self.current_position.pan
                    tilt_diff = self.target_position.tilt - self.current_position.tilt
                    
                    # 如果接近目标位置，停止移动
                    if abs(pan_diff) < 0.5 and abs(tilt_diff) < 0.5:
                        self.current_position = GimbalPosition(
                            self.target_position.pan,
                            self.target_position.tilt
                        )
                        self.is_moving = False
                        
                        # 广播到达目标位置
                        self.socketio.emit('position_reached', {
                            'position': self.current_position.to_dict()
                        }, broadcast=True)
                    else:
                        # 更新当前位置（简单插值）
                        speed_factor = 0.1  # 调整这个值来改变移动速度
                        self.current_position.pan += pan_diff * speed_factor
                        self.current_position.tilt += tilt_diff * speed_factor
                
                # 跟踪模式处理
                if self.tracking_mode and self.tracking_target:
                    # 这里可以添加目标跟踪逻辑
                    pass
                
                time.sleep(0.1)  # 100ms更新间隔
                
            except Exception as e:
                logger.error(f"位置更新循环错误: {e}")
                time.sleep(1)
    
    def start_service(self):
        """启动云台控制服务"""
        def run_service():
            logger.info(f"启动云台控制服务，端口: {self.port}")
            self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False)
        
        service_thread = threading.Thread(target=run_service, daemon=True)
        service_thread.start()
        return service_thread
    
    def stop_service(self):
        """停止云台控制服务"""
        # 停止移动
        self.stop_gimbal()
        
        # 清理客户端连接
        self.active_clients.clear()
        
        logger.info("云台控制服务已停止")


if __name__ == "__main__":
    # 测试代码
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(__file__)))
    
    from base_action.base_ctrl import BaseController
    
    # 创建测试实例
    base = BaseController('/dev/ttyAMA0', 115200)
    
    # 启动服务
    service = GimbalControlService(base, 8003)
    service.start_service()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        service.stop_service()