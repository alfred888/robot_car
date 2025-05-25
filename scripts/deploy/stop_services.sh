#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 从配置文件读取树莓派配置信息
PI_CONFIG_FILE="robot_car/robot_body/config/pi_config.yaml"

if [ ! -f "$PI_CONFIG_FILE" ]; then
    echo -e "${RED}错误: 找不到配置文件 $PI_CONFIG_FILE${NC}"
    exit 1
fi

# 使用yq读取yaml配置
PI_HOST=$(yq eval '.raspberry_pi.host' "$PI_CONFIG_FILE")
PI_USER=$(yq eval '.raspberry_pi.username' "$PI_CONFIG_FILE")
PI_PORT=$(yq eval '.raspberry_pi.ssh_port' "$PI_CONFIG_FILE")

if [ -z "$PI_HOST" ] || [ -z "$PI_USER" ] || [ -z "$PI_PORT" ]; then
    echo -e "${RED}错误: 配置文件中缺少必要的树莓派连接信息${NC}"
    exit 1
fi

# 检查SSH连接
echo -e "${YELLOW}正在检查SSH连接...${NC}"
if ! ssh -p $PI_PORT $PI_USER@$PI_HOST "echo 'SSH 连接成功'" &>/dev/null; then
    echo -e "${RED}错误: 无法连接到树莓派，请检查 SSH 配置${NC}"
    exit 1
fi

# 检查进程是否存在
check_process() {
    local process_name=$1
    local result=$(ssh -p $PI_PORT $PI_USER@$PI_HOST "ps aux | grep -E '$process_name' | grep -v grep")
    if [ -n "$result" ]; then
        return 0  # 进程存在
    else
        return 1  # 进程不存在
    fi
}

# 停止主程序
echo -e "${YELLOW}正在停止主程序...${NC}"
if check_process "python.*app.py"; then
    echo -e "${YELLOW}找到主程序进程，正在停止...${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "pkill -f 'python.*app.py'"
    sleep 2
    
    # 检查是否成功停止
    if check_process "python.*app.py"; then
        echo -e "${YELLOW}主程序仍在运行，尝试强制终止...${NC}"
        ssh -p $PI_PORT $PI_USER@$PI_HOST "pkill -9 -f 'python.*app.py'"
        sleep 1
        
        # 再次检查
        if check_process "python.*app.py"; then
            echo -e "${RED}错误: 无法停止主程序${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}主程序已停止${NC}"
else
    echo -e "${GREEN}主程序未运行${NC}"
fi

# 停止Jupyter服务
echo -e "${YELLOW}正在停止Jupyter服务...${NC}"
if check_process "jupyter"; then
    echo -e "${YELLOW}找到Jupyter进程，正在停止...${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "pkill -f 'jupyter'"
    sleep 2
    
    # 检查是否成功停止
    if check_process "jupyter"; then
        echo -e "${YELLOW}Jupyter仍在运行，尝试强制终止...${NC}"
        ssh -p $PI_PORT $PI_USER@$PI_HOST "pkill -9 -f 'jupyter'"
        sleep 1
        
        # 再次检查
        if check_process "jupyter"; then
            echo -e "${RED}错误: 无法停止Jupyter服务${NC}"
            exit 1
        fi
    fi
    echo -e "${GREEN}Jupyter服务已停止${NC}"
else
    echo -e "${GREEN}Jupyter服务未运行${NC}"
fi

# 最终检查确认
echo -e "${YELLOW}最终检查确认进程状态...${NC}"
if check_process "python.*app.py" || check_process "jupyter"; then
    echo -e "${RED}警告: 仍有进程未能完全终止${NC}"
    echo -e "${YELLOW}请手动检查以下进程:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "ps aux | grep -E 'python.*app.py|jupyter' | grep -v grep"
    exit 1
else
    echo -e "${GREEN}确认所有目标进程已终止${NC}"
fi

echo -e "${GREEN}停止操作完成${NC}" 