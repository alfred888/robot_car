# iOS App 集成指南

## 概述

本指南详细说明如何在iOS app中集成机器人远程服务，包括认证、视频流、语音控制和云台操作。

## 1. 项目配置

### 添加依赖

在 `Package.swift` 或 Xcode 中添加以下依赖：

```swift
// Package.swift
dependencies: [
    .package(url: "https://github.com/socketio/socket.io-client-swift", from: "16.0.0"),
    .package(url: "https://github.com/stasel/WebRTC", from: "1.1.0"),
    .package(url: "https://github.com/Alamofire/Alamofire", from: "5.0.0")
]
```

### Info.plist 配置

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

## 2. 核心服务类

### RobotAPIManager - 主要API管理器

```swift
import Foundation
import Alamofire

class RobotAPIManager {
    static let shared = RobotAPIManager()

    private let baseURL = "http://192.168.1.100:8000" // 替换为你的机器人IP
    private var jwtToken: String?
    private var sessionId: String?

    private init() {}

    // MARK: - 认证

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

    func logout(completion: @escaping (Result<Void, Error>) -> Void) {
        guard let sessionId = sessionId else {
            completion(.failure(APIError.notAuthenticated))
            return
        }

        let headers: HTTPHeaders = [
            "X-Session-ID": sessionId
        ]

        AF.request("\(baseURL)/auth/logout",
                  method: .post,
                  headers: headers)
        .validate()
        .response { response in
            self.jwtToken = nil
            self.sessionId = nil

            if response.error == nil {
                completion(.success(()))
            } else {
                completion(.failure(response.error!))
            }
        }
    }

    // MARK: - 通用请求方法

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
        .responseDecodable(of: T.type) { response in
            completion(response.result)
        }
    }
}

// MARK: - 数据模型

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

### GimbalController - 云台控制

```swift
extension RobotAPIManager {

    // MARK: - 云台控制

    func getGimbalPosition(completion: @escaping (Result<GimbalPosition, Error>) -> Void) {
        authenticatedRequest("\(baseURL)/gimbal/position",
                           responseType: GimbalPositionResponse.self) { result in
            switch result {
            case .success(let response):
                completion(.success(response.current))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }

    func moveGimbalTo(pan: Double, tilt: Double, speed: Int = 200, completion: @escaping (Result<Void, Error>) -> Void) {
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

    func moveGimbalRelative(panDelta: Double, tiltDelta: Double, speed: Int = 200, completion: @escaping (Result<Void, Error>) -> Void) {
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

    func moveToPreset(_ presetName: String, speed: Int = 200, completion: @escaping (Result<Void, Error>) -> Void) {
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

    func startGimbalScan(type: ScanType = .horizontal, completion: @escaping (Result<Void, Error>) -> Void) {
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

    func sendGesture(_ gesture: GestureType, completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = ["gesture": gesture.rawValue]

        authenticatedRequest("\(baseURL)/gimbal/gesture",
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

// MARK: - 云台数据模型

struct GimbalPosition: Codable {
    let pan: Double
    let tilt: Double
}

struct GimbalPositionResponse: Codable {
    let current: GimbalPosition
    let target: GimbalPosition
    let isMoving: Bool

    enum CodingKeys: String, CodingKey {
        case current, target
        case isMoving = "is_moving"
    }
}

enum ScanType: String, CaseIterable {
    case horizontal = "horizontal"
    case vertical = "vertical"
    case full = "full"
}

enum GestureType: String, CaseIterable {
    case swipeLeft = "swipe_left"
    case swipeRight = "swipe_right"
    case swipeUp = "swipe_up"
    case swipeDown = "swipe_down"
    case tap = "tap"
    case pinch = "pinch"
    case doubleTap = "double_tap"
}
```

### AudioController - 语音控制

```swift
extension RobotAPIManager {

    // MARK: - 音频控制

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

    func getAudioConfig(completion: @escaping (Result<AudioConfig, Error>) -> Void) {
        authenticatedRequest("\(baseURL)/audio/config",
                           responseType: AudioConfig.self,
                           completion: completion)
    }

    func setAudioConfig(_ config: AudioConfigRequest, completion: @escaping (Result<AudioConfig, Error>) -> Void) {
        let parameters = try! JSONEncoder().encode(config)
        let dict = try! JSONSerialization.jsonObject(with: parameters) as! [String: Any]

        authenticatedRequest("\(baseURL)/audio/config",
                           method: .post,
                           parameters: dict,
                           responseType: AudioConfigResponse.self) { result in
            switch result {
            case .success(let response):
                completion(.success(response.config))
            case .failure(let error):
                completion(.failure(error))
            }
        }
    }
}

// MARK: - 音频数据模型

struct AudioRecognitionResponse: Codable {
    let status: String
    let text: String
}

struct AudioConfig: Codable {
    let sampleRate: Int
    let channels: Int
    let chunkSize: Int
    let supportedFormats: [String]
    let supportedLanguages: [String]

    enum CodingKeys: String, CodingKey {
        case sampleRate = "sample_rate"
        case channels
        case chunkSize = "chunk_size"
        case supportedFormats = "supported_formats"
        case supportedLanguages = "supported_languages"
    }
}

struct AudioConfigRequest: Codable {
    let sampleRate: Int?
    let channels: Int?
    let chunkSize: Int?

    enum CodingKeys: String, CodingKey {
        case sampleRate = "sample_rate"
        case channels
        case chunkSize = "chunk_size"
    }
}

struct AudioConfigResponse: Codable {
    let status: String
    let config: AudioConfig
}
```

### VideoController - 视频控制

```swift
extension RobotAPIManager {

    // MARK: - 视频控制

    func getVideoStreamInfo(completion: @escaping (Result<VideoStreamInfo, Error>) -> Void) {
        authenticatedRequest("\(baseURL)/video/stream/info",
                           responseType: VideoStreamInfo.self,
                           completion: completion)
    }

    func setVideoQuality(_ quality: VideoQuality, fps: Int = 30, completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = [
            "quality": quality.rawValue,
            "fps": fps,
            "resolution": quality.resolution
        ]

        authenticatedRequest("\(baseURL)/video/stream/quality",
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

    func takeSnapshot(completion: @escaping (Result<SnapshotInfo, Error>) -> Void) {
        authenticatedRequest("\(baseURL)/video/snapshot",
                           method: .post,
                           responseType: SnapshotInfo.self,
                           completion: completion)
    }
}

// MARK: - 视频数据模型

struct VideoStreamInfo: Codable {
    let activeConnections: Int
    let maxConnections: Int
    let supportedFormats: [String]
    let supportedResolutions: [Resolution]

    enum CodingKeys: String, CodingKey {
        case activeConnections = "active_connections"
        case maxConnections = "max_connections"
        case supportedFormats = "supported_formats"
        case supportedResolutions = "supported_resolutions"
    }
}

struct Resolution: Codable {
    let width: Int
    let height: Int
    let name: String
}

enum VideoQuality: String, CaseIterable {
    case low = "low"
    case medium = "medium"
    case high = "high"

    var resolution: [String: Int] {
        switch self {
        case .low:
            return ["width": 320, "height": 240]
        case .medium:
            return ["width": 640, "height": 480]
        case .high:
            return ["width": 1280, "height": 720]
        }
    }
}

struct SnapshotInfo: Codable {
    let status: String
    let filename: String
    let timestamp: Int
    let size: Int
}
```

### RobotController - 综合控制

```swift
extension RobotAPIManager {

    // MARK: - 综合控制

    func getRobotStatus(completion: @escaping (Result<RobotStatus, Error>) -> Void) {
        authenticatedRequest("\(baseURL)/robot/status",
                           responseType: RobotStatus.self,
                           completion: completion)
    }

    func sayAndLook(text: String, direction: String, completion: @escaping (Result<Void, Error>) -> Void) {
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

    func startPatrol(type: ScanType = .horizontal, completion: @escaping (Result<Void, Error>) -> Void) {
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

    func enterInteractiveMode(completion: @escaping (Result<Void, Error>) -> Void) {
        let parameters: [String: Any] = [
            "command": "interactive_mode",
            "params": [:]
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

// MARK: - 系统数据模型

struct RobotStatus: Codable {
    let timestamp: Double
    let services: [String: ServiceStatus]
    let system: SystemInfo
}

struct ServiceStatus: Codable {
    let status: String
    let service: String?
    let connections: Int?
    let clients: Int?
    let streaming: Bool?
}

struct SystemInfo: Codable {
    let cpuPercent: Double
    let memoryPercent: Double
    let diskUsage: Double
    let networkConnections: Int
    let updateTime: Double

    enum CodingKeys: String, CodingKey {
        case cpuPercent = "cpu_percent"
        case memoryPercent = "memory_percent"
        case diskUsage = "disk_usage"
        case networkConnections = "network_connections"
        case updateTime = "update_time"
    }
}

struct BasicResponse: Codable {
    let success: Bool
    let message: String?
    let error: String?
}
```

## 3. UI视图控制器示例

### MainViewController - 主控制器

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
    }

    private func setupUI() {
        statusLabel.text = "未连接"
        connectButton.setTitle("连接机器人", for: .normal)

        // 添加云台控制手势
        let panGesture = UIPanGestureRecognizer(target: self, action: #selector(handleGimbalPan(_:)))
        gimbalControlView.addGestureRecognizer(panGesture)

        let tapGesture = UITapGestureRecognizer(target: self, action: #selector(handleGimbalTap(_:)))
        gimbalControlView.addGestureRecognizer(tapGesture)
    }

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
        present(alertController, animated: true)
    }

    @IBAction func patrolButtonTapped(_ sender: UIButton) {
        robotAPI.startPatrol(type: .horizontal) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success():
                    self?.showAlert(title: "成功", message: "开始巡逻")
                case .failure(let error):
                    self?.showAlert(title: "错误", message: error.localizedDescription)
                }
            }
        }
    }

    // MARK: - 手势处理

    @objc private func handleGimbalPan(_ gesture: UIPanGestureRecognizer) {
        let translation = gesture.translation(in: gimbalControlView)
        let velocity = gesture.velocity(in: gimbalControlView)

        // 将手势转换为云台移动
        let panDelta = Double(translation.x) * 0.1
        let tiltDelta = Double(-translation.y) * 0.1

        if gesture.state == .ended {
            robotAPI.moveGimbalRelative(panDelta: panDelta, tiltDelta: tiltDelta) { result in
                // 处理结果
            }
            gesture.setTranslation(.zero, in: gimbalControlView)
        }
    }

    @objc private func handleGimbalTap(_ gesture: UITapGestureRecognizer) {
        // 双击回到中心位置
        if gesture.numberOfTapsRequired == 2 {
            moveToPreset("home")
        }
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
                    self?.showAlert(title: "连接成功", message: "机器人已连接")

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

### GimbalControlViewController - 专门的云台控制

```swift
import UIKit

class GimbalControlViewController: UIViewController {

    @IBOutlet weak var panSlider: UISlider!
    @IBOutlet weak var tiltSlider: UISlider!
    @IBOutlet weak var speedSlider: UISlider!
    @IBOutlet weak var panLabel: UILabel!
    @IBOutlet weak var tiltLabel: UILabel!
    @IBOutlet weak var speedLabel: UILabel!
    @IBOutlet weak var controlPadView: UIView!

    private let robotAPI = RobotAPIManager.shared
    private var currentPosition = GimbalPosition(pan: 0, tilt: 0)

    override func viewDidLoad() {
        super.viewDidLoad()
        setupUI()
        setupControlPad()
        updateCurrentPosition()
    }

    private func setupUI() {
        panSlider.minimumValue = -180
        panSlider.maximumValue = 180
        panSlider.value = 0

        tiltSlider.minimumValue = -30
        tiltSlider.maximumValue = 30
        tiltSlider.value = 0

        speedSlider.minimumValue = 50
        speedSlider.maximumValue = 500
        speedSlider.value = 200

        updateLabels()
    }

    private func setupControlPad() {
        // 添加方向按钮
        let directions = [
            ("↑", CGPoint(x: 0.5, y: 0.2)),
            ("↓", CGPoint(x: 0.5, y: 0.8)),
            ("←", CGPoint(x: 0.2, y: 0.5)),
            ("→", CGPoint(x: 0.8, y: 0.5)),
            ("🏠", CGPoint(x: 0.5, y: 0.5))
        ]

        for (title, position) in directions {
            let button = createDirectionButton(title: title, position: position)
            controlPadView.addSubview(button)
        }
    }

    private func createDirectionButton(title: String, position: CGPoint) -> UIButton {
        let button = UIButton(type: .system)
        button.setTitle(title, for: .normal)
        button.titleLabel?.font = UIFont.systemFont(ofSize: 24)
        button.backgroundColor = UIColor.systemBlue.withAlphaComponent(0.3)
        button.layer.cornerRadius = 25
        button.frame = CGRect(x: 0, y: 0, width: 50, height: 50)

        // 设置约束
        button.translatesAutoresizingMaskIntoConstraints = false
        NSLayoutConstraint.activate([
            button.widthAnchor.constraint(equalToConstant: 50),
            button.heightAnchor.constraint(equalToConstant: 50),
            button.centerXAnchor.constraint(equalTo: controlPadView.centerXAnchor,
                                          constant: (position.x - 0.5) * 200),
            button.centerYAnchor.constraint(equalTo: controlPadView.centerYAnchor,
                                          constant: (position.y - 0.5) * 200)
        ])

        button.addTarget(self, action: #selector(directionButtonTapped(_:)), for: .touchUpInside)
        return button
    }

    @objc private func directionButtonTapped(_ sender: UIButton) {
        guard let title = sender.titleLabel?.text else { return }

        let speed = Int(speedSlider.value)

        switch title {
        case "↑":
            robotAPI.moveGimbalRelative(panDelta: 0, tiltDelta: 15, speed: speed) { _ in }
        case "↓":
            robotAPI.moveGimbalRelative(panDelta: 0, tiltDelta: -15, speed: speed) { _ in }
        case "←":
            robotAPI.moveGimbalRelative(panDelta: -15, tiltDelta: 0, speed: speed) { _ in }
        case "→":
            robotAPI.moveGimbalRelative(panDelta: 15, tiltDelta: 0, speed: speed) { _ in }
        case "🏠":
            robotAPI.moveToPreset("home", speed: speed) { _ in }
        default:
            break
        }

        // 延迟更新位置
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            self.updateCurrentPosition()
        }
    }

    @IBAction func sliderValueChanged(_ sender: UISlider) {
        updateLabels()
    }

    @IBAction func moveToSliderPosition(_ sender: UIButton) {
        let pan = Double(panSlider.value)
        let tilt = Double(tiltSlider.value)
        let speed = Int(speedSlider.value)

        robotAPI.moveGimbalTo(pan: pan, tilt: tilt, speed: speed) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success():
                    self?.updateCurrentPosition()
                case .failure(let error):
                    self?.showAlert(title: "错误", message: error.localizedDescription)
                }
            }
        }
    }

    @IBAction func scanButtonTapped(_ sender: UIButton) {
        let alertController = UIAlertController(title: "选择扫描类型", message: nil, preferredStyle: .actionSheet)

        for scanType in ScanType.allCases {
            alertController.addAction(UIAlertAction(title: scanType.rawValue.capitalized, style: .default) { [weak self] _ in
                self?.startScan(type: scanType)
            })
        }

        alertController.addAction(UIAlertAction(title: "取消", style: .cancel))
        present(alertController, animated: true)
    }

    private func startScan(type: ScanType) {
        robotAPI.startGimbalScan(type: type) { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success():
                    self?.showAlert(title: "成功", message: "开始\(type.rawValue)扫描")
                case .failure(let error):
                    self?.showAlert(title: "错误", message: error.localizedDescription)
                }
            }
        }
    }

    private func updateCurrentPosition() {
        robotAPI.getGimbalPosition { [weak self] result in
            DispatchQueue.main.async {
                switch result {
                case .success(let position):
                    self?.currentPosition = position
                    self?.panSlider.value = Float(position.pan)
                    self?.tiltSlider.value = Float(position.tilt)
                    self?.updateLabels()
                case .failure(let error):
                    print("获取位置失败: \(error)")
                }
            }
        }
    }

    private func updateLabels() {
        panLabel.text = String(format: "Pan: %.1f°", panSlider.value)
        tiltLabel.text = String(format: "Tilt: %.1f°", tiltSlider.value)
        speedLabel.text = String(format: "Speed: %.0f", speedSlider.value)
    }

    private func showAlert(title: String, message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "确定", style: .default))
        present(alert, animated: true)
    }
}
```

## 4. 使用示例

### 基本使用流程

```swift
class ExampleUsage {

    func basicUsageExample() {
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

    func advancedUsageExample() {
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
    }
}
```

这个集成指南提供了完整的iOS app与机器人远程服务交互的实现，包括认证、云台控制、语音交互和系统监控等功能。你可以根据具体需求调整和扩展这些代码。