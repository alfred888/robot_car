#!/bin/bash

# 视觉服务抽象层
# 支持多个视觉模型，通过环境变量或参数选择具体实现

# 默认配置
DEFAULT_MODEL="fastvlm"
MODELS_DIR="$HOME/models"
LOGS_DIR="$HOME/logs"
CONFIG_FILE="$HOME/.robot_eyes_config"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 加载配置
load_config() {
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
    else
        # 创建默认配置
        echo "MODEL=$DEFAULT_MODEL" > "$CONFIG_FILE"
        echo "MODELS_DIR=$MODELS_DIR" >> "$CONFIG_FILE"
        echo "LOGS_DIR=$LOGS_DIR" >> "$CONFIG_FILE"
    fi
}

# 保存配置
save_config() {
    echo "MODEL=$MODEL" > "$CONFIG_FILE"
    echo "MODELS_DIR=$MODELS_DIR" >> "$CONFIG_FILE"
    echo "LOGS_DIR=$LOGS_DIR" >> "$CONFIG_FILE"
}

# 检查环境
check_environment() {
    # 检查必要的目录
    mkdir -p "$MODELS_DIR"
    mkdir -p "$LOGS_DIR"
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}错误: 未安装Docker${NC}"
        exit 1
    fi
    
    # 检查docker-compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}错误: 未安装docker-compose${NC}"
        exit 1
    fi
}

# 启动视觉服务
start_service() {
    local model=$1
    local model_dir="$MODELS_DIR/$model"
    
    echo -e "${GREEN}启动 $model 视觉服务...${NC}"
    
    case $model in
        "fastvlm")
            cd "$(dirname "$0")/ml-fastvlm" || exit 1
            ./start_fastvlm.sh
            ;;
        # 在这里添加其他模型的启动方式
        # "other_model")
        #     cd "$(dirname "$0")/other_model" || exit 1
        #     ./start_other_model.sh
        #     ;;
        *)
            echo -e "${RED}错误: 不支持的模型 $model${NC}"
            exit 1
            ;;
    esac
}

# 停止视觉服务
stop_service() {
    local model=$1
    
    echo -e "${YELLOW}停止 $model 视觉服务...${NC}"
    
    case $model in
        "fastvlm")
            cd "$(dirname "$0")/ml-fastvlm" || exit 1
            docker-compose down
            ;;
        # 在这里添加其他模型的停止方式
        # "other_model")
        #     cd "$(dirname "$0")/other_model" || exit 1
        #     docker-compose down
        #     ;;
        *)
            echo -e "${RED}错误: 不支持的模型 $model${NC}"
            exit 1
            ;;
    esac
}

# 查看服务状态
status_service() {
    local model=$1
    
    echo -e "${GREEN}检查 $model 视觉服务状态...${NC}"
    
    case $model in
        "fastvlm")
            cd "$(dirname "$0")/ml-fastvlm" || exit 1
            docker-compose ps
            ;;
        # 在这里添加其他模型的状态检查
        # "other_model")
        #     cd "$(dirname "$0")/other_model" || exit 1
        #     docker-compose ps
        #     ;;
        *)
            echo -e "${RED}错误: 不支持的模型 $model${NC}"
            exit 1
            ;;
    esac
}

# 切换模型
switch_model() {
    local new_model=$1
    
    # 停止当前服务
    stop_service "$MODEL"
    
    # 更新配置
    MODEL=$new_model
    save_config
    
    # 启动新服务
    start_service "$MODEL"
}

# 查看图片
see() {
    local image_path=$1
    
    # 检查图片文件是否存在
    if [ ! -f "$image_path" ]; then
        echo -e "${RED}错误: 图片文件不存在: $image_path${NC}"
        return 1
    fi
    
    # 检查服务是否运行
    if ! docker ps | grep -q "fastvlm"; then
        echo -e "${YELLOW}警告: 视觉服务未运行，正在启动...${NC}"
        start_service "$MODEL"
        # 等待服务启动
        sleep 5
    fi
    
    # 调用Python客户端
    echo -e "${GREEN}正在分析图片: $image_path${NC}"
    python3 "$(dirname "$0")/robot_eyes.py" "$image_path" "$MODEL"
}

# 主函数
main() {
    # 加载配置
    load_config
    
    # 解析命令行参数
    case "$1" in
        "start")
            start_service "$MODEL"
            ;;
        "stop")
            stop_service "$MODEL"
            ;;
        "status")
            status_service "$MODEL"
            ;;
        "switch")
            if [ -z "$2" ]; then
                echo -e "${RED}错误: 请指定要切换的模型${NC}"
                exit 1
            fi
            switch_model "$2"
            ;;
        "config")
            echo "当前配置:"
            echo "模型: $MODEL"
            echo "模型目录: $MODELS_DIR"
            echo "日志目录: $LOGS_DIR"
            ;;
        "see")
            if [ -z "$2" ]; then
                echo -e "${RED}错误: 请指定图片路径${NC}"
                exit 1
            fi
            see "$2"
            ;;
        *)
            echo "用法: $0 {start|stop|status|switch|config|see}"
            echo "  start   - 启动视觉服务"
            echo "  stop    - 停止视觉服务"
            echo "  status  - 查看服务状态"
            echo "  switch  - 切换视觉模型"
            echo "  config  - 显示当前配置"
            echo "  see     - 分析图片"
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@" 