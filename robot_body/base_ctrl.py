"""
机器人底盘控制模块

该模块提供了机器人底盘的基础控制功能，包括：
- 串口通信
- 传感器数据读取
- 激光雷达数据处理
- 底盘运动控制
- 云台控制
- LED灯控制
- 舵机控制
"""

import serial  
import json
import queue
import threading
import yaml
import os
import time
import glob
import numpy as np

# 加载配置文件
curpath = os.path.realpath(__file__)
thisPath = os.path.dirname(curpath)
with open(thisPath + '/config.yaml', 'r') as yaml_file:
    f = yaml.safe_load(yaml_file)

class ReadLine:
    """
    串口数据读取类
    
    负责处理串口通信、传感器数据读取和激光雷达数据处理
    """
    def __init__(self, s):
        """
        初始化串口读取器
        
        Args:
            s: 串口对象
        """
        self.buf = bytearray()
        self.s = s

        # 传感器数据相关属性
        self.sensor_data = []
        self.sensor_list = []
        try:
            self.sensor_data_ser = serial.Serial(glob.glob('/dev/ttyUSB*')[0], 115200)
            print("/dev/ttyUSB* connected succeed")
        except:
            self.sensor_data_ser = None
        self.sensor_data_max_len = 51

        # 激光雷达相关属性
        try:
            self.lidar_ser = serial.Serial(glob.glob('/dev/ttyACM*')[0], 230400, timeout=1)
            print("/dev/ttyACM* connected succeed")
        except:
            self.lidar_ser = None
        self.ANGLE_PER_FRAME = 12  # 每帧数据包含的角度数
        self.HEADER = 0x54  # 数据帧头
        self.lidar_angles = []  # 激光雷达角度数据
        self.lidar_distances = []  # 激光雷达距离数据
        self.lidar_angles_show = []  # 用于显示的角度数据
        self.lidar_distances_show = []  # 用于显示的距离数据
        self.last_start_angle = 0  # 上一帧的起始角度

    def readline(self):
        """
        读取一行串口数据
        
        Returns:
            bytes: 读取到的数据行
        """
        i = self.buf.find(b"\n")
        if i >= 0:
            r = self.buf[:i+1]
            self.buf = self.buf[i+1:]
            return r
        while True:
            i = max(1, min(512, self.s.in_waiting))
            data = self.s.read(i)
            i = data.find(b"\n")
            if i >= 0:
                r = self.buf + data[:i+1]
                self.buf[0:] = data[i+1:]
                return r
            else:
                self.buf.extend(data)

    def clear_buffer(self):
        """清空输入缓冲区"""
        self.s.reset_input_buffer()

    def read_sensor_data(self):
        """读取传感器数据并处理"""
        if self.sensor_data_ser == None:
            return

        try:
            buffer_clear = False
            while self.sensor_data_ser.in_waiting > 0:
                buffer_clear = True
                sensor_readline = self.sensor_data_ser.readline()
                if len(sensor_readline) <= self.sensor_data_max_len:
                    self.sensor_list.append(sensor_readline.decode('utf-8')[:-2])
                else:
                    self.sensor_list.append(sensor_readline.decode('utf-8')[:self.sensor_data_max_len])
                    self.sensor_list.append(sensor_readline.decode('utf-8')[self.sensor_data_max_len:-2])
            if buffer_clear:
                self.sensor_data = self.sensor_list.copy()
                self.sensor_list.clear()
                self.sensor_data_ser.reset_input_buffer()
        except Exception as e:
            print(f"[base_ctrl.read_sensor_data] error: {e}")

    def parse_lidar_frame(self, data):
        """
        解析激光雷达数据帧
        
        Args:
            data: 原始数据帧
            
        Returns:
            float: 起始角度
        """
        start_angle = (data[5] << 8 | data[4]) * 0.01
        for i in range(0, self.ANGLE_PER_FRAME):
            offset = 6 + i * 3
            distance = data[offset+1] << 8 | data[offset]
            confidence = data[offset+2]
            self.lidar_angles.append(np.radians(start_angle + i * 0.83333 + 180))
            self.lidar_distances.append(distance)
        return start_angle

    def lidar_data_recv(self):
        """接收和处理激光雷达数据"""
        if self.lidar_ser == None:
            return
        try:
            while True:
                self.header = self.lidar_ser.read(1)
                if self.header == b'\x54':
                    data = self.header + self.lidar_ser.read(46)
                    hex_data = [int(hex(byte), 16) for byte in data]
                    start_angle = self.parse_lidar_frame(hex_data)
                    if self.last_start_angle > start_angle:
                        break
                    self.last_start_angle = start_angle
                else:
                    self.lidar_ser.flushInput()

            self.last_start_angle = start_angle
            self.lidar_angles_show = self.lidar_angles.copy()
            self.lidar_distances_show = self.lidar_distances.copy()
            self.lidar_angles.clear()
            self.lidar_distances.clear()
        except Exception as e:
            print(f"[base_ctrl.lidar_data_recv] error: {e}")
            self.lidar_ser = serial.Serial(glob.glob('/dev/ttyACM*')[0], 230400, timeout=1)


class BaseController:
    """
    机器人底盘控制器
    
    提供机器人底盘的各种控制功能，包括运动控制、云台控制、LED控制等
    """
    def __init__(self, uart_dev_set, buad_set):
        """
        初始化底盘控制器
        
        Args:
            uart_dev_set: 串口设备
            buad_set: 波特率
        """
        self.ser = serial.Serial(uart_dev_set, buad_set, timeout=1)
        self.rl = ReadLine(self.ser)
        self.command_queue = queue.Queue()
        self.command_thread = threading.Thread(target=self.process_commands, daemon=True)
        self.command_thread.start()

        # 状态变量
        self.base_light_status = 0
        self.head_light_status = 0
        self.data_buffer = None
        self.base_data = None

        # 配置参数
        self.use_lidar = f['base_config']['use_lidar']
        self.extra_sensor = f['base_config']['extra_sensor']

    def feedback_data(self):
        """
        获取底盘反馈数据
        
        Returns:
            dict: 底盘状态数据
        """
        try:
            while self.rl.s.in_waiting > 0:
                self.data_buffer = json.loads(self.rl.readline().decode('utf-8'))
                if 'T' in self.data_buffer:
                    self.base_data = self.data_buffer
                    self.data_buffer = None
                    if self.base_data["T"] == 1003:
                        print(self.base_data)
                        return self.base_data
            self.rl.clear_buffer()
            self.data_buffer = json.loads(self.rl.readline().decode('utf-8'))
            self.base_data = self.data_buffer
            return self.base_data
        except Exception as e:
            self.rl.clear_buffer()
            print(f"[base_ctrl.feedback_data] error: {e}")

    def on_data_received(self):
        """
        接收并解析数据
        
        Returns:
            dict: 解析后的数据
        """
        self.ser.reset_input_buffer()
        data_read = json.loads(self.rl.readline().decode('utf-8'))
        return data_read

    def send_command(self, data):
        """
        发送控制命令
        
        Args:
            data: 要发送的命令数据
        """
        self.command_queue.put(data)

    def process_commands(self):
        """处理命令队列中的命令"""
        while True:
            data = self.command_queue.get()
            self.ser.write((json.dumps(data) + '\n').encode("utf-8"))

    def base_json_ctrl(self, input_json):
        """
        发送JSON格式的控制命令
        
        Args:
            input_json: JSON格式的控制命令
        """
        self.send_command(input_json)

    def gimbal_emergency_stop(self):
        """云台紧急停止"""
        data = {"T":0}
        self.send_command(data)

    def base_speed_ctrl(self, input_left, input_right):
        """
        控制底盘速度
        
        Args:
            input_left: 左轮速度
            input_right: 右轮速度
        """
        data = {"T":1,"L":input_left,"R":input_right}
        self.send_command(data)

    def gimbal_ctrl(self, input_x, input_y, input_speed, input_acceleration):
        """
        控制云台运动
        
        Args:
            input_x: X轴位置
            input_y: Y轴位置
            input_speed: 运动速度
            input_acceleration: 加速度
        """
        data = {"T":133,"X":input_x,"Y":input_y,"SPD":input_speed,"ACC":input_acceleration}
        self.send_command(data)

    def gimbal_base_ctrl(self, input_x, input_y, input_speed):
        """
        控制云台基础运动
        
        Args:
            input_x: X轴位置
            input_y: Y轴位置
            input_speed: 运动速度
        """
        data = {"T":141,"X":input_x,"Y":input_y,"SPD":input_speed}
        self.send_command(data)

    def base_oled(self, input_line, input_text):
        """
        控制OLED显示
        
        Args:
            input_line: 显示行号
            input_text: 显示文本
        """
        data = {"T":3,"lineNum":input_line,"Text":input_text}
        self.send_command(data)

    def base_default_oled(self):
        """恢复OLED默认显示"""
        data = {"T":-3}
        self.send_command(data)

    def bus_servo_id_set(self, old_id, new_id):
        """
        设置舵机ID
        
        Args:
            old_id: 原ID
            new_id: 新ID
        """
        data = {"T":f['cmd_config']['cmd_set_servo_id'],"raw":old_id,"new":new_id}
        self.send_command(data)

    def bus_servo_torque_lock(self, input_id, input_status):
        """
        控制舵机力矩锁定
        
        Args:
            input_id: 舵机ID
            input_status: 锁定状态
        """
        data = {"T":f['cmd_config']['cmd_servo_torque'],"id":input_id,"cmd":input_status}
        self.send_command(data)

    def bus_servo_mid_set(self, input_id):
        """
        设置舵机中位
        
        Args:
            input_id: 舵机ID
        """
        data = {"T":f['cmd_config']['cmd_set_servo_mid'],"id":input_id}
        self.send_command(data)

    def lights_ctrl(self, pwmA, pwmB):
        """
        控制LED灯
        
        Args:
            pwmA: 底盘灯PWM值
            pwmB: 头部灯PWM值
        """
        data = {"T":132,"IO4":pwmA,"IO5":pwmB}
        self.send_command(data)
        self.base_light_status = pwmA
        self.head_light_status = pwmB

    def base_lights_ctrl(self):
        """切换底盘灯光状态"""
        if self.base_light_status != 0:
            self.base_light_status = 0
        else:
            self.base_light_status = 255
        self.lights_ctrl(self.base_light_status, self.head_light_status)

    def gimbal_dev_close(self):
        self.ser.close()

    def breath_light(self, input_time):
        breath_start_time = time.time()
        while time.time() - breath_start_time < input_time:
            for i in range(0, 128, 10):
                self.lights_ctrl(i, 128-i)
                time.sleep(0.1)
            for i in range(0, 128, 10):
                self.lights_ctrl(128-i, i)
                time.sleep(0.1)
        self.lights_ctrl(0, 0)


if __name__ == '__main__':
    # RPi5
    base = BaseController('/dev/ttyAMA0', 115200)

    # RPi4B
    # base = BaseController('/dev/serial0', 115200)

    # breath light for 15s
    base.breath_light(15)

    # gimble ctrl, look forward
    #                x  y  spd acc
    base.gimbal_ctrl(0, 0, 10, 0)
    
    # x(-180 ~ 180)
    # x- look left
    # x+ look right

    # y(-30 ~ 90)
    # y- look down
    # y+ look up