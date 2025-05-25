#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查进程是否存在
check_process() {
    local process_name=$1
    local result=$(ps aux | grep -E "$process_name" | grep -v grep)
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
    pkill -f "python.*app.py"
    sleep 2
    
    # 检查是否成功停止
    if check_process "python.*app.py"; then
        echo -e "${YELLOW}主程序仍在运行，尝试强制终止...${NC}"
        pkill -9 -f "python.*app.py"
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
    pkill -f "jupyter"
    sleep 2
    
    # 检查是否成功停止
    if check_process "jupyter"; then
        echo -e "${YELLOW}Jupyter仍在运行，尝试强制终止...${NC}"
        pkill -9 -f "jupyter"
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
    ps aux | grep -E "python.*app.py|jupyter" | grep -v grep
    exit 1
else
    echo -e "${GREEN}确认所有目标进程已终止${NC}"
fi

echo -e "${GREEN}停止操作完成${NC}" 