#!/bin/bash

# 检查是否在树莓派环境
if [ -f /proc/device-tree/model ]; then
    echo "检测到树莓派环境"
    # 树莓派环境使用pip
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
    VENV_DIR="venv"
else
    echo "检测到开发环境"
    # 开发环境使用conda
    PYTHON_CMD="python"
    PIP_CMD="pip"
    VENV_DIR="robot_env"
fi

# 检查Python版本
echo "检查Python版本..."
if command -v $PYTHON_CMD &> /dev/null; then
    $PYTHON_CMD --version
else
    echo "错误: 未找到Python"
    exit 1
fi

# 检查pip版本
echo "检查pip版本..."
if command -v $PIP_CMD &> /dev/null; then
    $PIP_CMD --version
else
    echo "错误: 未找到pip"
    exit 1
fi

# 创建Python虚拟环境
echo "创建Python虚拟环境..."
if [ -f /proc/device-tree/model ]; then
    # 树莓派环境使用venv
    if [ ! -d "$VENV_DIR" ]; then
        $PYTHON_CMD -m venv $VENV_DIR
        if [ $? -ne 0 ]; then
            echo "错误: 虚拟环境创建失败"
            exit 1
        fi
    else
        echo "虚拟环境已存在"
    fi
else
    # 开发环境使用conda
    if ! conda env list | grep -q "^$VENV_DIR "; then
        conda create -y -n $VENV_DIR python=3.11
        if [ $? -ne 0 ]; then
            echo "错误: conda环境创建失败"
            exit 1
        fi
    else
        echo "conda环境已存在"
    fi
fi

# 激活虚拟环境
echo "激活虚拟环境..."
if [ -f /proc/device-tree/model ]; then
    # 树莓派环境使用venv
    source $VENV_DIR/bin/activate
    if [ $? -ne 0 ]; then
        echo "错误: 虚拟环境激活失败"
        exit 1
    fi
else
    # 开发环境使用conda
    source $(conda info --base)/etc/profile.d/conda.sh
    conda activate $VENV_DIR
    if [ $? -ne 0 ]; then
        echo "错误: conda环境激活失败"
        exit 1
    fi
fi
echo "虚拟环境激活成功"

# 升级pip
echo "升级pip..."
$PIP_CMD install --upgrade pip
if [ $? -ne 0 ]; then
    echo "错误: pip升级失败"
    exit 1
fi
echo "pip升级成功"

# 安装依赖
echo "安装依赖..."
if [ -f "requirements.txt" ]; then
    $PIP_CMD install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "错误: 依赖安装失败"
        exit 1
    fi
    echo "依赖安装成功"
else
    echo "错误: requirements.txt文件不存在"
    exit 1
fi

echo "环境配置完成" 