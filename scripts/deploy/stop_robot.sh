#!/bin/bash

# 设置颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
CONFIG_FILE="$SCRIPT_DIR/../../robot_body/config/pi_config.yaml"

# 从配置文件读取默认配置
if [ -f "$CONFIG_FILE" ]; then
    # 使用yq工具读取yaml配置
    if command -v yq &> /dev/null; then
        if [ "$DEBUG_MODE" = true ]; then
            echo -e "${YELLOW}配置文件路径: $CONFIG_FILE${NC}"
            echo -e "${YELLOW}配置文件内容:${NC}"
            cat "$CONFIG_FILE"
        fi
        
        # 读取配置
        DEFAULT_HOST=$(yq eval '.raspberry_pi.host' "$CONFIG_FILE")
        DEFAULT_USER=$(yq eval '.raspberry_pi.username' "$CONFIG_FILE")
        DEFAULT_SSH_PORT=22  # SSH端口固定为22
        DEFAULT_SERVICE_PORT=$(yq eval '.raspberry_pi.port' "$CONFIG_FILE")
        DEBUG_MODE=$(yq eval '.raspberry_pi.debug' "$CONFIG_FILE")
        
        # 设置默认值（如果配置文件中没有指定）
        DEFAULT_HOST=${DEFAULT_HOST:-"ugvrpi"}
        DEFAULT_USER=${DEFAULT_USER:-"pi"}
        DEFAULT_SERVICE_PORT=${DEFAULT_SERVICE_PORT:-"8081"}
        DEBUG_MODE=${DEBUG_MODE:-false}
        
        if [ "$DEBUG_MODE" = true ]; then
            echo -e "${YELLOW}读取的配置:${NC}"
            echo -e "  HOST: $DEFAULT_HOST"
            echo -e "  USER: $DEFAULT_USER"
            echo -e "  SERVICE_PORT: $DEFAULT_SERVICE_PORT"
            echo -e "  DEBUG: $DEBUG_MODE"
        fi
    else
        echo -e "${YELLOW}警告: 未找到yq工具,使用默认配置${NC}"
        DEFAULT_HOST="ugvrpi"
        DEFAULT_USER="pi"
        DEFAULT_SSH_PORT=22
        DEFAULT_SERVICE_PORT=8081
        DEBUG_MODE=false
    fi
else
    echo -e "${YELLOW}警告: 未找到配置文件 $CONFIG_FILE,使用默认配置${NC}"
    DEFAULT_HOST="ugvrpi"
    DEFAULT_USER="pi"
    DEFAULT_SSH_PORT=22
    DEFAULT_SERVICE_PORT=8081
    DEBUG_MODE=false
fi

# 显示帮助信息
show_help() {
    echo "用法: $0 [选项]"
    echo "选项:"
    echo "  -h, --host HOST     指定树莓派主机名或IP (默认: $DEFAULT_HOST)"
    echo "  -u, --user USER     指定SSH用户名 (默认: $DEFAULT_USER)"
    echo "  -p, --port PORT     指定服务端口 (默认: $DEFAULT_SERVICE_PORT)"
    echo "  -d, --debug         启用调试模式"
    echo "  --help              显示此帮助信息"
    exit 0
}

# 初始化变量
HOST=""
USER=""
SERVICE_PORT=""

# 解析命令行参数
while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -u|--user)
            USER="$2"
            shift 2
            ;;
        -p|--port)
            SERVICE_PORT="$2"
            shift 2
            ;;
        -d|--debug)
            DEBUG_MODE=true
            shift
            ;;
        --help)
            show_help
            ;;
        *)
            echo -e "${RED}错误: 未知选项 $1${NC}"
            show_help
            ;;
    esac
done

# 使用默认值（只有在命令行没有指定时才使用配置文件的值）
HOST=${HOST:-$DEFAULT_HOST}
USER=${USER:-$DEFAULT_USER}
SERVICE_PORT=${SERVICE_PORT:-$DEFAULT_SERVICE_PORT}
SSH_PORT=$DEFAULT_SSH_PORT  # SSH端口固定为22

# 调试模式输出
if [ "$DEBUG_MODE" = true ]; then
    echo -e "${YELLOW}调试模式: 启用${NC}"
    echo -e "${YELLOW}最终使用的配置:${NC}"
    echo -e "  主机: $HOST"
    echo -e "  用户: $USER"
    echo -e "  SSH端口: $SSH_PORT"
    echo -e "  服务端口: $SERVICE_PORT"
fi

# 检查SSH连接
echo -e "${YELLOW}正在检查SSH连接...${NC}"
if ! ssh -p $SSH_PORT $USER@$HOST "echo 'SSH连接成功'" &>/dev/null; then
    echo -e "${RED}错误: 无法连接到 $USER@$HOST:$SSH_PORT${NC}"
    exit 1
fi

# 停止主程序
echo -e "${YELLOW}正在停止主程序...${NC}"
if [ "$DEBUG_MODE" = true ]; then
    ssh -p $SSH_PORT $USER@$HOST "ps aux | grep 'python.*app.py'"
fi

# 使用更直接的方式停止进程
ssh -p $SSH_PORT $USER@$HOST '
    # 设置调试模式
    DEBUG_MODE="'$DEBUG_MODE'"
    
    # 获取进程ID
    APP_PID=$(pgrep -f "/home/'$USER'/ugv_rpi/ugv-env/bin/python /home/'$USER'/ugv_rpi/app.py")
    JUPYTER_PID=$(pgrep -f "/home/'$USER'/ugv_rpi/ugv-env/bin/python.*jupyter-lab")
    
    if [ "$DEBUG_MODE" = "true" ]; then
        echo "找到的进程ID:"
        echo "APP_PID: $APP_PID"
        echo "JUPYTER_PID: $JUPYTER_PID"
    fi
    
    # 停止主程序
    if [ ! -z "$APP_PID" ]; then
        echo "正在停止主程序 (PID: $APP_PID)..."
        kill -15 $APP_PID 2>/dev/null || true
        sleep 2
        if kill -0 $APP_PID 2>/dev/null; then
            echo "强制终止主程序..."
            kill -9 $APP_PID 2>/dev/null || true
            sleep 1
        fi
    fi
    
    # 停止Jupyter服务
    if [ ! -z "$JUPYTER_PID" ]; then
        echo "正在停止Jupyter服务 (PID: $JUPYTER_PID)..."
        kill -15 $JUPYTER_PID 2>/dev/null || true
        sleep 2
        if kill -0 $JUPYTER_PID 2>/dev/null; then
            echo "强制终止Jupyter服务..."
            kill -9 $JUPYTER_PID 2>/dev/null || true
            sleep 1
        fi
    fi
    
    # 清理可能的残留进程
    echo "清理残留进程..."
    pkill -f "/home/'$USER'/ugv_rpi/ugv-env/bin/python /home/'$USER'/ugv_rpi/app.py" 2>/dev/null || true
    pkill -f "/home/'$USER'/ugv_rpi/ugv-env/bin/python.*jupyter" 2>/dev/null || true
    
    # 检查进程是否还在运行
    echo "检查进程状态..."
    if pgrep -f "/home/'$USER'/ugv_rpi/ugv-env/bin/python /home/'$USER'/ugv_rpi/app.py" > /dev/null; then
        echo -e "\033[0;31m警告: 主程序仍在运行\033[0m"
        if [ "$DEBUG_MODE" = "true" ]; then
            ps aux | grep "/home/'$USER'/ugv_rpi/ugv-env/bin/python /home/'$USER'/ugv_rpi/app.py"
        fi
    else
        echo -e "\033[0;32m主程序已停止\033[0m"
    fi
    
    if pgrep -f "/home/'$USER'/ugv_rpi/ugv-env/bin/python.*jupyter" > /dev/null; then
        echo -e "\033[0;31m警告: Jupyter服务仍在运行\033[0m"
        if [ "$DEBUG_MODE" = "true" ]; then
            ps aux | grep "/home/'$USER'/ugv_rpi/ugv-env/bin/python.*jupyter"
        fi
    else
        echo -e "\033[0;32mJupyter服务已停止\033[0m"
    fi
'

echo -e "${GREEN}停止操作完成${NC}" 