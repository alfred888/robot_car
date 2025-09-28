#!/usr/bin/env python3
"""
安全认证管理器 - 为远程服务提供安全认证和权限管理
支持JWT令牌、API密钥认证、设备绑定等安全机制
"""

import json
import logging
import time
import uuid
import hashlib
import hmac
import base64
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import jwt
from cryptography.fernet import Fernet
import secrets

logger = logging.getLogger('auth_manager')


class DeviceInfo:
    """设备信息类"""

    def __init__(self, device_id: str, device_name: str, device_type: str = "iOS"):
        self.device_id = device_id
        self.device_name = device_name
        self.device_type = device_type
        self.registered_time = time.time()
        self.last_seen = time.time()
        self.is_trusted = False
        self.permissions = []

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id,
            "device_name": self.device_name,
            "device_type": self.device_type,
            "registered_time": self.registered_time,
            "last_seen": self.last_seen,
            "is_trusted": self.is_trusted,
            "permissions": self.permissions
        }


class AuthSession:
    """认证会话类"""

    def __init__(self, session_id: str, device_id: str, user_id: str = "default"):
        self.session_id = session_id
        self.device_id = device_id
        self.user_id = user_id
        self.created_time = time.time()
        self.last_activity = time.time()
        self.permissions = []
        self.is_active = True
        self.access_count = 0

    def update_activity(self):
        """更新活动时间"""
        self.last_activity = time.time()
        self.access_count += 1

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "device_id": self.device_id,
            "user_id": self.user_id,
            "created_time": self.created_time,
            "last_activity": self.last_activity,
            "permissions": self.permissions,
            "is_active": self.is_active,
            "access_count": self.access_count
        }


class AuthManager:
    """安全认证管理器"""

    def __init__(self, config_file: str = None):
        # JWT配置
        self.jwt_secret = secrets.token_urlsafe(32)
        self.jwt_algorithm = 'HS256'
        self.jwt_expiry_hours = 24

        # 加密配置
        self.encryption_key = Fernet.generate_key()
        self.cipher_suite = Fernet(self.encryption_key)

        # 会话管理
        self.active_sessions: Dict[str, AuthSession] = {}
        self.registered_devices: Dict[str, DeviceInfo] = {}
        self.session_timeout = 1800  # 30分钟

        # API密钥管理
        self.api_keys: Dict[str, dict] = {
            'ios_app_v1': {
                'key': 'ios_secure_key_2024',
                'permissions': ['video', 'audio', 'gimbal', 'system'],
                'rate_limit': 1000,  # 每小时请求数
                'is_active': True
            },
            'test_client': {
                'key': 'test_key_dev_2024',
                'permissions': ['video', 'audio'],
                'rate_limit': 100,
                'is_active': True
            }
        }

        # 权限定义
        self.permission_definitions = {
            'video': {
                'name': '视频控制',
                'description': '访问视频流、拍照、录像功能',
                'endpoints': ['/video/*']
            },
            'audio': {
                'name': '音频控制',
                'description': '语音识别、语音合成功能',
                'endpoints': ['/audio/*']
            },
            'gimbal': {
                'name': '云台控制',
                'description': '云台旋转、预设位置控制',
                'endpoints': ['/gimbal/*']
            },
            'system': {
                'name': '系统管理',
                'description': '系统状态、服务管理功能',
                'endpoints': ['/robot/*', '/services/*']
            }
        }

        # 访问日志
        self.access_logs: List[dict] = []
        self.max_log_entries = 1000

        # 安全配置
        self.max_login_attempts = 5
        self.login_attempt_window = 300  # 5分钟
        self.failed_attempts: Dict[str, list] = {}

        logger.info("安全认证管理器初始化完成")

    def generate_jwt_token(self, device_id: str, user_id: str = "default",
                          permissions: List[str] = None) -> str:
        """生成JWT令牌"""
        try:
            payload = {
                'device_id': device_id,
                'user_id': user_id,
                'permissions': permissions or [],
                'issued_at': time.time(),
                'expires_at': time.time() + (self.jwt_expiry_hours * 3600)
            }

            token = jwt.encode(payload, self.jwt_secret, algorithm=self.jwt_algorithm)
            logger.info(f"为设备 {device_id} 生成JWT令牌")
            return token

        except Exception as e:
            logger.error(f"生成JWT令牌错误: {e}")
            raise

    def verify_jwt_token(self, token: str) -> Optional[dict]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=[self.jwt_algorithm])

            # 检查过期时间
            if payload.get('expires_at', 0) < time.time():
                logger.warning("JWT令牌已过期")
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("JWT令牌已过期")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"无效的JWT令牌: {e}")
            return None
        except Exception as e:
            logger.error(f"验证JWT令牌错误: {e}")
            return None

    def authenticate_api_key(self, app_id: str, api_key: str) -> Tuple[bool, dict]:
        """API密钥认证"""
        try:
            if app_id not in self.api_keys:
                return False, {"error": "无效的应用ID"}

            app_config = self.api_keys[app_id]

            if not app_config.get('is_active', True):
                return False, {"error": "应用已被禁用"}

            if app_config['key'] != api_key:
                return False, {"error": "API密钥错误"}

            return True, {
                "app_id": app_id,
                "permissions": app_config['permissions'],
                "rate_limit": app_config['rate_limit']
            }

        except Exception as e:
            logger.error(f"API密钥认证错误: {e}")
            return False, {"error": str(e)}

    def register_device(self, device_id: str, device_name: str,
                       device_type: str = "iOS") -> bool:
        """注册设备"""
        try:
            if device_id in self.registered_devices:
                # 更新现有设备信息
                device = self.registered_devices[device_id]
                device.device_name = device_name
                device.device_type = device_type
                device.last_seen = time.time()
            else:
                # 注册新设备
                device = DeviceInfo(device_id, device_name, device_type)
                self.registered_devices[device_id] = device

            logger.info(f"设备注册成功: {device_id} ({device_name})")
            return True

        except Exception as e:
            logger.error(f"设备注册错误: {e}")
            return False

    def create_session(self, device_id: str, user_id: str = "default",
                      permissions: List[str] = None) -> Optional[AuthSession]:
        """创建认证会话"""
        try:
            # 检查设备是否已注册
            if device_id not in self.registered_devices:
                logger.warning(f"尝试为未注册设备创建会话: {device_id}")
                return None

            # 生成会话ID
            session_id = str(uuid.uuid4())

            # 创建会话
            session = AuthSession(session_id, device_id, user_id)
            session.permissions = permissions or []

            self.active_sessions[session_id] = session

            # 更新设备最后见时间
            self.registered_devices[device_id].last_seen = time.time()

            logger.info(f"创建会话: {session_id} (设备: {device_id})")
            return session

        except Exception as e:
            logger.error(f"创建会话错误: {e}")
            return None

    def validate_session(self, session_id: str) -> Optional[AuthSession]:
        """验证会话"""
        try:
            if session_id not in self.active_sessions:
                return None

            session = self.active_sessions[session_id]

            # 检查会话是否过期
            if time.time() - session.last_activity > self.session_timeout:
                self.destroy_session(session_id)
                logger.info(f"会话已过期: {session_id}")
                return None

            # 检查会话是否活跃
            if not session.is_active:
                return None

            # 更新活动时间
            session.update_activity()
            return session

        except Exception as e:
            logger.error(f"验证会话错误: {e}")
            return None

    def destroy_session(self, session_id: str) -> bool:
        """销毁会话"""
        try:
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
                logger.info(f"销毁会话: {session_id}")
                return True
            return False

        except Exception as e:
            logger.error(f"销毁会话错误: {e}")
            return False

    def check_permission(self, session_id: str, permission: str) -> bool:
        """检查权限"""
        try:
            session = self.validate_session(session_id)
            if not session:
                return False

            return permission in session.permissions

        except Exception as e:
            logger.error(f"检查权限错误: {e}")
            return False

    def check_endpoint_permission(self, session_id: str, endpoint: str) -> bool:
        """检查端点权限"""
        try:
            session = self.validate_session(session_id)
            if not session:
                return False

            # 检查每个权限是否匹配端点
            for permission in session.permissions:
                if permission in self.permission_definitions:
                    endpoints = self.permission_definitions[permission]['endpoints']
                    for pattern in endpoints:
                        if self._match_endpoint_pattern(endpoint, pattern):
                            return True

            return False

        except Exception as e:
            logger.error(f"检查端点权限错误: {e}")
            return False

    def _match_endpoint_pattern(self, endpoint: str, pattern: str) -> bool:
        """匹配端点模式"""
        if pattern.endswith('/*'):
            prefix = pattern[:-2]
            return endpoint.startswith(prefix)
        return endpoint == pattern

    def log_access(self, session_id: str, endpoint: str, method: str,
                  status_code: int, ip_address: str = "unknown"):
        """记录访问日志"""
        try:
            log_entry = {
                'timestamp': time.time(),
                'session_id': session_id,
                'endpoint': endpoint,
                'method': method,
                'status_code': status_code,
                'ip_address': ip_address
            }

            self.access_logs.append(log_entry)

            # 限制日志条目数量
            if len(self.access_logs) > self.max_log_entries:
                self.access_logs = self.access_logs[-self.max_log_entries:]

        except Exception as e:
            logger.error(f"记录访问日志错误: {e}")

    def check_rate_limit(self, app_id: str) -> bool:
        """检查访问频率限制"""
        try:
            if app_id not in self.api_keys:
                return False

            rate_limit = self.api_keys[app_id]['rate_limit']
            current_time = time.time()
            one_hour_ago = current_time - 3600

            # 统计最近一小时的访问次数
            recent_accesses = [
                log for log in self.access_logs
                if log['timestamp'] > one_hour_ago and
                   log.get('app_id') == app_id
            ]

            return len(recent_accesses) < rate_limit

        except Exception as e:
            logger.error(f"检查访问频率限制错误: {e}")
            return False

    def check_failed_attempts(self, identifier: str) -> bool:
        """检查失败尝试次数"""
        try:
            current_time = time.time()

            if identifier not in self.failed_attempts:
                return True

            # 清理过期的失败尝试记录
            self.failed_attempts[identifier] = [
                attempt_time for attempt_time in self.failed_attempts[identifier]
                if current_time - attempt_time < self.login_attempt_window
            ]

            return len(self.failed_attempts[identifier]) < self.max_login_attempts

        except Exception as e:
            logger.error(f"检查失败尝试次数错误: {e}")
            return True

    def record_failed_attempt(self, identifier: str):
        """记录失败尝试"""
        try:
            if identifier not in self.failed_attempts:
                self.failed_attempts[identifier] = []

            self.failed_attempts[identifier].append(time.time())

        except Exception as e:
            logger.error(f"记录失败尝试错误: {e}")

    def clear_failed_attempts(self, identifier: str):
        """清除失败尝试记录"""
        try:
            if identifier in self.failed_attempts:
                del self.failed_attempts[identifier]

        except Exception as e:
            logger.error(f"清除失败尝试记录错误: {e}")

    def encrypt_data(self, data: str) -> str:
        """加密数据"""
        try:
            encrypted_data = self.cipher_suite.encrypt(data.encode())
            return base64.b64encode(encrypted_data).decode()

        except Exception as e:
            logger.error(f"加密数据错误: {e}")
            raise

    def decrypt_data(self, encrypted_data: str) -> str:
        """解密数据"""
        try:
            encrypted_bytes = base64.b64decode(encrypted_data.encode())
            decrypted_data = self.cipher_suite.decrypt(encrypted_bytes)
            return decrypted_data.decode()

        except Exception as e:
            logger.error(f"解密数据错误: {e}")
            raise

    def generate_secure_token(self, length: int = 32) -> str:
        """生成安全令牌"""
        return secrets.token_urlsafe(length)

    def verify_signature(self, data: str, signature: str, secret: str) -> bool:
        """验证签名"""
        try:
            expected_signature = hmac.new(
                secret.encode(),
                data.encode(),
                hashlib.sha256
            ).hexdigest()

            return hmac.compare_digest(signature, expected_signature)

        except Exception as e:
            logger.error(f"验证签名错误: {e}")
            return False

    def get_session_info(self, session_id: str) -> Optional[dict]:
        """获取会话信息"""
        session = self.validate_session(session_id)
        return session.to_dict() if session else None

    def get_device_info(self, device_id: str) -> Optional[dict]:
        """获取设备信息"""
        device = self.registered_devices.get(device_id)
        return device.to_dict() if device else None

    def get_all_sessions(self) -> List[dict]:
        """获取所有活跃会话"""
        return [session.to_dict() for session in self.active_sessions.values()]

    def get_all_devices(self) -> List[dict]:
        """获取所有注册设备"""
        return [device.to_dict() for device in self.registered_devices.values()]

    def cleanup_expired_sessions(self):
        """清理过期会话"""
        try:
            current_time = time.time()
            expired_sessions = []

            for session_id, session in self.active_sessions.items():
                if current_time - session.last_activity > self.session_timeout:
                    expired_sessions.append(session_id)

            for session_id in expired_sessions:
                self.destroy_session(session_id)

            if expired_sessions:
                logger.info(f"清理了 {len(expired_sessions)} 个过期会话")

        except Exception as e:
            logger.error(f"清理过期会话错误: {e}")

    def get_stats(self) -> dict:
        """获取统计信息"""
        try:
            current_time = time.time()

            # 计算活跃会话数
            active_sessions = len(self.active_sessions)

            # 计算最近一小时的访问次数
            one_hour_ago = current_time - 3600
            recent_accesses = len([
                log for log in self.access_logs
                if log['timestamp'] > one_hour_ago
            ])

            # 计算注册设备数
            total_devices = len(self.registered_devices)
            trusted_devices = len([
                device for device in self.registered_devices.values()
                if device.is_trusted
            ])

            return {
                "active_sessions": active_sessions,
                "total_devices": total_devices,
                "trusted_devices": trusted_devices,
                "recent_accesses": recent_accesses,
                "total_logs": len(self.access_logs),
                "failed_attempts": len(self.failed_attempts)
            }

        except Exception as e:
            logger.error(f"获取统计信息错误: {e}")
            return {}


if __name__ == "__main__":
    # 测试代码
    auth_manager = AuthManager()

    # 测试设备注册
    device_id = "test_ios_device_001"
    auth_manager.register_device(device_id, "Test iPhone", "iOS")

    # 测试会话创建
    session = auth_manager.create_session(device_id, "test_user", ["video", "audio"])

    if session:
        print(f"会话创建成功: {session.session_id}")

        # 测试权限检查
        print(f"视频权限: {auth_manager.check_permission(session.session_id, 'video')}")
        print(f"系统权限: {auth_manager.check_permission(session.session_id, 'system')}")

        # 测试端点权限
        print(f"视频端点权限: {auth_manager.check_endpoint_permission(session.session_id, '/video/stream')}")

        # 测试统计信息
        stats = auth_manager.get_stats()
        print(f"统计信息: {stats}")