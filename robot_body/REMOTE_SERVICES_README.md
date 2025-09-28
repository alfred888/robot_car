# 机器人远程服务完整指南

## 概述

本项目为iOS app提供了完整的远程服务功能，包括：

- 🎥 **远程视频** - 实时视频流传输和控制
- 🎤 **语音聊天** - 双向语音对话功能
- 🎯 **云台控制** - 精确的云台方向控制
- 🔒 **安全认证** - 完整的身份验证和权限管理

## 服务架构

```
📱 iOS App
    ↓
🌐 统一API (端口 8000)
    ↓
┌─────────────────────────────────┐
│  🎥 视频聊天服务 (8001)          │
│  🎤 音频聊天服务 (8002)          │
│  🎯 云台控制服务 (8003)          │
│  📊 服务管理器 (9000)            │
└─────────────────────────────────┘
    ↓
🤖 机器人硬件
```

## 快速开始

### 1. 启动所有服务

```bash
# 进入机器人目录
cd /home/ws/robot_car/robot_body

# 启动统一API和所有远程服务
python3 start_unified_remote_services.py --enable-manager --auto-start-services

# 或者只启动统一API
python3 start_unified_remote_services.py
```

### 2. 启动单个服务

```bash
# 只启动视频聊天服务
python3 start_remote_services.py --service video

# 只启动语音聊天服务
python3 start_remote_services.py --service audio

# 只启动云台控制服务
python3 start_remote_services.py --service gimbal
```

### 3. 自定义端口

```bash
# 使用自定义端口启动服务管理器
python3 start_remote_services.py --port 9999
```

## 服务端口列表

| 服务名称 | 端口 | 描述 |
|---------|------|------|
| 服务管理器 | 9000 | 统一管理所有远程服务 |
| 视频聊天 | 8001 | WebRTC视频通话服务 |
| 语音聊天 | 8002 | 双向语音对话服务 |
| 云台控制 | 8003 | 云台方向控制服务 |

## API 文档

### 服务管理器 API (端口: 9000)

#### 健康检查
```http
GET /health
```
返回管理器健康状态和系统信息。

#### 获取所有服务状态
```http
GET /services
```
返回所有注册服务的状态信息。

#### 启动服务
```http
POST /services/{service_name}/start
```
启动指定的服务。

#### 停止服务
```http
POST /services/{service_name}/stop
```
停止指定的服务。

#### 重启服务
```http
POST /services/{service_name}/restart
```
重启指定的服务。

#### 服务发现
```http
GET /discovery
```
获取所有运行中服务的地址和状态。

---

### 视频聊天服务 API (端口: 8001)

#### WebRTC连接

**创建Offer**
```http
POST /offer
Content-Type: application/json

{
  "client_id": "unique_client_id",
  "offer": {
    "sdp": "webrtc_offer_sdp",
    "type": "offer"
  }
}
```

**处理Answer**
```http
POST /answer
Content-Type: application/json

{
  "client_id": "unique_client_id", 
  "answer": {
    "sdp": "webrtc_answer_sdp",
    "type": "answer"
  }
}
```

**添加ICE Candidate**
```http
POST /candidate
Content-Type: application/json

{
  "client_id": "unique_client_id",
  "candidate": {
    "candidate": "ice_candidate_string",
    "sdpMLineIndex": 0
  }
}
```

#### WebSocket事件

**连接建立**
```javascript
// 客户端连接
socket.emit('connect');

// 服务器响应
socket.on('connected', function(data) {
  console.log('Client ID:', data.client_id);
});
```

**WebRTC信令**
```javascript
// 发送offer
socket.emit('webrtc_offer', {
  offer: {
    sdp: "...",
    type: "offer"
  }
});

// 接收answer
socket.on('webrtc_answer', function(data) {
  // 处理answer
});

// 发送ICE candidate
socket.emit('webrtc_candidate', {
  candidate: {
    candidate: "...",
    sdpMLineIndex: 0
  }
});
```

---

### 语音聊天服务 API (端口: 8002)

#### HTTP接口

**让机器人说话**
```http
POST /speak
Content-Type: application/json

{
  "text": "你好，我是机器人！"
}
```

**语音识别**
```http
POST /recognize
Content-Type: application/json

{
  "audio": "base64_encoded_audio_data"
}
```

#### WebSocket事件

**开始说话**
```javascript
socket.emit('start_talking');
```

**停止说话**
```javascript
socket.emit('stop_talking');
```

**发送音频数据**
```javascript
socket.emit('audio_data', {
  audio: "base64_encoded_audio"
});
```

**发送文字消息**
```javascript
socket.emit('send_message', {
  text: "Hello robot!"
});
```

**接收语音识别结果**
```javascript
socket.on('speech_recognized', function(data) {
  console.log('识别结果:', data.text);
});
```

**接收机器人回复**
```javascript
socket.on('robot_reply', function(data) {
  console.log('机器人回复:', data.text);
});
```

---

### 云台控制服务 API (端口: 8003)

#### 位置控制

**获取当前位置**
```http
GET /position
```

**设置绝对位置**
```http
POST /position
Content-Type: application/json

{
  "pan": 45.0,        // 水平角度 (-180 to 180)
  "tilt": 20.0,       // 垂直角度 (-30 to 30)
  "speed": 200,       // 移动速度
  "smoothness": 10    // 平滑度
}
```

**相对移动**
```http
POST /move
Content-Type: application/json

{
  "pan_delta": 10.0,   // 水平移动增量
  "tilt_delta": -5.0,  // 垂直移动增量
  "speed": 150
}
```

#### 预设位置

**移动到预设位置**
```http
POST /preset/{preset_name}
Content-Type: application/json

{
  "speed": 200
}
```

可用预设位置：
- `home` - 中心位置 (0°, 0°)
- `left` - 左侧 (-90°, 0°)
- `right` - 右侧 (90°, 0°)
- `up` - 向上 (0°, 20°)
- `down` - 向下 (0°, -20°)
- `front_left` - 左前方 (-45°, 0°)
- `front_right` - 右前方 (45°, 0°)
- `back_left` - 左后方 (-135°, 0°)
- `back_right` - 右后方 (135°, 0°)

**获取所有预设**
```http
GET /presets
```

**保存当前位置为预设**
```http
POST /presets
Content-Type: application/json

{
  "name": "my_preset"
}
```

#### 控制命令

**停止移动**
```http
POST /stop
```

**获取限制信息**
```http
GET /limits
```

#### WebSocket事件

**移动到指定位置**
```javascript
socket.emit('move_to', {
  pan: 45.0,
  tilt: 20.0,
  speed: 200
});
```

**相对移动**
```javascript
socket.emit('move_delta', {
  pan_delta: 10.0,
  tilt_delta: -5.0,
  speed: 150
});
```

**前往预设位置**
```javascript
socket.emit('goto_preset', {
  preset: 'home',
  speed: 200
});
```

**停止移动**
```javascript
socket.emit('stop');
```

**接收位置变化**
```javascript
socket.on('position_changed', function(data) {
  console.log('当前位置:', data.current);
  console.log('目标位置:', data.target);
  console.log('是否移动中:', data.is_moving);
});
```

**接收到达目标位置**
```javascript
socket.on('position_reached', function(data) {
  console.log('已到达位置:', data.position);
});
```

## 客户端示例

### JavaScript WebSocket客户端

```javascript
// 连接视频聊天服务
const videoSocket = io('http://robot_ip:8001');

// 连接语音聊天服务  
const audioSocket = io('http://robot_ip:8002');

// 连接云台控制服务
const gimbalSocket = io('http://robot_ip:8003');

// 连接服务管理器
const managerSocket = io('http://robot_ip:9000');

// 示例：控制云台移动
gimbalSocket.emit('move_to', {
  pan: 90,
  tilt: 0,
  speed: 200
});

// 示例：让机器人说话
fetch('http://robot_ip:8002/speak', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({text: '你好！'})
});
```

### Python客户端示例

```python
import requests
import socketio

# 连接云台控制服务
sio = socketio.Client()
sio.connect('http://robot_ip:8003')

# 移动云台
sio.emit('move_to', {
    'pan': 45.0,
    'tilt': 20.0, 
    'speed': 200
})

# HTTP请求示例
response = requests.post('http://robot_ip:8002/speak', 
                        json={'text': '机器人你好！'})
print(response.json())
```

## 移动APP集成指南

### Android集成

1. **添加WebRTC依赖**
```gradle
implementation 'org.webrtc:google-webrtc:1.0.32006'
```

2. **WebSocket连接**
```java
IO.Options options = new IO.Options();
Socket socket = IO.socket("http://robot_ip:8001", options);
socket.connect();
```

3. **WebRTC视频通话**
```java
// 创建PeerConnection
PeerConnectionFactory factory = PeerConnectionFactory.builder().createPeerConnectionFactory();
PeerConnection peerConnection = factory.createPeerConnection(iceServers, observer);

// 发送offer给机器人
socket.emit("webrtc_offer", offerData);
```

### iOS集成

1. **添加WebRTC框架**
```swift
import WebRTC
```

2. **Socket.IO连接**
```swift
let manager = SocketManager(socketURL: URL(string: "http://robot_ip:8001")!)
let socket = manager.defaultSocket
socket.connect()
```

3. **云台控制**
```swift
socket.emit("move_to", ["pan": 45.0, "tilt": 20.0, "speed": 200])
```

## 错误处理

### 常见错误码

| 错误码 | 说明 | 解决方案 |
|-------|------|---------|
| 404 | 服务未找到 | 检查服务是否启动 |
| 400 | 参数错误 | 检查请求参数格式 |
| 500 | 服务器内部错误 | 查看服务器日志 |
| 连接超时 | 网络连接问题 | 检查网络和防火墙设置 |

### 调试技巧

1. **查看服务状态**
```bash
curl http://robot_ip:9000/services
```

2. **查看服务健康状态**
```bash
curl http://robot_ip:9000/health
```

3. **查看日志**
```bash
# 查看服务启动日志
python3 start_remote_services.py --auto-start

# 服务会输出详细的运行日志
```

## 性能优化建议

1. **网络优化**
   - 使用有线连接获得更稳定的性能
   - 确保足够的带宽（建议至少10Mbps）
   - 优化WiFi信号强度

2. **硬件优化**
   - 使用高性能存储卡（Class 10或更高）
   - 确保充足的散热
   - 监控CPU和内存使用率

3. **服务配置**
   - 根据需要调整视频质量
   - 优化音频采样率
   - 合理设置云台移动速度

## 安全注意事项

1. **网络安全**
   - 在生产环境中使用HTTPS/WSS
   - 设置防火墙规则
   - 使用VPN进行远程访问

2. **访问控制**
   - 实现身份验证机制
   - 限制同时连接数
   - 记录访问日志

3. **数据保护**
   - 不在日志中记录敏感信息
   - 定期更新依赖包
   - 监控异常访问

## 故障排除

### 服务无法启动

1. **检查端口占用**
```bash
netstat -tulpn | grep :8001
```

2. **检查权限**
```bash
# 确保有执行权限
chmod +x start_remote_services.py
```

3. **检查依赖**
```bash
pip3 install -r requirements.txt
```

### WebRTC连接失败

1. **检查STUN服务器**
   - 确保可以访问Google STUN服务器
   - 如需要，配置本地STUN/TURN服务器

2. **防火墙设置**
   - 开放必要的端口范围
   - 检查NAT设置

### 音频问题

1. **检查音频设备**
```bash
aplay -l  # 列出播放设备
arecord -l  # 列出录音设备
```

2. **调整音频配置**
   - 检查音量设置
   - 验证音频驱动

## 扩展开发

### 添加新服务

1. **创建服务类**
```python
class MyCustomService:
    def __init__(self, port):
        self.port = port
        # 初始化代码
    
    def start_service(self):
        # 启动服务
        pass
    
    def stop_service(self):
        # 停止服务
        pass
```

2. **注册到管理器**
```python
# 在 RemoteServiceManager._register_services() 中添加
custom_service = MyCustomService(8004)
self.services["custom"] = ServiceInfo(
    name="custom",
    service_instance=custom_service,
    port=8004,
    description="自定义服务"
)
```

### 自定义协议

1. **扩展WebSocket事件**
```python
@self.socketio.on('custom_event')
def handle_custom_event(data):
    # 处理自定义事件
    pass
```

2. **添加HTTP端点**
```python
@self.app.route('/custom', methods=['POST'])
def custom_endpoint():
    # 处理自定义HTTP请求
    pass
```

## 支持和反馈

如有问题或建议，请：

1. 查看详细日志输出
2. 检查网络连接状态
3. 验证硬件功能正常
4. 参考示例代码和文档

---

## iOS App 详细集成指南

### 项目配置

#### 1. 添加依赖包

在Xcode中通过Package Manager添加以下依赖：

```
https://github.com/Alamofire/Alamofire (5.0.0+)
https://github.com/socketio/socket.io-client-swift (16.0.0+)
https://github.com/stasel/WebRTC (1.1.0+)
```

#### 2. Info.plist配置

```xml
<!-- 允许HTTP连接（仅开发环境） -->
<key>NSAppTransportSecurity</key>
<dict>
    <key>NSAllowsArbitraryLoads</key>
    <true/>
</dict>

<!-- 相机和麦克风权限 -->
<key>NSCameraUsageDescription</key>
<string>需要相机权限进行视频通话</string>
<key>NSMicrophoneUsageDescription</key>
<string>需要麦克风权限进行语音对话</string>
```

### 核心代码实现

#### 1. API管理器 (RobotAPIManager.swift)

```swift
import Foundation
import Alamofire

class RobotAPIManager {
    static let shared = RobotAPIManager()

    private let baseURL = "http://192.168.1.100:8000" // 替换为机器人IP
    private var jwtToken: String?
    private var sessionId: String?

    private init() {}

    // 登录认证
    func login(completion: @escaping (Result<LoginResponse, Error>) -> Void) {
        let parameters: [String: Any] = [
            "app_id": "ios_app_v1",
            "api_key": "ios_secure_key_2024",
            "device_id": UIDevice.current.identifierForVendor?.uuidString ?? UUID().uuidString,
            "device_name": UIDevice.current.name,
            "device_type": "iOS"
        ]

        AF.request("\(baseURL)/auth/login",
                  method: .post,
                  parameters: parameters,
                  encoding: JSONEncoding.default)
        .validate()
        .responseDecodable(of: LoginResponse.self) { response in
            switch response.result {
            case .success(let loginResponse):
                self.jwtToken = loginResponse.jwtToken
                self.sessionId = loginResponse.sessionId
                completion(.success(loginResponse))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }

    // 通用认证请求方法
    private func authenticatedRequest<T: Codable>(
        _ url: String,
        method: HTTPMethod = .get,
        parameters: [String: Any]? = nil,
        responseType: T.Type,
        completion: @escaping (Result<T, Error>) -> Void
    ) {
        guard let token = jwtToken else {
            completion(.failure(APIError.notAuthenticated))
            return
        }

        let headers: HTTPHeaders = [
            "Authorization": "Bearer \(token)",
            "Content-Type": "application/json"
        ]

        AF.request(url,
                  method: method,
                  parameters: parameters,
                  encoding: JSONEncoding.default,
                  headers: headers)
        .validate()
        .responseDecodable(of: T.self) { response in
            completion(response.result)
        }
    }
}

// 数据模型
struct LoginResponse: Codable {
    let success: Bool
    let sessionId: String
    let jwtToken: String
    let permissions: [String]
    let services: [String: Int]
    let expiresIn: Int

    enum CodingKeys: String, CodingKey {
        case success
        case sessionId = "session_id"
        case jwtToken = "jwt_token"
        case permissions
        case services
        case expiresIn = "expires_in"
    }
}

enum APIError: Error {
    case notAuthenticated
    case invalidResponse
    case networkError(String)
}
```

#### 2. 云台控制扩展

```swift
extension RobotAPIManager {

    // 移动到指定位置
    func moveGimbalTo(pan: Double, tilt: Double, speed: Int = 200,
                      completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = [
            "pan": pan,
            "tilt": tilt,
            "speed": speed
        ]

        authenticatedRequest("\(baseURL)/gimbal/position",
                           method: .post,
                           parameters: parameters,
                           responseType: BasicResponse.self) { result in
            switch result {
            case .success(_):
                completion(.success(()))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }

    // 相对移动
    func moveGimbalRelative(panDelta: Double, tiltDelta: Double, speed: Int = 200,
                           completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = [
            "pan_delta": panDelta,
            "tilt_delta": tiltDelta,
            "speed": speed
        ]

        authenticatedRequest("\(baseURL)/gimbal/move",
                           method: .post,
                           parameters: parameters,
                           responseType: BasicResponse.self) { result in
            switch result {
            case .success(_):
                completion(.success(()))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }

    // 移动到预设位置
    func moveToPreset(_ presetName: String, speed: Int = 200,
                     completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = ["speed": speed]

        authenticatedRequest("\(baseURL)/gimbal/preset/\(presetName)",
                           method: .post,
                           parameters: parameters,
                           responseType: BasicResponse.self) { result in
            switch result {
            case .success(_):
                completion(.success(()))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }

    // 开始扫描
    func startGimbalScan(type: ScanType = .horizontal,
                        completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = [
            "type": type.rawValue,
            "speed": 200,
            "range": 0.8
        ]

        authenticatedRequest("\(baseURL)/gimbal/scan",
                           method: .post,
                           parameters: parameters,
                           responseType: BasicResponse.self) { result in
            switch result {
            case .success(_):
                completion(.success(()))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
}

enum ScanType: String, CaseIterable {
    case horizontal = "horizontal"
    case vertical = "vertical"
    case full = "full"
}
```

#### 3. 语音控制扩展

```swift
extension RobotAPIManager {

    // 让机器人说话
    func speakText(_ text: String, completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = ["text": text]

        authenticatedRequest("\(baseURL)/audio/speak",
                           method: .post,
                           parameters: parameters,
                           responseType: BasicResponse.self) { result in
            switch result {
            case .success(_):
                completion(.success(()))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }

    // 语音识别
    func recognizeAudio(_ audioData: Data, completion: @escaping (Result<String, Error>) -> Void) {
        let base64Audio = audioData.base64EncodedString()
        let parameters: [String: Any] = ["audio": base64Audio]

        authenticatedRequest("\(baseURL)/audio/recognize",
                           method: .post,
                           parameters: parameters,
                           responseType: AudioRecognitionResponse.self) { result in
            switch result {
            case .success(let response):
                completion(.success(response.text))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
}

struct AudioRecognitionResponse: Codable {
    let status: String
    let text: String
}
```

#### 4. 综合控制扩展

```swift
extension RobotAPIManager {

    // 获取机器人状态
    func getRobotStatus(completion: @escaping (Result<RobotStatus, Error>) -> Void) {
        authenticatedRequest("\(baseURL)/robot/status",
                           responseType: RobotStatus.self,
                           completion: completion)
    }

    // 边说话边转向
    func sayAndLook(text: String, direction: String,
                   completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = [
            "command": "say_and_look",
            "params": [
                "text": text,
                "direction": direction
            ]
        ]

        authenticatedRequest("\(baseURL)/robot/control",
                           method: .post,
                           parameters: parameters,
                           responseType: BasicResponse.self) { result in
            switch result {
            case .success(_):
                completion(.success(()))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }

    // 启动巡逻模式
    func startPatrol(type: ScanType = .horizontal,
                    completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = [
            "command": "patrol",
            "params": ["type": type.rawValue]
        ]

        authenticatedRequest("\(baseURL)/robot/control",
                           method: .post,
                           parameters: parameters,
                           responseType: BasicResponse.self) { result in
            switch result {
            case .success(_):
                completion(.success(()))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
}

struct RobotStatus: Codable {
    let timestamp: Double
    let services: [String: ServiceStatus]
    let system: SystemInfo
}

struct ServiceStatus: Codable {
    let status: String
    let service: String?
}

struct SystemInfo: Codable {
    let cpuPercent: Double
    let memoryPercent: Double

    enum CodingKeys: String, CodingKey {
        case cpuPercent = "cpu_percent"
        case memoryPercent = "memory_percent"
    }
}

struct BasicResponse: Codable {
    let success: Bool
    let message: String?
}
```

### UI实现示例

#### 主控制界面 (MainViewController.swift)

```swift
import UIKit

class MainViewController: UIViewController {

    @IBOutlet weak var statusLabel: UILabel!
    @IBOutlet weak var connectButton: UIButton!
    @IBOutlet weak var speakTextField: UITextField!
    @IBOutlet weak var gimbalControlView: UIView!

    private let robotAPI = RobotAPIManager.shared
    private var isConnected = false

    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        setupGestureRecognizers()
    }

    private func setupUI() {
        statusLabel.text = "未连接"
        connectButton.setTitle("连接机器人", for: .normal)
    }

    private func setupGestureRecognizers() {
        // 平移手势控制云台
        let panGesture = UIPanGestureRecognizer(target: self, action: #selector(handleGimbalPan(_:)))
        gimbalControlView.addGestureRecognizer(panGesture)

        // 双击回到中心
        let doubleTapGesture = UITapGestureRecognizer(target: self, action: #selector(handleDoubleTap(_:)))
        doubleTapGesture.numberOfTapsRequired = 2
        gimbalControlView.addGestureRecognizer(doubleTapGesture)
    }

    // MARK: - 按钮响应

    @IBAction func connectButtonTapped(_ sender: UIButton) {
        if isConnected {
            logout()
        } else {
            login()
        }
    }

    @IBAction func speakButtonTapped(_ sender: UIButton) {
        guard let text = speakTextField.text, !text.isEmpty else { return }

        robotAPI.speakText(text) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success():
                    self?.showAlert(title: "成功", message: "机器人正在说话")
                case .failure(let error):
                    self?.showAlert(title: "错误", message: error.localizedDescription)
                }
            }
        }
    }

    @IBAction func presetButtonTapped(_ sender: UIButton) {
        let presets = ["home", "left", "right", "up", "down"]
        let alertController = UIAlertController(title: "选择预设位置", message: nil, preferredStyle: .actionSheet)

        for preset in presets {
            alertController.addAction(UIAlertAction(title: preset.capitalized, style: .default) { [weak self] _ in
                self?.moveToPreset(preset)
            })
        }

        alertController.addAction(UIAlertAction(title: "取消", style: .cancel))

        if let popover = alertController.popoverPresentationController {
            popover.sourceView = sender
            popover.sourceRect = sender.bounds
        }

        present(alertController, animated: true)
    }

    // MARK: - 手势处理

    @objc private func handleGimbalPan(_ gesture: UIPanGestureRecognizer) {
        let translation = gesture.translation(in: gimbalControlView)

        // 将手势转换为云台移动 (调整灵敏度)
        let panDelta = Double(translation.x) * 0.1
        let tiltDelta = Double(-translation.y) * 0.1

        if gesture.state == .ended {
            robotAPI.moveGimbalRelative(panDelta: panDelta, tiltDelta: tiltDelta) { result in
                // 移动完成
            }
            gesture.setTranslation(.zero, in: gimbalControlView)
        }
    }

    @objc private func handleDoubleTap(_ gesture: UITapGestureRecognizer) {
        moveToPreset("home")
    }

    // MARK: - 私有方法

    private func login() {
        statusLabel.text = "连接中..."
        connectButton.isEnabled = false

        robotAPI.login { [weak self] result in
            DispatchQueue.main.async {
                self?.connectButton.isEnabled = true

                switch result {
                case .success(let response):
                    self?.isConnected = true
                    self?.statusLabel.text = "已连接"
                    self?.connectButton.setTitle("断开连接", for: .normal)
                    self?.showAlert(title: "连接成功", message: "机器人已连接\n权限: \(response.permissions.joined(separator: ", "))")

                case .failure(let error):
                    self?.statusLabel.text = "连接失败"
                    self?.showAlert(title: "连接失败", message: error.localizedDescription)
                }
            }
        }
    }

    private func logout() {
        robotAPI.logout { [weak self] result in
            DispatchQueue.main.async {
                self?.isConnected = false
                self?.statusLabel.text = "未连接"
                self?.connectButton.setTitle("连接机器人", for: .normal)
            }
        }
    }

    private func moveToPreset(_ preset: String) {
        robotAPI.moveToPreset(preset) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success():
                    self?.showAlert(title: "成功", message: "移动到 \(preset) 位置")
                case .failure(let error):
                    self?.showAlert(title: "错误", message: error.localizedDescription)
                }
            }
        }
    }

    private func showAlert(title: String, message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "确定", style: .default))
        present(alert, animated: true)
    }
}
```

### 快速使用示例

#### 1. 基本控制流程

```swift
class QuickStartExample {

    func basicUsage() {
        let robotAPI = RobotAPIManager.shared

        // 1. 登录
        robotAPI.login { result in
            switch result {
            case .success(let response):
                print("登录成功，权限: \(response.permissions)")

                // 2. 控制云台
                robotAPI.moveToPreset("home") { _ in
                    print("移动到中心位置")
                }

                // 3. 让机器人说话
                robotAPI.speakText("你好，我是机器人") { _ in
                    print("机器人开始说话")
                }

                // 4. 获取机器人状态
                robotAPI.getRobotStatus { result in
                    switch result {
                    case .success(let status):
                        print("系统状态: CPU \(status.system.cpuPercent)%")
                    case .failure(let error):
                        print("获取状态失败: \(error)")
                    }
                }

            case .failure(let error):
                print("登录失败: \(error)")
            }
        }
    }
}
```

#### 2. 高级功能

```swift
func advancedFeatures() {
    let robotAPI = RobotAPIManager.shared

    // 综合控制：边说话边转向
    robotAPI.sayAndLook(text: "我正在向左看", direction: "left") { result in
        switch result {
        case .success():
            print("执行综合命令成功")
        case .failure(let error):
            print("执行失败: \(error)")
        }
    }

    // 启动巡逻模式
    robotAPI.startPatrol(type: .horizontal) { result in
        switch result {
        case .success():
            print("开始巡逻")
        case .failure(let error):
            print("巡逻启动失败: \(error)")
        }
    }

    // 精确云台控制
    robotAPI.moveGimbalTo(pan: 45.0, tilt: 20.0, speed: 300) { result in
        switch result {
        case .success():
            print("云台移动完成")
        case .failure(let error):
            print("云台移动失败: \(error)")
        }
    }
}
```

### 重要配置说明

#### 1. 机器人连接信息

```swift
// 在RobotAPIManager中修改这些配置
private let baseURL = "http://192.168.1.100:8000"  // 替换为你的机器人IP

// 认证信息
"app_id": "ios_app_v1"
"api_key": "ios_secure_key_2024"
```

#### 2. 可用的预设位置

- `home` - 中心位置 (0°, 0°)
- `left` - 左侧 (-90°, 0°)
- `right` - 右侧 (90°, 0°)
- `up` - 向上 (0°, 20°)
- `down` - 向下 (0°, -20°)
- `front_left` - 左前方 (-45°, 0°)
- `front_right` - 右前方 (45°, 0°)

#### 3. 扫描类型

- `horizontal` - 水平扫描
- `vertical` - 垂直扫描
- `full` - 全方位扫描

#### 4. 综合控制命令

- `say_and_look` - 边说话边转向
- `patrol` - 巡逻模式
- `interactive_mode` - 交互模式

### 调试提示

1. **网络连接**：确保iOS设备和机器人在同一网络
2. **IP地址**：检查机器人的实际IP地址
3. **端口访问**：确认防火墙未阻止端口8000
4. **权限检查**：验证app_id对应的权限范围
5. **错误处理**：查看错误信息了解具体问题

---

**版本**: 1.0.0
**更新日期**: 2024年
**兼容性**: Python 3.7+, 树莓派 4/5, iOS 13.0+