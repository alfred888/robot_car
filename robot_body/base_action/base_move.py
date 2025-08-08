import serial
import json
import time
import logging
import yaml
import os

# 设置日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 输出到控制台
        logging.FileHandler('move_controller.log')  # 输出到文件
    ]
)

# 获取logger
logger = logging.getLogger('body')

# 获取当前文件路径
curpath = os.path.realpath(__file__)
thisPath = os.path.dirname(curpath)

# 加载配置文件
with open(thisPath + '/../config/config.yaml', 'r') as yaml_file:
    f = yaml.safe_load(yaml_file)

class Move:
    """移动控制器类，提供小车移动功能"""
    
    def __init__(self, uart_dev_set, buad_set):
        """初始化移动控制器
        Args:
            uart_dev_set: 串口设备名
            buad_set: 波特率
        """
        logger.info(f"初始化Move控制器,串口:{uart_dev_set},波特率:{buad_set}")
        self.ser = serial.Serial(uart_dev_set, buad_set, timeout=1)
        
        # 获取速度配置
        self.max_speed = f['args_config']['max_speed']
        self.slow_speed = f['args_config']['slow_speed']
        self.speed_rate = 1.0  # 默认速度倍率
        
        logger.info(f"速度配置 - max_speed: {self.max_speed}, slow_speed: {self.slow_speed}")
        logger.info("移动控制器初始化完成")
    
    def send_command(self, data):
        """发送命令到串口
        Args:
            data: 要发送的数据字典
        """
        try:
            command = json.dumps(data) + '\n'
            self.ser.write(command.encode("utf-8"))
            logger.debug(f"发送移动命令: {data}")
        except Exception as e:
            logger.error(f"发送移动命令失败: {e}")
    
    def set_speed_rate(self, rate):
        """设置速度倍率
        Args:
            rate: 速度倍率 (0.0-1.0)
        """
        if 0.0 <= rate <= 1.0:
            self.speed_rate = rate
            logger.info(f"设置速度倍率为: {rate}")
            return True
        else:
            logger.error(f"速度倍率无效: {rate}, 应在0.0-1.0范围内")
            return False
    
    def _calculate_speed(self, base_speed):
        """计算实际速度值
        Args:
            base_speed: 基础速度值
        Returns:
            int: 计算后的速度值
        """
        # 使用与页面相同的方式：直接使用原始值，然后乘以speed_rate
        return int(base_speed * self.speed_rate)
    
    def move_forward(self, duration=2):
        """前进
        Args:
            duration: 持续时间(秒)
        """
        logger.info(f"前进 - 持续时间: {duration}秒")
        speed = self._calculate_speed(self.max_speed)
        logger.info(f"前进速度: {speed}")
        
        self.send_command({"T": 1, "L": speed, "R": speed})
        time.sleep(duration)
        self.stop()
    
    def move_backward(self, duration=2):
        """后退
        Args:
            duration: 持续时间(秒)
        """
        logger.info(f"后退 - 持续时间: {duration}秒")
        speed = self._calculate_speed(self.max_speed)
        logger.info(f"后退速度: {speed}")
        
        self.send_command({"T": 1, "L": -speed, "R": -speed})
        time.sleep(duration)
        self.stop()
    
    def turn_left(self, duration=2):
        """左转
        Args:
            duration: 持续时间(秒)
        """
        logger.info(f"左转 - 持续时间: {duration}秒")
        speed = self._calculate_speed(self.max_speed)
        logger.info(f"左转速度: 左轮{-speed}, 右轮{speed}")
        
        self.send_command({"T": 1, "L": -speed, "R": speed})
        time.sleep(duration)
        self.stop()
    
    def turn_right(self, duration=2):
        """右转
        Args:
            duration: 持续时间(秒)
        """
        logger.info(f"右转 - 持续时间: {duration}秒")
        speed = self._calculate_speed(self.max_speed)
        logger.info(f"右转速度: 左轮{speed}, 右轮{-speed}")
        
        self.send_command({"T": 1, "L": speed, "R": -speed})
        time.sleep(duration)
        self.stop()
    
    def move_forward_slow(self, duration=2):
        """慢速前进
        Args:
            duration: 持续时间(秒)
        """
        logger.info(f"慢速前进 - 持续时间: {duration}秒")
        speed = self._calculate_speed(self.slow_speed)
        logger.info(f"慢速前进速度: {speed}")
        
        self.send_command({"T": 1, "L": speed, "R": speed})
        time.sleep(duration)
        self.stop()
    
    def move_backward_slow(self, duration=2):
        """慢速后退
        Args:
            duration: 持续时间(秒)
        """
        logger.info(f"慢速后退 - 持续时间: {duration}秒")
        speed = self._calculate_speed(self.slow_speed)
        logger.info(f"慢速后退速度: {speed}")
        
        self.send_command({"T": 1, "L": -speed, "R": -speed})
        time.sleep(duration)
        self.stop()
    
    def stop(self):
        """停止移动"""
        logger.info("停止移动")
        self.send_command({"T": 1, "L": 0, "R": 0})
    
    def set_speed(self, left_speed, right_speed):
        """设置左右轮速度
        Args:
            left_speed: 左轮速度 (-100到100)
            right_speed: 右轮速度 (-100到100)
        """
        if -100 <= left_speed <= 100 and -100 <= right_speed <= 100:
            logger.info(f"设置速度 - 左轮: {left_speed}, 右轮: {right_speed}")
            self.send_command({"T": 1, "L": left_speed, "R": right_speed})
            return True
        else:
            logger.error(f"速度值无效: 左轮{left_speed}, 右轮{right_speed}, 应在-100到100范围内")
            return False
    
    def get_status(self):
        """获取当前状态
        Returns:
            dict: 包含速度配置和倍率的字典
        """
        status = {
            'max_speed': self.max_speed,
            'slow_speed': self.slow_speed,
            'speed_rate': self.speed_rate,
            'calculated_max_speed': self._calculate_speed(self.max_speed),
            'calculated_slow_speed': self._calculate_speed(self.slow_speed)
        }
        logger.debug(f"当前状态: {status}")
        return status
    
    def close(self):
        """关闭串口连接"""
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
            logger.info("移动控制器串口已关闭")


def test_move_controller():
    """测试移动控制器功能"""
    logger.info("=== 开始测试移动控制器 ===")
    
    try:
        # 初始化移动控制器
        move_ctrl = Move('/dev/ttyAMA0', 115200)
        
        # 测试1: 获取状态
        logger.info("测试1: 获取状态")
        status = move_ctrl.get_status()
        logger.info(f"初始状态: {status}")
        
        # 测试2: 前进
        logger.info("测试2: 前进")
        move_ctrl.move_forward(3)
        time.sleep(1)
        
        # 测试3: 后退
        logger.info("测试3: 后退")
        move_ctrl.move_backward(3)
        time.sleep(1)
        
        # 测试4: 左转
        logger.info("测试4: 左转")
        move_ctrl.turn_left(2)
        time.sleep(1)
        
        # 测试5: 右转
        logger.info("测试5: 右转")
        move_ctrl.turn_right(2)
        time.sleep(1)
        
        # 测试6: 慢速前进
        logger.info("测试6: 慢速前进")
        move_ctrl.move_forward_slow(3)
        time.sleep(1)
        
        # 测试7: 慢速后退
        logger.info("测试7: 慢速后退")
        move_ctrl.move_backward_slow(3)
        time.sleep(1)
        
        # 测试8: 设置速度倍率
        logger.info("测试8: 设置速度倍率")
        move_ctrl.set_speed_rate(0.5)
        move_ctrl.move_forward(2)
        time.sleep(1)
        
        # 测试9: 自定义速度
        logger.info("测试9: 自定义速度")
        move_ctrl.set_speed(50, 30)
        time.sleep(2)
        move_ctrl.stop()
        
        # 测试10: 最终状态
        logger.info("测试10: 最终状态")
        final_status = move_ctrl.get_status()
        logger.info(f"最终状态: {final_status}")
        
        # 关闭连接
        move_ctrl.close()
        
        logger.info("=== 移动控制器测试完成 ===")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")


if __name__ == '__main__':
    # 运行测试
    test_move_controller()
