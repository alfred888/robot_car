#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# 检查操作系统类型
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    PYTHON_CMD="python3"
    VENV_NAME="venv_mac"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Ubuntu/Linux
    PYTHON_CMD="python3"
    VENV_NAME="venv_linux"
else
    echo "不支持的操作系统: $OSTYPE"
    exit 1
fi

# 检查 Python 是否安装
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo "错误: 未找到 $PYTHON_CMD"
    exit 1
fi

# 创建虚拟环境（如果不存在）
if [ ! -d "$VENV_NAME" ]; then
    echo "创建虚拟环境..."
    $PYTHON_CMD -m venv "$VENV_NAME"
fi

# 激活虚拟环境
echo "激活虚拟环境..."
source "$VENV_NAME/bin/activate"

# 升级 pip
echo "升级 pip..."
pip install --upgrade pip

# 安装依赖
echo "安装依赖..."
pip install -r requirements.txt

# 启动服务
echo "启动测试服务..."
python http_server.py 