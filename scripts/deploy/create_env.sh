#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
# 获取项目根目录的绝对路径
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# 从配置文件读取树莓派配置信息
PI_CONFIG_FILE="$PROJECT_ROOT/robot_car/robot_body/config/pi_config.yaml"

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

# 检查参数
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  -h, --help     显示帮助信息"
    exit 0
fi

# 主函数
main() {
    # 检查是否安装了必要的工具
    if ! command -v ssh &> /dev/null; then
        echo -e "${RED}错误: 未安装 ssh${NC}"
        exit 1
    fi
    
    # 检查 SSH 连接
    echo -e "${YELLOW}检查 SSH 连接...${NC}"
    if ! ssh -p $PI_PORT $PI_USER@$PI_HOST "echo 'SSH 连接成功'" &>/dev/null; then
        echo -e "${RED}错误: 无法连接到树莓派，请检查 SSH 配置${NC}"
        exit 1
    fi
    
    # 执行setup.sh脚本
    echo -e "${YELLOW}正在执行setup.sh脚本...${NC}"
    ssh -p $PI_PORT $PI_USER@$PI_HOST "cd ~/robot_body && ./setup.sh"
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}环境配置成功！${NC}"
    else
        echo -e "${RED}环境配置失败！${NC}"
        exit 1
    fi
}

# 执行主函数
main "$@"
