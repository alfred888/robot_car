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
        logging.FileHandler('light_controller.log')  # 输出到文件
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

class LightController:
    """灯光控制器类，提供灯光控制功能"""
    
    def __init__(self, uart_dev_set, buad_set):
        """初始化灯光控制器
        Args:
            uart_dev_set: 串口设备名
            buad_set: 波特率
        """
        logger.info(f"初始化LightController,串口:{uart_dev_set},波特率:{buad_set}")
        self.ser = serial.Serial(uart_dev_set, buad_set, timeout=1)
        
        # 灯光状态
        self.base_light_status = 0
        self.head_light_status = 0
        
        logger.info("灯光控制器初始化完成")
    
    def send_command(self, data):
        """发送命令到串口
        Args:
            data: 要发送的数据字典
        """
        try:
            command = json.dumps(data) + '\n'
            self.ser.write(command.encode("utf-8"))
            logger.debug(f"发送灯光命令: {data}")
        except Exception as e:
            logger.error(f"发送灯光命令失败: {e}")
    
    def lights_ctrl(self, pwmA, pwmB):
        """控制灯光
        Args:
            pwmA: 基础灯光PWM值 (0-255)
            pwmB: 头部灯光PWM值 (0-255)
        """
        data = {"T": 132, "IO4": pwmA, "IO5": pwmB}
        self.send_command(data)
        self.base_light_status = pwmA
        self.head_light_status = pwmB
        logger.info(f"灯光控制 - 基础灯:{pwmA}, 头部灯:{pwmB}")
    
    def turn_on(self):
        """打开所有灯光"""
        logger.info("打开所有灯光")
        self.lights_ctrl(255, 255)
        return True
    
    def turn_off(self):
        """关闭所有灯光"""
        logger.info("关闭所有灯光")
        self.lights_ctrl(0, 0)
        return True
    
    def turn_on_base_light(self):
        """只打开基础灯光"""
        logger.info("打开基础灯光")
        self.lights_ctrl(255, self.head_light_status)
        return True
    
    def turn_off_base_light(self):
        """只关闭基础灯光"""
        logger.info("关闭基础灯光")
        self.lights_ctrl(0, self.head_light_status)
        return True
    
    def turn_on_head_light(self):
        """只打开头部灯光"""
        logger.info("打开头部灯光")
        self.lights_ctrl(self.base_light_status, 255)
        return True
    
    def turn_off_head_light(self):
        """只关闭头部灯光"""
        logger.info("关闭头部灯光")
        self.lights_ctrl(self.base_light_status, 0)
        return True
    
    def set_brightness(self, brightness):
        """设置灯光亮度
        Args:
            brightness: 亮度值 (0-255)
        """
        if 0 <= brightness <= 255:
            logger.info(f"设置灯光亮度为: {brightness}")
            self.lights_ctrl(brightness, brightness)
            return True
        else:
            logger.error(f"亮度值无效: {brightness}, 应在0-255范围内")
            return False
    
    def breath_light(self, duration=15):
        """呼吸灯效果
        Args:
            duration: 持续时间(秒)
        """
        logger.info(f"启动呼吸灯效果，持续时间: {duration}秒")
        start_time = time.time()
        
        try:
            while time.time() - start_time < duration:
                # 渐亮
                for i in range(0, 128, 10):
                    self.lights_ctrl(i, 128-i)
                    time.sleep(0.1)
                # 渐暗
                for i in range(0, 128, 10):
                    self.lights_ctrl(128-i, i)
                    time.sleep(0.1)
        except KeyboardInterrupt:
            logger.info("呼吸灯被用户中断")
        
        # 呼吸灯结束后关闭
        self.turn_off()
        logger.info("呼吸灯效果结束")
    
    def stop_breath_light(self):
        """停止呼吸灯效果"""
        logger.info("停止呼吸灯效果")
        self.turn_off()
        return True
    
    def get_status(self):
        """获取当前灯光状态
        Returns:
            dict: 包含基础灯和头部灯状态的字典
        """
        status = {
            'base_light': self.base_light_status,
            'head_light': self.head_light_status,
            'base_light_on': self.base_light_status > 0,
            'head_light_on': self.head_light_status > 0
        }
        logger.debug(f"当前灯光状态: {status}")
        return status
    
    def close(self):
        """关闭串口连接"""
        if hasattr(self, 'ser') and self.ser.is_open:
            self.ser.close()
            logger.info("灯光控制器串口已关闭")


def test_light_controller():
    """测试灯光控制器功能"""
    logger.info("=== 开始测试灯光控制器 ===")
    
    try:
        # 初始化灯光控制器
        light_ctrl = LightController('/dev/ttyAMA0', 115200)
        
        # 测试1: 获取初始状态
        logger.info("测试1: 获取初始状态")
        status = light_ctrl.get_status()
        logger.info(f"初始状态: {status}")
        
        # 测试2: 打开所有灯光
        logger.info("测试2: 打开所有灯光")
        light_ctrl.turn_on()
        time.sleep(2)
        
        # 测试3: 设置不同亮度
        logger.info("测试3: 测试不同亮度")
        for brightness in [50, 100, 150, 200, 255]:
            light_ctrl.set_brightness(brightness)
            time.sleep(0.5)
        
        # 测试4: 关闭所有灯光
        logger.info("测试4: 关闭所有灯光")
        light_ctrl.turn_off()
        time.sleep(1)
        
        # 测试5: 测试单独控制
        logger.info("测试5: 测试单独控制")
        light_ctrl.turn_on_base_light()
        time.sleep(1)
        light_ctrl.turn_off_base_light()
        time.sleep(1)
        
        light_ctrl.turn_on_head_light()
        time.sleep(1)
        light_ctrl.turn_off_head_light()
        time.sleep(1)
        
        # 测试6: 呼吸灯效果（短时间）
        logger.info("测试6: 呼吸灯效果（3秒）")
        light_ctrl.breath_light(3)
        
        # 测试7: 最终状态
        logger.info("测试7: 最终状态")
        final_status = light_ctrl.get_status()
        logger.info(f"最终状态: {final_status}")
        
        # 关闭连接
        light_ctrl.close()
        
        logger.info("=== 灯光控制器测试完成 ===")
        
    except Exception as e:
        logger.error(f"测试失败: {e}")
        import traceback
        logger.error(f"详细错误: {traceback.format_exc()}")


if __name__ == '__main__':
    # 运行测试
    test_light_controller()
