# 导入基础控制器库
from base_ctrl import BaseController
import threading
import yaml, os
os.makedirs('logs', exist_ok=True)
import logging.config

curpath = os.path.realpath(__file__)
thisPath = os.path.dirname(curpath)

def setup_logging(config_path):
    """初始化日志配置，处理 ~ 和日志目录创建"""
    try:
        config_path = os.path.abspath(config_path)
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        # 处理日志路径
        for handler in config.get("handlers", {}).values():
            if "filename" in handler:
                handler["filename"] = os.path.abspath(os.path.expanduser(handler["filename"]))
                # 创建目录
                os.makedirs(os.path.dirname(handler["filename"]), exist_ok=True)

        logging.config.dictConfig(config)
    except Exception as e:
        print(f"[ERROR] Failed to load logging configuration: {e}", file=sys.stderr)
        logging.basicConfig(level=logging.INFO)

# 使用当前目录中的 config/logging_config.yaml
setup_logging(os.path.join(os.path.dirname(__file__), "config", "logging_config.yaml"))

# 创建日志记录器
logger = logging.getLogger("body")

# 检查是否为树莓派5
def is_raspberry_pi5():
    with open('/proc/cpuinfo', 'r') as file:
        for line in file:
            if 'Model' in line:
                if 'Raspberry Pi 5' in line:
                    logger.info("检测到树莓派5")
                    return True
                else:
                    logger.info("检测到其他型号树莓派")
                    return False

# 根据树莓派型号选择串口
if is_raspberry_pi5():
    logger.info("使用 /dev/ttyAMA0 串口")
    base = BaseController('/dev/ttyAMA0', 115200)
else:
    logger.info("使用 /dev/serial0 串口")
    base = BaseController('/dev/serial0', 115200)

# 启动呼吸灯线程
threading.Thread(target=lambda: base.breath_light(15), daemon=True).start()
logger.info("启动呼吸灯")

# 读取配置文件
with open(thisPath + '/config/config.yaml', 'r') as yaml_file:
    f = yaml.safe_load(yaml_file)
    logger.info(f"加载配置文件: {f['base_config']['robot_name']}")

# OLED显示初始化信息
base.base_oled(0, f["base_config"]["robot_name"])
base.base_oled(1, f"sbc_version: {f['base_config']['sbc_version']}")
base.base_oled(2, f"{f['base_config']['main_type']}{f['base_config']['module_type']}")
base.base_oled(3, "Starting...")
logger.info("OLED显示初始化完成")

# 导入Flask及相关库
from flask import Flask, render_template, Response, request, jsonify, redirect, url_for, send_from_directory, send_file
from flask_socketio import SocketIO, emit
from werkzeug.utils import secure_filename
from aiortc import RTCPeerConnection, RTCSessionDescription
import json
import uuid
import asyncio
import time
import cv_ctrl
import robot_mouth.audio_ctrl as audio_ctrl
import os_info

# 获取系统信息
UPLOAD_FOLDER = thisPath + '/sounds/others'
si = os_info.SystemInfo()
logger.info("系统信息初始化完成")

# 创建Flask应用和SocketIO
app = Flask(__name__)
socketio = SocketIO(app)
logger.info("Flask应用和SocketIO初始化完成")

# WebRTC连接管理
active_pcs = {}
MAX_CONNECTIONS = 1
pcs = set()

# 相机控制对象
cvf = cv_ctrl.OpencvFuncs(thisPath, base)
logger.info("相机控制初始化完成")

# 命令与动作映射表
cmd_actions = {
    # 缩放控制
    f['code']['zoom_x1']: lambda: cvf.scale_ctrl(1),
    f['code']['zoom_x2']: lambda: cvf.scale_ctrl(2),
    f['code']['zoom_x4']: lambda: cvf.scale_ctrl(4),

    # 图片和视频控制
    f['code']['pic_cap']: cvf.picture_capture,
    f['code']['vid_sta']: lambda: cvf.video_record(True),
    f['code']['vid_end']: lambda: cvf.video_record(False),

    # 计算机视觉模式控制
    f['code']['cv_none']: lambda: cvf.set_cv_mode(f['code']['cv_none']),
    f['code']['cv_moti']: lambda: cvf.set_cv_mode(f['code']['cv_moti']),
    f['code']['cv_face']: lambda: cvf.set_cv_mode(f['code']['cv_face']),
    f['code']['cv_objs']: lambda: cvf.set_cv_mode(f['code']['cv_objs']),
    f['code']['cv_clor']: lambda: cvf.set_cv_mode(f['code']['cv_clor']),
    f['code']['mp_hand']: lambda: cvf.set_cv_mode(f['code']['mp_hand']),
    f['code']['cv_auto']: lambda: cvf.set_cv_mode(f['code']['cv_auto']),
    f['code']['mp_face']: lambda: cvf.set_cv_mode(f['code']['mp_face']),
    f['code']['mp_pose']: lambda: cvf.set_cv_mode(f['code']['mp_pose']),

    # 检测反应控制
    f['code']['re_none']: lambda: cvf.set_detection_reaction(f['code']['re_none']),
    f['code']['re_capt']: lambda: cvf.set_detection_reaction(f['code']['re_capt']),
    f['code']['re_reco']: lambda: cvf.set_detection_reaction(f['code']['re_reco']),

    # 运动控制
    f['code']['mc_lock']: lambda: cvf.set_movtion_lock(True),
    f['code']['mc_unlo']: lambda: cvf.set_movtion_lock(False),

    # 灯光控制
    f['code']['led_off']: lambda: cvf.head_light_ctrl(0),
    f['code']['led_aut']: lambda: cvf.head_light_ctrl(1),
    f['code']['led_ton']: lambda: cvf.head_light_ctrl(2),

    # 舵机控制
    f['code']['release']: lambda: base.bus_servo_torque_lock(255, 0),
    f['code']['s_panid']: lambda: base.bus_servo_id_set(255, 2),
    f['code']['s_tilid']: lambda: base.bus_servo_id_set(255, 1),
    f['code']['set_mid']: lambda: base.bus_servo_mid_set(255),

    # 基础灯光控制
    f['code']['base_of']: lambda: base.lights_ctrl(0, base.head_light_status),
    f['code']['base_on']: lambda: base.lights_ctrl(255, base.head_light_status),
    f['code']['head_ct']: lambda: cvf.head_light_ctrl(3),
    f['code']['base_ct']: base.base_lights_ctrl
}

# 需要反馈的命令动作
cmd_feedback_actions = [f['code']['cv_none'], f['code']['cv_moti'],
                        f['code']['cv_face'], f['code']['cv_objs'],
                        f['code']['cv_clor'], f['code']['mp_hand'],
                        f['code']['cv_auto'], f['code']['mp_face'],
                        f['code']['mp_pose'], f['code']['re_none'],
                        f['code']['re_capt'], f['code']['re_reco'],
                        f['code']['mc_lock'], f['code']['mc_unlo'],
                        f['code']['led_off'], f['code']['led_aut'],
                        f['code']['led_ton'], f['code']['base_of'],
                        f['code']['base_on'], f['code']['head_ct'],
                        f['code']['base_ct']
                        ]

# 处理计算机视觉信息
def process_cv_info(cmd):
    if cmd[f['fb']['detect_type']] != f['code']['cv_none']:
        logger.debug(cmd[f['fb']['detect_type']])
        pass

# 生成视频帧
def generate_frames():
    while True:
        frame = cvf.frame_process()
        try:
            yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n') 
        except Exception as e:
            logger.error(f"生成视频帧错误: {e}")

# 主页路由
@app.route('/')
def index():
    audio_ctrl.play_random_audio("connected", False)
    logger.info("用户访问主页")
    return render_template('index.html')

# 机器人视觉路由
@app.route('/eyes')
def eyes():
    logger.info("用户访问机器人视觉页面")
    return render_template('index_eyes.html')

# 获取配置路由
@app.route('/config')
def get_config():
    logger.debug("获取配置文件")
    with open(thisPath + '/config/config.yaml', 'r') as file:
        yaml_content = file.read()
    return yaml_content

# 静态文件服务
@app.route('/<path:filename>')
def serve_static(filename):
    logger.debug(f"请求静态文件: {filename}")
    return send_from_directory('templates', filename)

# 获取图片文件名
@app.route('/get_photo_names')
def get_photo_names():
    logger.debug("获取图片列表")
    photo_files = sorted(os.listdir(thisPath + '/templates/pictures'), key=lambda x: os.path.getmtime(os.path.join(thisPath + '/templates/pictures', x)), reverse=True)
    return jsonify(photo_files)

# 删除图片
@app.route('/delete_photo', methods=['POST'])
def delete_photo():
    filename = request.form.get('filename')
    try:
        os.remove(os.path.join(thisPath + '/templates/pictures', filename))
        logger.info(f"删除图片: {filename}")
        return jsonify(success=True)
    except Exception as e:
        logger.error(f"删除图片失败: {e}")
        return jsonify(success=False)

# 视频相关路由
@app.route('/videos/<path:filename>')
def videos(filename):
    logger.debug(f"请求视频文件: {filename}")
    return send_from_directory(thisPath + '/templates/videos', filename)

@app.route('/get_video_names')
def get_video_names():
    logger.debug("获取视频列表")
    video_files = sorted(
        [filename for filename in os.listdir(thisPath + '/templates/videos/') if filename.endswith('.mp4')],
        key=lambda filename: os.path.getctime(os.path.join(thisPath + '/templates/videos/', filename)),
        reverse=True
    )
    return jsonify(video_files)

@app.route('/delete_video', methods=['POST'])
def delete_video():
    filename = request.form.get('filename')
    try:
        os.remove(os.path.join(thisPath + '/templates/videos', filename))
        logger.info(f"删除视频: {filename}")
        return jsonify(success=True)
    except Exception as e:
        logger.error(f"删除视频失败: {e}")
        return jsonify(success=False)

# WebRTC连接管理
def manage_connections(pc_id):
    if len(active_pcs) >= MAX_CONNECTIONS:
        oldest_pc_id = next(iter(active_pcs))
        old_pc = active_pcs.pop(oldest_pc_id)
        old_pc.close()
        logger.info(f"关闭旧连接: {oldest_pc_id}")
    active_pcs[pc_id] = pc
    logger.info(f"新建连接: {pc_id}")

# WebRTC offer处理
async def offer_async():
    params = await request.json
    offer = RTCSessionDescription(sdp=params["sdp"], type=params["type"])
    pc = RTCPeerConnection()
    pc_id = "PeerConnection(%s)" % uuid.uuid4()
    pc_id = pc_id[:8]
    manage_connections(pc_id)
    await pc.createOffer(offer)
    await pc.setLocalDescription(offer)
    response_data = {"sdp": pc.localDescription.sdp, "type": pc.localDescription.type}
    logger.info(f"创建WebRTC连接: {pc_id}")
    return jsonify(response_data)

def offer():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    future = asyncio.run_coroutine_threadsafe(offer_async(), loop)
    return future.result()

# 设置产品版本
def set_version(input_main, input_module):
    logger.info(f"设置产品版本: main={input_main}, module={input_module}")
    base.base_json_ctrl({"T":900,"main":input_main,"module":input_module})
    if input_main == 1:
        cvf.info_update("RaspRover", (0,255,255), 0.36)
    elif input_main == 2:
        cvf.info_update("UGV Rover", (0,255,255), 0.36)
    elif input_main == 3:
        cvf.info_update("UGV Beast", (0,255,255), 0.36)
    if input_module == 0:
        cvf.info_update("No Module", (0,255,255), 0.36)
    elif input_module == 1:
        cvf.info_update("ARM", (0,255,255), 0.36)
    elif input_module == 2:
        cvf.info_update("PT", (0,255,255), 0.36)

# 命令行控制主函数
def cmdline_ctrl(args_string):
    if not args_string:
        return
    args = args_string.split()
    
    # 基础控制命令
    if args[0] == 'base':
        if args[1] == '-c' or args[1] == '--cmd':
            base.base_json_ctrl(json.loads(args[2]))
        elif args[1] == '-r' or args[1] == '--recv':
            if args[2] == 'on':
                cvf.show_recv_info(True)
            else:
                cvf.show_recv_info(False)

    # 音频控制命令
    elif args[0] == 'audio':
        if args[1] == '-s' or args[1] == '--say':
            audio_ctrl.play_speech_thread(' '.join(args[2:]))
        elif args[1] == '-v' or args[1] == '--volume':
            audio_ctrl.set_audio_volume(args[2])
        elif args[1] == '-p' or args[1] == '--play_file':
            audio_ctrl.play_file(args[2])

    # 发送命令
    elif args[0] == 'send':
        if args[1] == '-a' or args[1] == '--add':
            if args[2] == '-b' or args[2] == '--broadcast':
                base.base_json_ctrl({"T":303,"mac":"FF:FF:FF:FF:FF:FF"})
            else:
                base.base_json_ctrl({"T":303,"mac":args[2]})
        elif args[1] == '-rm' or args[1] == '--remove':
            if args[2] == '-b' or args[2] == '--broadcast':
                base.base_json_ctrl({"T":304,"mac":"FF:FF:FF:FF:FF:FF"})
            else:
                base.base_json_ctrl({"T":304,"mac":args[2]})
        elif args[1] == '-b' or args[1] == '--broadcast':
            base.base_json_ctrl({"T":306,"mac":"FF:FF:FF:FF:FF:FF","dev":0,"b":0,"s":0,"e":0,"h":0,"cmd":3,"megs":' '.join(args[2:])})
        elif args[1] == '-g' or args[1] == '--group':
            base.base_json_ctrl({"T":305,"dev":0,"b":0,"s":0,"e":0,"h":0,"cmd":3,"megs":' '.join(args[2:])})
        else:
            base.base_json_ctrl({"T":306,"mac":args[1],"dev":0,"b":0,"s":0,"e":0,"h":0,"cmd":3,"megs":' '.join(args[2:])})

    # 计算机视觉控制命令
    elif args[0] == 'cv':
        if args[1] == '-r' or args[1] == '--range':
            try:
                lower_trimmed = args[2].strip("[]")
                lower_nums = [int(lower_num) for lower_num in lower_trimmed.split(",")]
                if all(0 <= num <= 255 for num in lower_nums):
                    pass
                else:
                    return
            except:
                return
            try:
                upper_trimmed = args[3].strip("[]")
                upper_nums = [int(upper_num) for upper_num in upper_trimmed.split(",")]
                if all(0 <= num <= 255 for num in upper_nums):
                    pass
                else:
                    return
            except:
                return
            cvf.change_target_color(lower_nums, upper_nums)
        elif args[1] == '-s' or args[1] == '--select':
            cvf.selet_target_color(args[2])

    # 视频控制命令
    elif args[0] == 'video' or args[0] == 'v':
        if args[1] == '-q' or args[1] == '--quality':
            try:
                int(args[2])
            except:
                return
            cvf.set_video_quality(int(args[2]))

    # 线路控制命令
    elif args[0] == 'line':
        if args[1] == '-r' or args[1] == '--range':
            try:
                lower_trimmed = args[2].strip("[]")
                lower_nums = [int(lower_num) for lower_num in lower_trimmed.split(",")]
                if all(0 <= num <= 255 for num in lower_nums):
                    pass
                else:
                    return
            except:
                return
            try:
                upper_trimmed = args[3].strip("[]")
                upper_nums = [int(upper_num) for upper_num in upper_trimmed.split(",")]
                if all(0 <= num <= 255 for num in upper_nums):
                    pass
                else:
                    return
            except:
                return
            cvf.change_line_color(lower_nums, upper_nums)
        elif args[1] == '-s' or args[1] == '--set':
            if len(args) != 9:
                return
            try:
                for i in range(2,9):
                    float(args[i])
            except:
                return
            cvf.set_line_track_args(float(args[2]), float(args[3]), float(args[4]), float(args[5]), float(args[6]), float(args[7]), float(args[8]))

    # 跟踪控制命令
    elif args[0] == 'track':
        cvf.set_pt_track_args(args[1], args[2])

    # 延时摄影命令
    elif args[0] == 'timelapse':
        if args[1] == '-s' or args[1] == '--start':
            if len(args) != 6:
                return
            try:
                move_speed = float(args[2])
                move_time  = float(args[3])
                t_interval = float(args[4])
                loop_times = int(args[5])
            except:
                return
            cvf.timelapse(move_speed, move_time, t_interval, loop_times)
        elif args[1] == '-e' or args[1] == '--end' or args[1] == '--stop':
            cvf.mission_stop()

    # 产品类型设置
    elif args[0] == 'p':
        main_type = int(args[1][0])
        module_type = int(args[1][1])
        set_version(main_type, module_type)

    # 系统设置
    elif args[0] == 's':
        main_type = int(args[1][0])
        module_type = int(args[1][1])
        if main_type == 1:
            f['base_config']['robot_name'] = "RaspRover"
            f['args_config']['max_speed'] = 0.65
            f['args_config']['slow_speed'] = 0.3
        elif main_type == 2:
            f['base_config']['robot_name'] = "UGV Rover"
            f['args_config']['max_speed'] = 1.3
            f['args_config']['slow_speed'] = 0.2
        elif main_type == 3:
            f['base_config']['robot_name'] = "UGV Beast"
            f['args_config']['max_speed'] = 1.0
            f['args_config']['slow_speed'] = 0.2
        f['base_config']['main_type'] = main_type
        f['base_config']['module_type'] = module_type
        with open(thisPath + '/config/config.yaml', "w") as yaml_file:
            yaml.dump(f, yaml_file)
        set_version(main_type, module_type)

    # 测试命令
    elif args[0] == 'test':
        cvf.update_base_data({"T":1003,"mac":1111,"megs":"helllo aaaaaaaa"})

# WebRTC路由
@app.route('/offer', methods=['POST'])
def offer_route():
    return offer()

# 视频流路由
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# 命令处理路由
@app.route('/send_command', methods=['POST'])
def handle_command():
    command = request.form['command']
    logger.info(f"收到命令: {command}")
    cvf.info_update("CMD:" + command, (0,255,255), 0.36)
    try:
        cmdline_ctrl(command)
    except Exception as e:
        logger.error(f"[app.handle_command] error: {e}")
    return jsonify({"status": "success", "message": "Command received"})

# 音频文件管理路由
@app.route('/getAudioFiles', methods=['GET'])
def get_audio_files():
    files = [f for f in os.listdir(UPLOAD_FOLDER) if os.path.isfile(os.path.join(UPLOAD_FOLDER, f)) and (f.endswith('.mp3') or f.endswith('.wav'))]
    return jsonify(files)

@app.route('/uploadAudio', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file:
        filename = secure_filename(file.filename)
        file.save(os.path.join(UPLOAD_FOLDER, filename))
        return jsonify({'success': 'File uploaded successfully'})

@app.route('/playAudio', methods=['POST'])
def play_audio():
    audio_file = request.form['audio_file']
    logger.debug(f"播放音频文件: {thisPath}/sounds/others/{audio_file}")
    audio_ctrl.play_audio_thread(thisPath + '/sounds/others/' + audio_file)
    return jsonify({'success': 'Audio is playing'})

@app.route('/stop_audio', methods=['POST'])
def audio_stop():
    audio_ctrl.stop()
    return jsonify({'success': 'Audio stop'})

@app.route('/settings/<path:filename>')
def serve_static_settings(filename):
    return send_from_directory('templates', filename)

# WebSocket处理
@socketio.on('json', namespace='/json')
def handle_socket_json(json):
    try:
        base.base_json_ctrl(json)
    except Exception as e:
        logger.error(f"处理JSON数据错误: {e}")
        return

# 更新WebSocket数据
def update_data_websocket_single():
    try:
        socket_data = {
            f['fb']['picture_size']:si.pictures_size,
            f['fb']['video_size']:  si.videos_size,
            f['fb']['cpu_load']:    si.cpu_load,
            f['fb']['cpu_temp']:    si.cpu_temp,
            f['fb']['ram_usage']:   si.ram,
            f['fb']['wifi_rssi']:   si.wifi_rssi,

            f['fb']['led_mode']:    cvf.cv_light_mode,
            f['fb']['detect_type']: cvf.cv_mode,
            f['fb']['detect_react']:cvf.detection_reaction_mode,
            f['fb']['pan_angle']:   cvf.pan_angle,
            f['fb']['tilt_angle']:  cvf.tilt_angle,
            f['fb']['base_voltage']:base.base_data['v'],
            f['fb']['video_fps']:   cvf.video_fps,
            f['fb']['cv_movtion_mode']: cvf.cv_movtion_lock,
            f['fb']['base_light']:  base.base_light_status
        }
        socketio.emit('update', socket_data, namespace='/ctrl')
    except Exception as e:
        logger.error(f"[app.update_data_websocket_single] error: {e}")

# 数据更新循环
def update_data_loop():
    base.base_oled(2, "F/J:5000/8888")
    start_time = time.time()
    time.sleep(1)
    while 1:
        update_data_websocket_single()
        eth0 = si.eth0_ip
        wlan = si.wlan_ip
        if eth0:
            base.base_oled(0, f"E:{eth0}")
        else:
            base.base_oled(0, f"E: No Ethernet")
        if wlan:
            base.base_oled(1, f"W:{wlan}")
        else:
            base.base_oled(1, f"W: NO {si.net_interface}")
        elapsed_time = time.time() - start_time
        hours = int(elapsed_time // 3600)
        minutes = int((elapsed_time % 3600) // 60)
        seconds = int(elapsed_time % 60)
        base.base_oled(3, f"{si.wifi_mode} {hours:02d}:{minutes:02d}:{seconds:02d} {si.wifi_rssi}dBm")
        time.sleep(5)

# 基础数据更新循环
def base_data_loop():
    sensor_interval = 1
    sensor_read_time = time.time()
    while True:
        cvf.update_base_data(base.feedback_data())

        # 获取传感器数据
        if base.extra_sensor:
            if time.time() - sensor_read_time > sensor_interval:
                base.rl.read_sensor_data()
                sensor_read_time = time.time()
        
        # 获取激光雷达数据
        if base.use_lidar:
            base.rl.lidar_data_recv()
        
        time.sleep(0.025)

# WebSocket命令处理
@socketio.on('message', namespace='/ctrl')
def handle_socket_cmd(message):
    try:
        json_data = json.loads(message)
    except json.JSONDecodeError:
        logger.error("解析JSON错误.[app.handle_socket_cmd]")
        return
    cmd_a = float(json_data.get("A", 0))
    if cmd_a in cmd_actions:
        cmd_actions[cmd_a]()
    else:
        pass
    if cmd_a in cmd_feedback_actions:
        threading.Thread(target=update_data_websocket_single, daemon=True).start()

# 启动命令
def cmd_on_boot():
    cmd_list = [
        'base -c {"T":142,"cmd":50}',   # 设置反馈间隔
        'base -c {"T":131,"cmd":1}',    # 开启串口反馈流
        'base -c {"T":143,"cmd":0}',    # 关闭串口回显
        'base -c {{"T":4,"cmd":{}}}'.format(f['base_config']['module_type']),      # 选择模块 - 0:无 1:RoArm-M2-S 2:云台
        'base -c {"T":300,"mode":0,"mac":"EF:EF:EF:EF:EF:EF"}',  # 基础不会被esp-now广播命令控制，但仍可接收广播消息
        'send -a -b'    # 添加广播MAC地址到对等点
    ]
    logger.debug('base -c {{"T":4,"cmd":{}}}'.format(f['base_config']['module_type']))
    for i in range(0, len(cmd_list)):
        cmdline_ctrl(cmd_list[i])
        cvf.info_update(cmd_list[i], (0,255,255), 0.36)
    set_version(f['base_config']['main_type'], f['base_config']['module_type'])

# 主程序入口
if __name__ == "__main__":
    # 关闭灯光
    base.lights_ctrl(255, 255)
    
    # 播放启动音频
    audio_ctrl.play_random_audio("robot_started", False)

    # 更新视频和图片大小
    si.update_folder(thisPath)

    # 云台/机械臂向前看
    if f['base_config']['module_type'] == 1:
        base.base_json_ctrl({"T":f['cmd_config']['cmd_arm_ctrl_ui'],"E":f['args_config']['arm_default_e'],"Z":f['args_config']['arm_default_z'],"R":f['args_config']['arm_default_r']})
    else:
        base.gimbal_ctrl(0, 0, 200, 10)

    # 启动反馈循环
    si.start()
    si.resume()
    data_update_thread = threading.Thread(target=update_data_loop, daemon=True)
    data_update_thread.start()

    # 启动基础数据更新
    base_update_thread = threading.Thread(target=base_data_loop, daemon=True)
    base_update_thread.start()

    # 关闭灯光
    base.lights_ctrl(0, 0)
    cmd_on_boot()

    # 运行主Web应用
    socketio.run(app, host='0.0.0.0', port=5000, allow_unsafe_werkzeug=True)
