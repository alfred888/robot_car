#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查是否为树莓派
if [ -f /proc/device-tree/model ]; then
    IS_RASPBERRY_PI=true
    echo -e "${YELLOW}检测到树莓派环境${NC}"
else
    IS_RASPBERRY_PI=false
    echo -e "${YELLOW}非树莓派环境${NC}"
fi

# 检查Python版本
echo -e "${YELLOW}检查Python版本...${NC}"
if command -v python3 &>/dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo -e "${GREEN}找到Python: $PYTHON_VERSION${NC}"
else
    echo -e "${RED}错误: 未找到Python3${NC}"
    exit 1
fi

# 检查pip版本
echo -e "${YELLOW}检查pip版本...${NC}"
if command -v pip3 &>/dev/null; then
    PIP_VERSION=$(pip3 --version)
    echo -e "${GREEN}找到pip: $PIP_VERSION${NC}"
else
    echo -e "${RED}错误: 未找到pip3${NC}"
    exit 1
fi

# 创建虚拟环境
echo -e "${YELLOW}创建Python虚拟环境...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}虚拟环境创建成功${NC}"
    else
        echo -e "${RED}错误: 虚拟环境创建失败${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}虚拟环境已存在${NC}"
fi

# 激活虚拟环境
echo -e "${YELLOW}激活虚拟环境...${NC}"
source venv/bin/activate
if [ $? -eq 0 ]; then
    echo -e "${GREEN}虚拟环境激活成功${NC}"
else
    echo -e "${RED}错误: 虚拟环境激活失败${NC}"
    exit 1
fi

# 升级pip
echo -e "${YELLOW}升级pip...${NC}"
pip install --upgrade pip
if [ $? -eq 0 ]; then
    echo -e "${GREEN}pip升级成功${NC}"
else
    echo -e "${RED}错误: pip升级失败${NC}"
    exit 1
fi

# 安装依赖
echo -e "${YELLOW}安装依赖...${NC}"
if [ "$IS_RASPBERRY_PI" = true ]; then
    # 树莓派特定依赖
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}依赖安装成功${NC}"
    else
        echo -e "${RED}错误: 依赖安装失败${NC}"
        exit 1
    fi
else
    # 非树莓派环境
    pip install -r requirements.txt
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}依赖安装成功${NC}"
    else
        echo -e "${RED}错误: 依赖安装失败${NC}"
        exit 1
    fi
fi

# 设置权限
echo -e "${YELLOW}设置脚本执行权限...${NC}"
chmod +x *.sh
if [ $? -eq 0 ]; then
    echo -e "${GREEN}权限设置成功${NC}"
else
    echo -e "${RED}错误: 权限设置失败${NC}"
    exit 1
fi

echo -e "${GREEN}环境配置完成！${NC}"
echo -e "${YELLOW}使用以下命令激活环境：${NC}"
echo "source venv/bin/activate" 