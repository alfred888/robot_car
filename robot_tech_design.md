# 机器人技术设计文档

## 1. 项目概述
### 1.1 项目目标
### 1.2 系统架构
### 1.3 技术栈选择

## 2. 系统设计
### 2.1 硬件架构
- 主控制器
- 传感器系统
- 执行器系统
- 电源系统

### 2.2 软件架构
- 操作系统
- 驱动层
- 控制层
- 应用层

### 2.3 系统环境性能要求

#### 2.3.1 大脑模块（Ubuntu服务器）
- **硬件配置**
  - CPU: Intel/AMD 8核心以上
  - GPU: NVIDIA RTX 4090 (24GB显存)
  - 内存: 32GB DDR4
  - 存储: 1TB NVMe SSD
  - 网络: 千兆以太网

- **软件环境**
  - 操作系统: Ubuntu 24.02 LTS
  - CUDA: 12.0+
  - Python: 3.10+
  - 系统服务:
    - Docker 24.0+
    - NVIDIA驱动 535+
    - CUDA Toolkit 12.0+

</edit>

#### 2.3.2 身体模块（树莓派）
- **基本信息**
  - 型号: Raspberry Pi 5 Model B Rev 1.0
  - 序列号: 0a4816057272f66a
  - 主机名: ugvrpi
  - 操作系统: Debian GNU/Linux 12 (bookworm)
  - 内核版本: 6.6.20+rpt-rpi-2712

- **硬件配置**
  - CPU: Broadcom BCM2711 (4核)
  - 内存: 4GB
  - 存储: 235GB
  - GPU: VideoCore VI
  - 网络: 2.4GHz/5GHz WiFi + 千兆以太网
  - 扩展板: 
    - 电机驱动板
    - 摄像头模块 (IMX219)
    - 音频模块

</edit>

- **软件环境**
  - 操作系统: Raspberry Pi OS (64位)
  - Python: 3.10+
  - 系统服务:
    - OpenCV
    - ALSA音频系统
    - GPIO库
    - Camera驱动

- **性能指标**
  - CPU利用率: 峰值70%
  - 内存使用: 峰值4GB
  - 摄像头帧率: 30fps@640x480
  - 音频采样率: 16kHz
  - 电机控制延迟: <50ms
  - 网络延迟: <100ms

- **系统监控指标**
  - CPU温度: <80°C
  - 内存使用率: <80%
  - 存储使用率: <70%
  - 网络带宽: 峰值50Mbps
  - 电池电量: >20%
  - 系统负载: <3.0

- **关键进程**
  - 主控制进程
  - 摄像头采集进程
  - 音频处理进程
  - 电机控制进程
  - WebSocket客户端进程

### 2.4 日志系统设计

#### 2.4.1 日志配置概述
系统采用Python标准库logging模块实现日志功能，通过YAML配置文件进行集中管理。日志系统具有以下特点：
- 分级日志（DEBUG/INFO/ERROR）
- 日志轮转（防止日志文件过大）
- 模块化配置（不同模块独立配置）
- 错误日志单独存储
- 支持控制台和文件输出

#### 2.4.2 大脑模块日志配置
- **日志格式**
  - 标准格式：`%(asctime)s [%(levelname)s] %(name)s: %(message)s`
  - 详细格式：`%(asctime)s [%(levelname)s] %(name)s [%(filename)s:%(lineno)d] - %(message)s`

- **日志处理器**
  - 控制台输出：INFO级别，标准格式
  - 普通日志文件：DEBUG级别，详细格式，10MB/文件，保留5个备份
  - 错误日志文件：ERROR级别，详细格式，10MB/文件，保留3个备份

- **模块日志**
  - brain：大脑核心模块
  - vision：视觉处理模块
  - speech：语音处理模块
  - nlp：语言处理模块
  - websocket：通信模块

#### 2.4.3 身体模块日志配置
- **日志格式**
  - 与大脑模块保持一致，便于统一分析

- **日志处理器**
  - 控制台输出：INFO级别，标准格式
  - 普通日志文件：DEBUG级别，详细格式，5MB/文件，保留3个备份
  - 错误日志文件：ERROR级别，详细格式，5MB/文件，保留2个备份

- **模块日志**
  - body：身体核心模块
  - hardware：硬件控制模块
  - camera：摄像头模块
  - audio：音频处理模块
  - motors：电机控制模块
  - websocket：通信模块

#### 2.4.4 日志使用规范
1. **日志级别使用**
   - DEBUG：详细的调试信息
   - INFO：正常的操作信息
   - ERROR：错误信息，需要关注

2. **日志内容规范**
   - 时间戳：精确到秒
   - 模块名：使用配置文件中定义的模块名
   - 消息内容：清晰、具体、可追踪

3. **日志文件管理**
   - 定期检查日志文件大小
   - 重要日志及时备份
   - 定期清理过期日志

4. **错误日志处理**
   - 错误日志单独存储
   - 包含完整的错误堆栈
   - 记录错误发生时的系统状态

### 2.5 项目结构
```
robot_car/
├── big_brain/                    # 大脑模块（部署在Ubuntu服务器）
│   ├── config/                   # 配置文件
│   │   ├── server_config.yaml    # 服务器配置
│   │   └── model_config.yaml     # 模型配置
│   ├── models/                   # 大模型存储目录
│   │   ├── vision/              # 视觉模型
│   │   │   ├── yolo/           # YOLO系列模型
│   │   │   └── clip/           # CLIP模型
│   │   ├── speech/             # 语音模型
│   │   │   ├── whisper/        # Whisper模型
│   │   │   └── tts/            # 语音合成模型
│   │   ├── nlp/                # 语言模型
│   │   │   ├── llm/            # 大语言模型
│   │   │   └── embeddings/     # 嵌入模型
│   │   └── cache/              # 模型缓存
│   ├── src/
│   │   ├── core/                # 核心功能
│   │   │   ├── brain.py         # 大脑主控
│   │   │   └── state.py         # 状态管理
│   │   ├── plugins/             # 插件系统
│   │   │   ├── vision/          # 视觉插件
│   │   │   ├── speech/          # 语音插件
│   │   │   └── nlp/             # 语言处理插件
│   │   ├── services/            # 服务层
│   │   │   ├── vision_service.py
│   │   │   ├── speech_service.py
│   │   │   └── nlp_service.py
│   │   └── utils/               # 工具函数
│   ├── tests/                   # 测试文件
│   ├── logs/                    # 日志文件
│   └── requirements.txt         # 依赖管理
│
├── robot_body/                  # 身体模块（部署在树莓派）
│   ├── config/                  # 配置文件
│   │   ├── pi_config.yaml      # 树莓派配置
│   │   └── hardware_config.yaml # 硬件配置
│   ├── src/
│   │   ├── core/               # 核心功能
│   │   │   ├── body.py         # 身体主控
│   │   │   └── little_brain.py # 本地小脑
│   │   ├── modules/            # 功能模块
│   │   │   ├── vision/         # 视觉模块
│   │   │   ├── speech/         # 语音模块
│   │   │   ├── movement/       # 运动模块
│   │   │   └── audio/          # 音频模块
│   │   ├── hardware/           # 硬件驱动
│   │   │   ├── motors/         # 电机控制
│   │   │   ├── sensors/        # 传感器
│   │   │   └── camera/         # 摄像头
│   │   └── utils/              # 工具函数
│   ├── tests/                  # 测试文件
│   ├── logs/                   # 日志文件
│   └── requirements.txt        # 依赖管理
│
├── common/                     # 共享模块
│   ├── protocols/             # 通信协议
│   │   ├── websocket/         # WebSocket协议
│   │   └── message/           # 消息格式
│   ├── utils/                 # 通用工具
│   └── constants/             # 常量定义
│
├── docs/                      # 文档
│   ├── api/                   # API文档
│   ├── setup/                 # 部署文档
│   └── development/           # 开发文档
│
├── scripts/                   # 脚本文件
│   ├── deploy/               # 部署脚本
│   ├── setup/                # 环境配置脚本
│   └── tools/                # 工具脚本
│
├── .gitignore
├── README.md
└── docker-compose.yml        # Docker配置
```

## 3. 功能模块
### 3.1 运动控制
### 3.2 传感器数据处理
### 3.3 导航系统
### 3.4 任务规划

## 4. 接口设计
### 4.1 硬件接口
### 4.2 软件接口
### 4.3 通信协议

## 5. 安全设计
### 5.1 硬件安全
### 5.2 软件安全
### 5.3 应急处理

## 6. 测试计划
### 6.1 单元测试
### 6.2 集成测试
### 6.3 系统测试

## 7. 部署方案
### 7.1 环境要求
### 7.2 部署步骤
### 7.3 维护计划

## 8. 项目时间线
### 8.1 开发阶段
### 8.2 测试阶段
### 8.3 部署阶段

## 9. 风险评估
### 9.1 技术风险
### 9.2 项目风险
### 9.3 应对策略 