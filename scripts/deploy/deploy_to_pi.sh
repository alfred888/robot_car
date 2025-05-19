#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 从配置文件读取树莓派配置信息
PI_CONFIG_FILE="robot_body/config/pi_config.yaml"

if [ ! -f "$PI_CONFIG_FILE" ]; then
    echo -e "${RED}错误: 找不到配置文件 $PI_CONFIG_FILE${NC}"
    exit 1
fi

# 使用yq读取yaml配置
PI_HOST=$(yq eval '.raspberry_pi.host' "$PI_CONFIG_FILE")
PI_USER=$(yq eval '.raspberry_pi.username' "$PI_CONFIG_FILE") 


PI_PORT=22  # SSH端口固定为22
REMOTE_DIR="~/robot_body"
LOCAL_DIR="robot_body"

if [ -z "$PI_HOST" ] || [ -z "$PI_USER" ] || [ -z "$PI_PASS" ]; then
    echo -e "${RED}错误: 配置文件中缺少必要的树莓派连接信息${NC}"
    exit 1
fi

# 检查参数
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    echo "  -c, --check    只检查树莓派配置"
    echo "  -d, --deploy   部署代码到树莓派"
    exit 0
fi

# 检查树莓派配置
check_pi_config() {
    echo -e "${YELLOW}正在检查树莓派配置...${NC}"
    
    # 检查系统信息
    echo -e "\n${GREEN}系统信息:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "uname -a"
    
    # 检查 Python 版本
    echo -e "\n${GREEN}Python 版本:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "python3 --version"
    
    # 检查磁盘空间
    echo -e "\n${GREEN}磁盘空间:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "df -h"
    
    # 检查内存使用
    echo -e "\n${GREEN}内存使用:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "free -h"
    
    # 检查 CPU 信息
    echo -e "\n${GREEN}CPU 信息:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "cat /proc/cpuinfo | grep 'Model name'"
    
    # 检查 GPU 信息
    echo -e "\n${GREEN}GPU 信息:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "vcgencmd get_mem gpu"
    
    # 检查温度
    echo -e "\n${GREEN}系统温度:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "vcgencmd measure_temp"
    
    # 检查网络配置
    echo -e "\n${GREEN}网络配置:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "ip addr show"
    
    # 检查已安装的包
    echo -e "\n${GREEN}已安装的 Python 包:${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "pip3 list"
}

# 部署代码到树莓派
deploy_to_pi() {
    echo -e "${YELLOW}正在部署代码到树莓派...${NC}"
    
    # 创建远程目录
    echo -e "\n${GREEN}创建远程目录...${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "mkdir -p $REMOTE_DIR"
    
    # 清空远程目录内容（保留目录本身）
    echo -e "\n${GREEN}清空远程 robot_body 目录内容...${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "rm -rf $REMOTE_DIR/*"
    
    # 同步代码
    echo -e "\n${GREEN}同步代码...${NC}"
    rsync -avz --exclude 'venv' \
              --exclude '__pycache__' \
              --exclude '*.pyc' \
              --exclude '.git' \
              --exclude 'logs' \
              -e "ssh -p $PI_PORT" \
              $LOCAL_DIR/ $PI_USER@$PI_HOST:$REMOTE_DIR/
    
    # 检查部署结果
    if [ $? -eq 0 ]; then
        echo -e "\n${GREEN}代码部署成功！${NC}"
    else
        echo -e "\n${RED}代码部署失败！${NC}"
        exit 1
    fi
    
    # 设置权限
    echo -e "\n${GREEN}设置文件权限...${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "chmod -R 755 $REMOTE_DIR"
    
    # 创建虚拟环境
    echo -e "\n${GREEN}创建虚拟环境...${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "cd $REMOTE_DIR && python3 -m venv venv"
    
    # 安装依赖
    echo -e "\n${GREEN}安装依赖...${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "cd $REMOTE_DIR && source venv/bin/activate && pip install -r requirements.txt"
}

# 主函数
main() {
    # 检查是否安装了必要的工具
    if ! command -v ssh &> /dev/null; then
        echo -e "${RED}错误: 未安装 ssh${NC}"
        exit 1
    fi
    
    if ! command -v rsync &> /dev/null; then
        echo -e "${RED}错误: 未安装 rsync${NC}"
        exit 1
    fi
    
    # 根据参数执行不同的操作
    case "$1" in
        "-c"|"--check")
            check_pi_config
            ;;
        "-d"|"--deploy")
            deploy_to_pi
            ;;
        *)
            check_pi_config
            deploy_to_pi
            ;;
    esac
}

# 执行主函数
main "$@" 