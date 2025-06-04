# 导入所需的库
import pygame  # 用于音频播放
import os  # 用于文件和路径操作
import random  # 用于随机选择音频文件
import threading  # 用于多线程操作
import time  # 用于时间相关操作
import yaml  # 用于读取配置文件
import pyttsx3  # 用于文字转语音

# 标记USB音频设备连接状态
usb_connected = False

# 获取当前文件路径
curpath = os.path.realpath(__file__)
thisPath = os.path.dirname(curpath)
# 读取配置文件
with open(os.path.dirname(thisPath) + '/config/config.yaml', 'r') as yaml_file:
    config = yaml.safe_load(yaml_file)

# 获取当前目录的绝对路径
current_path = os.path.dirname(thisPath)

# 初始化音频设备
try:
	pygame.mixer.init()
	pygame.mixer.music.set_volume(config['audio_config']['default_volume'])
	usb_connected = True
	print('audio usb connected')
except:
	usb_connected = False
	print('audio usb not connected')

# 创建音频播放事件标志和最小播放间隔时间
play_audio_event = threading.Event()
min_time_bewteen_play = config['audio_config']['min_time_bewteen_play']

# 初始化文字转语音引擎
engine = pyttsx3.init()
engine.setProperty('rate', config['audio_config']['speed_rate'])


def play_audio(input_audio_file):
	"""播放单个音频文件的函数"""
	if not usb_connected:
		return
	try:
		pygame.mixer.music.load(input_audio_file)
		pygame.mixer.music.play()
	except:
		play_audio_event.clear()
		return
	while pygame.mixer.music.get_busy():
		pass
	time.sleep(min_time_bewteen_play)
	play_audio_event.clear()


def play_random_audio(input_dirname, force_flag):
	"""从指定目录随机播放一个音频文件"""
	if not usb_connected:
		return
	if play_audio_event.is_set() and not force_flag:
		return
	audio_files = [f for f in os.listdir(current_path + "/sounds/" + input_dirname) if f.endswith((".mp3", ".wav"))]
	audio_file = random.choice(audio_files)
	play_audio_event.set()
	audio_thread = threading.Thread(target=play_audio, args=(current_path + "/sounds/" + input_dirname + "/" + audio_file,))
	audio_thread.start()


def play_audio_thread(input_file):
	"""在新线程中播放音频文件"""
	if not usb_connected:
		return
	if play_audio_event.is_set():
		return
	play_audio_event.set()
	audio_thread = threading.Thread(target=play_audio, args=(input_file,))
	audio_thread.start()


def play_file(audio_file):
	"""播放sounds目录下的指定音频文件"""
	if not usb_connected:
		return
	audio_file = current_path + "/sounds/" + audio_file
	play_audio_thread(audio_file)


def get_mixer_status():
	"""获取音频播放器状态"""
	if not usb_connected:
		return
	return pygame.mixer.music.get_busy()


def set_audio_volume(input_volume):
	"""设置音频音量(0-1)"""
	if not usb_connected:
		return
	input_volume = float(input_volume)
	if input_volume > 1:
		input_volume = 1
	elif input_volume < 0:
		input_volume = 0
	pygame.mixer.music.set_volume(input_volume)


def set_min_time_between(input_time):
	"""设置两次播放之间的最小间隔时间"""
	if not usb_connected:
		return
	global min_time_bewteen_play
	min_time_bewteen_play = input_time


def play_speech(input_text):
	"""播放文字转语音"""
	if not usb_connected:
		return
	engine.say(input_text)
	engine.runAndWait()
	play_audio_event.clear()


def play_speech_thread(input_text):
	"""在新线程中播放文字转语音"""
	if not usb_connected:
		return
	if play_audio_event.is_set():
		return
	play_audio_event.set()
	speech_thread = threading.Thread(target=play_speech, args=(input_text,))
	speech_thread.start()

def stop():
	"""停止当前音频播放"""
	if not usb_connected:
		return
	pygame.mixer.music.stop()
	play_audio_event.clear()


if __name__ == '__main__':
	# 测试代码
	# while True:
	# 	print(1)
	# 	engine.say("this is a test")
	# 	engine.runAndWait()
	# 	time.sleep(1)
	play_audio_thread("/home/ws/robot_car/robot_body/sounds/others/Boomopera_-_You_Rock_Full_Length.mp3")
	time.sleep(100)