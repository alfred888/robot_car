#!/bin/bash

# 当前目录已经在 robot_body 下,无需切换目录

# 停止 app.py
echo "正在停止 app.py..."
pkill -f "python.*app.py"
sleep 2

# 检查是否成功停止
if pgrep -f "python.*app.py" > /dev/null; then
    echo "app.py 仍在运行，尝试强制终止..."
    pkill -9 -f "python.*app.py"
    sleep 1
fi

# 停止 Jupyter
echo "正在停止 Jupyter..."
pkill -f "jupyter"
sleep 2

if pgrep -f "jupyter" > /dev/null; then
    echo "Jupyter 仍在运行，尝试强制终止..."
    pkill -9 -f "jupyter"
    sleep 1
fi

# 激活虚拟环境
echo "激活虚拟环境并重启 app.py..."
source ugv-env/bin/activate

# 启动 app.py（后台运行，日志输出到 body.log）
nohup python app.py > ${HOME}/logs/body.log 2>&1 &

# 启动 Jupyter（后台运行，日志输出到 jupyter.log）
nohup ./start_jupyter.sh > ${HOME}/logs/jupyter.log 2>&1 &

echo "机器人服务已重启。"