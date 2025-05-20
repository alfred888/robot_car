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

# 创建临时crontab文件
TEMP_CRONTAB=$(mktemp)

# 获取当前的crontab内容
echo -e "${YELLOW}获取当前crontab配置...${NC}"
ssh -p $PI_PORT $PI_USER@$PI_HOST "crontab -l" > "$TEMP_CRONTAB" 2>/dev/null

# 检查是否成功获取crontab
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}当前没有crontab配置，创建新的配置...${NC}"
    echo "" > "$TEMP_CRONTAB"
fi

# 添加新的crontab配置
echo -e "${YELLOW}添加新的crontab配置...${NC}"

# 检查是否已存在相关配置
if ! grep -q "robot_body/app.py" "$TEMP_CRONTAB"; then
    # 添加启动主程序的配置（开机自启）
    echo "@reboot cd /home/$PI_USER/robot_body && ./venv/bin/python app.py >> /home/$PI_USER/robot_body/app.log 2>&1" >> "$TEMP_CRONTAB"
    echo -e "${GREEN}已添加主程序自启动配置${NC}"
fi

if ! grep -q "robot_body/start_jupyter.sh" "$TEMP_CRONTAB"; then
    # 添加启动Jupyter的配置（开机自启）
    echo "@reboot cd /home/$PI_USER/robot_body && ./start_jupyter.sh >> /home/$PI_USER/robot_body/jupyter.log 2>&1" >> "$TEMP_CRONTAB"
    echo -e "${GREEN}已添加Jupyter自启动配置${NC}"
fi

# 上传新的crontab配置
echo -e "${YELLOW}更新crontab配置...${NC}"
cat "$TEMP_CRONTAB" | ssh -p $PI_PORT $PI_USER@$PI_HOST "crontab -"

# 检查是否成功更新
if [ $? -eq 0 ]; then
    echo -e "${GREEN}crontab配置已成功更新${NC}"
else
    echo -e "${RED}错误: 更新crontab配置失败${NC}"
    exit 1
fi

# 清理临时文件
rm "$TEMP_CRONTAB"

# 显示当前的crontab配置
echo -e "${YELLOW}当前的crontab配置:${NC}"
ssh -p $PI_PORT $PI_USER@$PI_HOST "crontab -l"

echo -e "${GREEN}设置完成${NC}" 