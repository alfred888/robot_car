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

echo "机器人服务已停止。" 