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

### 2.6 环境管理规范

#### 2.6.1 Conda 环境配置
- **环境命名规范**
  - 大脑模块：`robot_brain`
  - 身体模块：`robot_body`
  - 开发环境：`robot_dev`

- **环境文件位置**
  ```
  robot_car/
  ├── big_brain/
  │   └── environment.yml    # 大脑模块环境配置
  ├── robot_body/
  │   └── environment.yml    # 身体模块环境配置
  └── environment.yml        # 开发环境配置
  ```

- **环境文件格式**
  ```yaml
  name: robot_brain
  channels:
    - conda-forge
    - pytorch
    - nvidia
  dependencies:
    - python=3.10
    - pip
    - pip:
      - fastapi==0.109.0
      - uvicorn==0.27.0
      - pydantic==2.5.3
      - websockets==12.0
      - numpy==1.26.3
      - torch==2.1.2
      - torchvision==0.16.2
      - opencv-python==4.9.0.80
      - python-multipart==0.0.6
      - python-jose==3.3.0
      - passlib==1.7.4
      - bcrypt==4.1.2
      - python-dotenv==1.0.0
      - pyyaml==6.0.1
      - pytest==7.4.4
      - pytest-asyncio==0.23.3
      - pytest-cov==4.1.0
      - black==23.12.1
      - isort==5.13.2
      - mypy==1.8.0
      - flake8==7.0.0
  ```

#### 2.6.2 环境管理流程
1. **环境创建**
   ```bash
   # 创建大脑模块环境
   conda env create -f big_brain/environment.yml
   
   # 创建身体模块环境
   conda env create -f robot_body/environment.yml
   
   # 创建开发环境
   conda env create -f environment.yml
   ```

2. **环境激活**
   ```bash
   # 激活大脑模块环境
   conda activate robot_brain
   
   # 激活身体模块环境
   conda activate robot_body
   
   # 激活开发环境
   conda activate robot_dev
   ```

3. **环境更新**
   ```bash
   # 更新环境
   conda env update -f environment.yml
   
   # 导出环境
   conda env export > environment.yml
   ```

4. **环境清理**
   ```bash
   # 删除环境
   conda env remove -n robot_brain
   
   # 清理缓存
   conda clean -a
   ```

#### 2.6.3 依赖管理规范
1. **版本控制**
   - 所有依赖必须指定具体版本
   - 使用 `==` 固定版本号
   - 定期更新依赖版本

2. **依赖分类**
   - 核心依赖：项目必需的包
   - 开发依赖：测试、代码质量工具
   - 可选依赖：可选功能模块

3. **依赖更新流程**
   - 在开发环境中测试新版本
   - 更新环境文件
   - 提交版本更新
   - 更新文档

#### 2.6.4 环境变量管理
1. **环境变量文件**
   ```
   robot_car/
   ├── big_brain/
   │   └── .env.example    # 大脑模块环境变量示例
   ├── robot_body/
   │   └── .env.example    # 身体模块环境变量示例
   └── .env.example        # 开发环境变量示例
   ```

2. **环境变量规范**
   - 使用 `.env` 文件管理环境变量
   - 提供 `.env.example` 作为模板
   - 敏感信息使用环境变量
   - 不同环境使用不同配置

3. **环境变量使用**
   ```python
   from dotenv import load_dotenv
   import os
   
   # 加载环境变量
   load_dotenv()
   
   # 使用环境变量
   API_KEY = os.getenv("API_KEY")
   ```

#### 2.6.5 开发工具配置
1. **编辑器配置**
   - VSCode 设置
   - Python 插件
   - 代码格式化工具

2. **代码质量工具**
   - Black：代码格式化
   - isort：导入排序
   - mypy：类型检查
   - flake8：代码检查

3. **Git 配置**
   - 提交信息规范
   - 分支管理策略
   - 代码审查流程

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

## 约束说明

- **ugv_body 文件夹**：该文件夹包含机器人原有的代码，仅作为参考，禁止修改。任何新功能或修改应在其他模块中实现，以保持原有代码的完整性。 