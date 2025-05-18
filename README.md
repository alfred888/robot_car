# 智能机器人项目

这是一个基于树莓派的智能机器人项目，采用分布式架构设计，包含大脑（big_brain）和身体（robot_body）两个主要模块。

## 系统要求

### 大脑模块（Ubuntu 24.02服务器）
- NVIDIA RTX 4090 GPU
- CUDA 12.0+
- Python 3.10+
- 16GB+ RAM

### 身体模块（树莓派）
- Raspberry Pi 4B+
- 4GB+ RAM
- 摄像头模块
- 电机驱动模块
- 音频模块

## 快速开始

### 1. 克隆项目
```bash
git clone https://github.com/yourusername/robot_car.git
cd robot_car
```

### 2. 安装依赖

#### 大脑模块
```bash
cd big_brain
pip install -r requirements.txt
```

#### 身体模块
```bash
cd robot_body
pip install -r requirements.txt
```

### 3. 配置

1. 修改 `big_brain/config/server_config.yaml` 中的服务器配置
2. 修改 `robot_body/config/pi_config.yaml` 中的树莓派配置
3. 下载所需模型到 `big_brain/models` 目录

### 4. 运行

#### 启动大脑模块
```bash
cd big_brain
python src/core/brain.py
```

#### 启动身体模块
```bash
cd robot_body
python src/core/body.py
```

## 项目结构

详细的项目结构请参考 `robot_tech_design.md` 文档。

## 开发指南

1. 遵循 PEP 8 编码规范
2. 所有新功能需要编写单元测试
3. 提交代码前运行测试套件
4. 保持文档的及时更新

## 许可证

MIT License