#!/usr/bin/env python3
"""
远程服务启动脚本
启动机器人的所有远程服务：视频聊天、语音聊天、云台控制
"""

import sys
import os
import time
import signal
import logging
import argparse

# 添加项目路径
curpath = os.path.realpath(__file__)
thisPath = os.path.dirname(curpath)
sys.path.append(thisPath)

# 导入必要的模块
from base_action.base_ctrl import BaseController
from base_action.cv_ctrl import OpencvFuncs
from services.remote_service_manager import RemoteServiceManager
import yaml

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('remote_services')

# 全局变量
service_manager = None


def signal_handler(signum, frame):
    """信号处理器 - 优雅退出"""
    logger.info("收到退出信号，正在停止服务...")
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
            for line in file:
                if 'Model' in line:
                    if 'Raspberry Pi' in line:
                        logger.info(f"检测到设备: {line.strip()}")
                        return True
        return False
    except:
        return False


def setup_base_controller():
    """设置基础控制器"""
    try:
        # 根据设备类型选择串口
        if check_raspberry_pi():
            # 树莓派5使用 /dev/ttyAMA0，其他使用 /dev/serial0
            try:
                with open('/proc/cpuinfo', 'r') as file:
                    content = file.read()
                    if 'Raspberry Pi 5' in content:
                        serial_port = '/dev/ttyAMA0'
                    else:
                        serial_port = '/dev/serial0'
            except:
                serial_port = '/dev/ttyAMA0'
            
            logger.info(f"使用串口: {serial_port}")
            base = BaseController(serial_port, 115200)
        else:
            logger.warning("非树莓派环境，使用模拟控制器")
            # 这里可以创建一个模拟的BaseController用于测试
            base = BaseController('/dev/null', 115200)
        
        return base
    except Exception as e:
        logger.error(f"设置基础控制器错误: {e}")
        return None


def setup_cv_controller(base_ctrl):
    """设置计算机视觉控制器"""
    try:
        cv_ctrl = OpencvFuncs(thisPath, base_ctrl)
        return cv_ctrl
    except Exception as e:
        logger.error(f"设置CV控制器错误: {e}")
        return None


def main():
    """主函数"""
    global service_manager
    
    # 解析命令行参数
    parser = argparse.ArgumentParser(description='机器人远程服务启动器')
    parser.add_argument('--port', type=int, default=9000, help='服务管理器端口')
    parser.add_argument('--auto-start', action='store_true', help='自动启动所有服务')
    parser.add_argument('--service', choices=['video', 'audio', 'gimbal'], 
                       help='只启动指定服务')
    args = parser.parse_args()
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("=" * 50)
    logger.info("机器人远程服务启动器")
    logger.info("=" * 50)
    
    # 加载配置
    config = load_config()
    if not config:
        logger.error("无法加载配置文件，退出")
        return 1
    
    # 设置基础控制器
    logger.info("初始化基础控制器...")
    base_ctrl = setup_base_controller()
    if not base_ctrl:
        logger.error("无法初始化基础控制器，退出")
        return 1
    
    # 设置CV控制器
    logger.info("初始化计算机视觉控制器...")
    cv_ctrl = setup_cv_controller(base_ctrl)
    if not cv_ctrl:
        logger.error("无法初始化CV控制器，退出")
        return 1
    
    # 创建服务管理器
    logger.info("创建远程服务管理器...")
    try:
        service_manager = RemoteServiceManager(base_ctrl, cv_ctrl, args.port)
        
        # 启动管理器
        logger.info(f"启动服务管理器，监听端口: {args.port}")
        manager_thread = service_manager.start_manager()
        
        # 等待管理器启动
        time.sleep(3)
        
        # 根据参数启动服务
        if args.auto_start:
            logger.info("自动启动所有服务...")
            service_manager.start_all_services()
        elif args.service:
            service_map = {
                'video': 'video_chat',
                'audio': 'audio_chat', 
                'gimbal': 'gimbal_control'
            }
            service_name = service_map[args.service]
            logger.info(f"启动服务: {service_name}")
            service_manager.start_service_by_name(service_name)
        
        logger.info("=" * 50)
        logger.info("远程服务已启动！")
        logger.info("=" * 50)
        logger.info("服务地址:")
        logger.info(f"  - 服务管理器: http://localhost:{args.port}")
        logger.info(f"  - 视频聊天:   http://localhost:8001")
        logger.info(f"  - 语音聊天:   http://localhost:8002")
        logger.info(f"  - 云台控制:   http://localhost:8003")
        logger.info("=" * 50)
        logger.info("按 Ctrl+C 停止所有服务")
        logger.info("=" * 50)
        
        # 保持运行
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            pass
            
    except Exception as e:
        logger.error(f"启动服务管理器错误: {e}")
        return 1
    
    finally:
        if service_manager:
            logger.info("正在停止服务...")
            service_manager.stop_manager()
        logger.info("所有服务已停止")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)