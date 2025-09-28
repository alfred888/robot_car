#!/usr/bin/env python3
"""
统一远程服务启动脚本
启动所有远程服务，包括统一API、视频聊天、音频聊天、云台控制等
"""

import sys
import os
import time
import signal
import logging
import argparse
import threading

# 添加项目路径
curpath = os.path.realpath(__file__)
thisPath = os.path.dirname(curpath)
sys.path.append(thisPath)

# 导入必要的模块
from base_action.base_ctrl import BaseController
from base_action.cv_ctrl import OpencvFuncs
from services.unified_api import UnifiedRemoteAPI
from services.remote_service_manager import RemoteServiceManager
import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('unified_remote_services')

# 全局变量
unified_api = None
service_manager = None
base_controller = None
cv_controller = None


def signal_handler(signum, frame):
    """信号处理器 - 优雅退出"""
    logger.info("收到退出信号，正在停止所有服务...")

    if unified_api:
        unified_api.stop_service()

    if service_manager:
        service_manager.stop_manager()

    sys.exit(0)


def load_config():
    """加载配置文件"""
    try:
        config_path = os.path.join(thisPath, 'config', 'config.yaml')
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"加载配置文件错误: {e}")
        return None


def check_raspberry_pi():
    """检查是否为树莓派"""
    try:
        with open('/proc/cpuinfo', 'r') as file:
            content = file.read()
            if 'Raspberry Pi' in content:
                logger.info("检测到树莓派设备")
                return 'Raspberry Pi 5' in content
        return None
    except:
        return None


def setup_base_controller():
    """设置基础控制器"""
    global base_controller

    try:
        # 根据设备类型选择串口
        pi_version = check_raspberry_pi()
        if pi_version is not None:
            if pi_version:  # 树莓派5
                serial_port = '/dev/ttyAMA0'
            else:  # 其他树莓派
                serial_port = '/dev/serial0'

            logger.info(f"使用串口: {serial_port}")
            base_controller = BaseController(serial_port, 115200)
        else:
            logger.warning("非树莓派环境，使用模拟控制器")
            # 创建一个模拟的BaseController用于测试
            base_controller = None

        return base_controller

    except Exception as e:
        logger.error(f"设置基础控制器错误: {e}")
        return None


def setup_cv_controller():
    """设置计算机视觉控制器"""
    global cv_controller

    try:
        if base_controller:
            cv_controller = OpencvFuncs(thisPath, base_controller)
            return cv_controller
        else:
            logger.warning("基础控制器未就绪，跳过CV控制器初始化")
            return None
    except Exception as e:
        logger.error(f"设置CV控制器错误: {e}")
        return None


def start_services(args):
    """启动所有服务"""
    global unified_api, service_manager

    try:
        # 1. 启动统一API服务
        logger.info("启动统一远程API服务...")
        unified_api = UnifiedRemoteAPI(args.api_port)
        api_thread = unified_api.start_service()
        time.sleep(2)

        # 2. 启动服务管理器
        if args.enable_manager:
            logger.info("启动服务管理器...")
            service_manager = RemoteServiceManager(base_controller, cv_controller, args.manager_port)
            manager_thread = service_manager.start_manager()
            time.sleep(3)

            # 3. 自动启动所有子服务
            if args.auto_start_services:
                logger.info("自动启动所有子服务...")
                service_manager.start_all_services()

        return True

    except Exception as e:
        logger.error(f"启动服务错误: {e}")
        return False


def print_service_info(args):
    """打印服务信息"""
    logger.info("=" * 60)
    logger.info("🤖 机器人统一远程服务已启动！")
    logger.info("=" * 60)
    logger.info("📱 iOS App 连接信息:")
    logger.info(f"   统一API地址: http://localhost:{args.api_port}")

    if args.enable_manager:
        logger.info(f"   服务管理器: http://localhost:{args.manager_port}")
        logger.info("")
        logger.info("🔧 各独立服务地址:")
        logger.info("   视频聊天服务: http://localhost:8001")
        logger.info("   音频聊天服务: http://localhost:8002")
        logger.info("   云台控制服务: http://localhost:8003")

    logger.info("")
    logger.info("🔑 认证信息:")
    logger.info("   iOS App ID: ios_app_v1")
    logger.info("   API Key: ios_secure_key_2024")
    logger.info("   测试客户端 ID: test_client")
    logger.info("   测试 API Key: test_key_dev_2024")
    logger.info("")
    logger.info("📚 API文档:")
    logger.info("   登录: POST /auth/login")
    logger.info("   视频: GET/POST /video/*")
    logger.info("   音频: GET/POST /audio/*")
    logger.info("   云台: GET/POST /gimbal/*")
    logger.info("   系统: GET /robot/status")
    logger.info("")
    logger.info("🛡️ 安全特性:")
    logger.info("   ✅ JWT令牌认证")
    logger.info("   ✅ API密钥验证")
    logger.info("   ✅ 设备注册管理")
    logger.info("   ✅ 会话管理")
    logger.info("   ✅ 访问频率限制")
    logger.info("   ✅ 访问日志记录")
    logger.info("=" * 60)
    logger.info("按 Ctrl+C 停止所有服务")
    logger.info("=" * 60)


def monitor_services():
    """监控服务状态"""
    while True:
        try:
            # 定期清理过期会话
            if unified_api and unified_api.auth_manager:
                unified_api.auth_manager.cleanup_expired_sessions()

            time.sleep(300)  # 每5分钟检查一次

        except Exception as e:
            logger.error(f"服务监控错误: {e}")
            time.sleep(60)


def main():
    """主函数"""
    global unified_api, service_manager, base_controller, cv_controller

    # 解析命令行参数
    parser = argparse.ArgumentParser(description='机器人统一远程服务启动器')
    parser.add_argument('--api-port', type=int, default=8000, help='统一API端口')
    parser.add_argument('--manager-port', type=int, default=9000, help='服务管理器端口')
    parser.add_argument('--enable-manager', action='store_true', help='启用服务管理器')
    parser.add_argument('--auto-start-services', action='store_true', help='自动启动所有子服务')
    parser.add_argument('--config', type=str, help='配置文件路径')
    args = parser.parse_args()

    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("🚀 启动机器人统一远程服务...")

    # 加载配置
    config = load_config()
    if not config:
        logger.warning("未能加载配置文件，使用默认配置")

    # 设置基础控制器
    logger.info("初始化基础控制器...")
    base_controller = setup_base_controller()

    # 设置CV控制器
    if base_controller:
        logger.info("初始化计算机视觉控制器...")
        cv_controller = setup_cv_controller()
    else:
        logger.warning("跳过CV控制器初始化")

    # 启动服务
    if start_services(args):
        # 启动监控线程
        monitor_thread = threading.Thread(target=monitor_services, daemon=True)
        monitor_thread.start()

        # 打印服务信息
        print_service_info(args)

        # 保持运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
    else:
        logger.error("服务启动失败")
        return 1

    # 清理资源
    logger.info("正在停止服务...")
    if unified_api:
        unified_api.stop_service()
    if service_manager:
        service_manager.stop_manager()

    logger.info("所有服务已停止")
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)