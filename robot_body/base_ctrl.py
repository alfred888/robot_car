import serial  
import json
import queue
import threading
import yaml
import os
import time
import glob
import numpy as np
import logging

# 日志配置（由主程序统一加载，这里只获取 logger）
logger = logging.getLogger('body')

# 获取当前文件路径
curpath = os.path.realpath(__file__)
thisPath = os.path.dirname(curpath)

# 加载配置文件
with open(thisPath + '/config/config.yaml', 'r') as yaml_file:
    f = yaml.safe_load(yaml_file)

class ReadLine:
	"""串口读取类,用于读取串口数据、传感器数据和激光雷达数据"""
	def __init__(self, s):
		self.buf = bytearray()
		self.s = s

		# 传感器数据相关
		self.sensor_data = []
		self.sensor_list = []
		try:
			# 尝试连接USB传感器
			self.sensor_data_ser = serial.Serial(glob.glob('/dev/ttyUSB*')[0], 115200)
			logger.info("/dev/ttyUSB* connected succeed")
		except:
			self.sensor_data_ser = None
		self.sensor_data_max_len = 51

		# 激光雷达相关
		try:
			# 尝试连接激光雷达
			self.lidar_ser = serial.Serial(glob.glob('/dev/ttyACM*')[0], 230400, timeout=1)
			logger.info("/dev/ttyACM* connected succeed")
		except:
			self.lidar_ser = None
		self.ANGLE_PER_FRAME = 12  # 每帧角度数
		self.HEADER = 0x54         # 帧头
		self.lidar_angles = []     # 激光雷达角度数据
		self.lidar_distances = []  # 激光雷达距离数据
		self.lidar_angles_show = []    # 用于显示的角度数据
		self.lidar_distances_show = [] # 用于显示的距离数据
		self.last_start_angle = 0      # 上一帧起始角度

	def readline(self):
		"""读取一行数据,直到遇到换行符"""
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
		"""清空串口缓冲区"""
		self.s.reset_input_buffer()

	def read_sensor_data(self):
		"""读取传感器数据"""
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
			logger.error(f"[base_ctrl.read_sensor_data] error: {e}")

	def parse_lidar_frame(self, data):
		"""解析激光雷达数据帧"""
		# header = data[0]
		# verlen = data[1]
		# speed  = data[3] << 8 | data[2]
		start_angle = (data[5] << 8 | data[4]) * 0.01
		# print(start)
		# end_angle = (data[43] << 8 | data[42]) * 0.01
		for i in range(0, self.ANGLE_PER_FRAME):
			offset = 6 + i * 3
			distance = data[offset+1] << 8 | data[offset]
			confidence = data[offset+2]
			# lidar_angles.append(np.radians(start_angle + i * 0.167))
			self.lidar_angles.append(np.radians(start_angle + i * 0.83333 + 180))
			# lidar_angles.append(np.radians(start_angle + end_angle))
			self.lidar_distances.append(distance)
		# end_angle = (data[43] << 8 | data[42]) * 0.01
		# timestamp = data[45] << 8 | data[44]
		# crc = data[46]
		return start_angle

	def lidar_data_recv(self):
		"""接收激光雷达数据"""
		if self.lidar_ser == None:
			return
		try:
			while True:
				self.header = self.lidar_ser.read(1)
				if self.header == b'\x54':
					# Read the rest of the data
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
			logger.error(f"[base_ctrl.lidar_data_recv] error: {e}")
			self.lidar_ser = serial.Serial(glob.glob('/dev/ttyACM*')[0], 230400, timeout=1)


class BaseController:
	"""基础控制器类,用于控制机器人的基本功能"""

	def __init__(self, uart_dev_set, buad_set):
		"""初始化基础控制器
		Args:
			uart_dev_set: 串口设备名
			buad_set: 波特率
		"""
		logger.info(f"初始化BaseController,串口:{uart_dev_set},波特率:{buad_set}")
		self.ser = serial.Serial(uart_dev_set, buad_set, timeout=1)
		self.rl = ReadLine(self.ser)
		self.command_queue = queue.Queue()
		self.command_thread = threading.Thread(target=self.process_commands, daemon=True)
		self.command_thread.start()
		logger.info("命令处理线程已启动")

		# 灯光状态
		self.base_light_status = 0
		self.head_light_status = 0

		# 数据缓存
		self.data_buffer = None
		self.base_data = None

		# 功能开关
		self.use_lidar = f['base_config']['use_lidar']
		self.extra_sensor = f['base_config']['extra_sensor']
		logger.info(f"激光雷达状态:{self.use_lidar},额外传感器:{self.extra_sensor}")

	def feedback_data(self):
		"""获取反馈数据"""
		try:
			while self.rl.s.in_waiting > 0:
				raw = self.rl.readline()
				try:
					text = raw.decode('utf-8')
				except UnicodeDecodeError as e:
					logger.warning(f"[decode] error: {e} | raw: {raw[:10].hex()}")
					continue

				try:
					self.data_buffer = json.loads(text)
				except json.JSONDecodeError as e:
					logger.warning(f"[json] error: {e} | text: {text}")
					continue

				if 'T' in self.data_buffer:
					self.base_data = self.data_buffer
					self.data_buffer = None
					if self.base_data["T"] == 1003:
						logger.debug(self.base_data)
						return self.base_data

			self.rl.clear_buffer()

			raw = self.rl.readline()
			try:
				text = raw.decode('utf-8')
				self.data_buffer = json.loads(text)
				self.base_data = self.data_buffer
				return self.base_data
			except Exception as e:
				logger.warning(f"[feedback_data final] error: {e} | raw: {raw[:10].hex()}")
				return None

		except Exception as e:
			self.rl.clear_buffer()
			logger.error(f"[base_ctrl.feedback_data] fatal error: {e}")

	def on_data_received(self):
		"""接收数据回调"""
		logger.debug("重置输入缓冲区并读取数据")
		self.ser.reset_input_buffer()
		data_read = json.loads(self.rl.readline().decode('utf-8'))
		return data_read

	def send_command(self, data):
		"""发送命令到命令队列"""
		logger.debug(f"发送命令: {data}")
		self.command_queue.put(data)

	def process_commands(self):
		"""处理命令队列中的命令"""
		while True:
			data = self.command_queue.get()
			logger.debug(f"处理命令: {data}")
			self.ser.write((json.dumps(data) + '\n').encode("utf-8"))

	def base_json_ctrl(self, input_json):
		"""基础JSON控制接口"""
		logger.debug(f"基础JSON控制: {input_json}")
		self.send_command(input_json)

	def gimbal_emergency_stop(self):
		"""云台紧急停止"""
		logger.info("云台紧急停止")
		data = {"T":0}
		logger.debug(f"速度控制 - 左:{input_left} 右:{input_right}")

	def base_speed_ctrl(self, input_left, input_right):
		"""控制底盘左右轮速度
		Args:
			input_left: 左轮速度
			input_right: 右轮速度
		"""
		logger.info(f"[base_speed_ctrl] 速度控制 - 左:{input_left} 右:{input_right}")
		data = {"T":1,"L":input_left,"R":input_right}
		self.send_command(data)

	def gimbal_ctrl(self, input_x, input_y, input_speed, input_acceleration):
		"""控制云台运动
		Args:
			input_x: X轴角度(-180~180)
			input_y: Y轴角度(-30~90)
			input_speed: 运动速度
			input_acceleration: 加速度
		"""
		logger.debug(f"云台控制 - X:{input_x} Y:{input_y} 速度:{input_speed} 加速度:{input_acceleration}")
		data = {"T":133,"X":input_x,"Y":input_y,"SPD":input_speed,"ACC":input_acceleration}
		self.send_command(data)

	def gimbal_base_ctrl(self, input_x, input_y, input_speed):
		"""云台基础控制
		Args:
			input_x: X轴角度
			input_y: Y轴角度
			input_speed: 运动速度
		"""
		logger.debug(f"云台基础控制 - X:{input_x} Y:{input_y} 速度:{input_speed}")
		data = {"T":141,"X":input_x,"Y":input_y,"SPD":input_speed}
		self.send_command(data)

	def base_oled(self, input_line, input_text):
		"""OLED显示控制
		Args:
			input_line: 显示行号
			input_text: 显示文本
		"""
		logger.debug(f"OLED显示 - 行:{input_line} 文本:{input_text}")
		data = {"T":3,"lineNum":input_line,"Text":input_text}
		self.send_command(data)

	def base_default_oled(self):
		"""恢复OLED默认显示"""
		logger.debug("恢复OLED默认显示")
		data = {"T":-3}
		self.send_command(data)

	def bus_servo_id_set(self, old_id, new_id):
		"""设置总线舵机ID
		Args:
			old_id: 原ID
			new_id: 新ID
		"""
		logger.info(f"设置总线舵机ID - 原ID:{old_id} 新ID:{new_id}")
		data = {"T":f['cmd_config']['cmd_set_servo_id'],"raw":old_id,"new":new_id}
		self.send_command(data)

	def bus_servo_torque_lock(self, input_id, input_status):
		"""舵机扭矩锁定控制
		Args:
			input_id: 舵机ID
			input_status: 锁定状态
		"""
		logger.debug(f"舵机扭矩锁定 - ID:{input_id} 状态:{input_status}")
		data = {"T":f['cmd_config']['cmd_servo_torque'],"id":input_id,"cmd":input_status}
		self.send_command(data)

	def bus_servo_mid_set(self, input_id):
		"""设置舵机中位
		Args:
			input_id: 舵机ID
		"""
		logger.debug(f"设置舵机中位 - ID:{input_id}")
		data = {"T":f['cmd_config']['cmd_set_servo_mid'],"id":input_id}
		self.send_command(data)

	def lights_ctrl(self, pwmA, pwmB):
		"""控制灯光
		Args:
			pwmA: 基础灯光PWM值
			pwmB: 头部灯光PWM值
		"""
		logger.debug(f"灯光控制 - A:{pwmA} B:{pwmB}")
		data = {"T":132,"IO4":pwmA,"IO5":pwmB}
		self.send_command(data)
		self.base_light_status = pwmA
		self.head_light_status = pwmB

	def base_lights_ctrl(self):
		"""基础灯光开关控制"""
		if self.base_light_status != 0:
			self.base_light_status = 0
		else:
			self.base_light_status = 255
		logger.debug(f"基础灯光控制 - 状态:{self.base_light_status}")
		self.lights_ctrl(self.base_light_status, self.head_light_status)

	def gimbal_dev_close(self):
		"""关闭云台设备"""
		logger.info("关闭云台设备")
		self.ser.close()

	def breath_light(self, input_time):
		"""呼吸灯效果
		Args:
			input_time: 持续时间(秒)
		"""
		logger.info(f"启动呼吸灯 - 持续时间:{input_time}秒")
		breath_start_time = time.time()
		while time.time() - breath_start_time < input_time:
			for i in range(0, 128, 10):
				self.lights_ctrl(i, 128-i)
				time.sleep(0.1)
			for i in range(0, 128, 10):
				self.lights_ctrl(128-i, i)
				time.sleep(0.1)
		self.lights_ctrl(0, 0)
		logger.info("呼吸灯结束")


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