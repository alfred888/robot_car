#!/bin/bash

# 检查是否以root权限运行脚本
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo."
    echo "Use 'sudo ./setup.sh' instead of './setup.sh'"
    echo "Exiting..."
    exit 1
fi

# 设置是否使用国内源的默认值
use_index=false

# 解析命令行参数
while [[ $# -gt 0 ]]; do
  key="$1"
  case $key in
    -i|--index)  # 使用国内源选项
      use_index=true
      shift
      ;;
    *)  # 未知选项
      # 显示使用帮助
      echo "Usage: $0 [-i | --index] (to use other source)"
      exit 1
      ;;
  esac
done

# 检查固件配置文件位置
if [ -e /boot/firmware/config.txt ] ; then
  FIRMWARE=/firmware
else
  FIRMWARE=
fi
CONFIG=/boot${FIRMWARE}/config.txt

# 检查是否为树莓派设备
is_pi () {
  ARCH=$(dpkg --print-architecture)
  if [ "$ARCH" = "armhf" ] || [ "$ARCH" = "arm64" ] ; then
    return 0
  else
    return 1
  fi
}

# 获取命令行配置文件路径
if is_pi ; then
  if [ -e /proc/device-tree/chosen/os_prefix ]; then
    PREFIX="$(cat /proc/device-tree/chosen/os_prefix)"
  fi
  CMDLINE="/boot${FIRMWARE}/${PREFIX}cmdline.txt"
else
  CMDLINE=/proc/cmdline
fi

# 检查是否为树莓派5
is_pifive() {
  grep -q "^Revision\s*:\s*[ 123][0-9a-fA-F][0-9a-fA-F]4[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]$" /proc/cpuinfo
  return $?
}

# 配置命令行参数
# 移除串口控制台配置
sed -i $CMDLINE -e "s/console=ttyAMA0,[0-9]\+ //"
sed -i $CMDLINE -e "s/console=serial0,[0-9]\+ //"

# 配置config.txt的函数
set_config_var() {
  lua - "$1" "$2" "$3" <<EOF > "$3.bak"
local key=assert(arg[1])
local value=assert(arg[2])
local fn=assert(arg[3])
local file=assert(io.open(fn))
local made_change=false
for line in file:lines() do
  if line:match("^#?%s*"..key.."=.*$") then
    line=key.."="..value
    made_change=true
  end
  print(line)
end

if not made_change then
  print(key.."="..value)
end
EOF
mv "$3.bak" "$3"
}

# 启用UART0
set_config_var dtparam=uart0 on $CONFIG

# 禁用蓝牙
echo "# Add dtoverlay=disable-bt to /boot/firmware/config.txt"
if ! grep -q 'dtoverlay=disable-bt' /boot/firmware/config.txt; then
  echo 'dtoverlay=disable-bt' >> /boot/firmware/config.txt
fi

# 禁用蓝牙相关服务
sudo systemctl disable hciuart.service
sudo systemctl disable bluetooth.service

# 配置软件源
if $use_index; then
  # 备份原始sources.list
  if ! [ -e /etc/apt/sources.list.bak ]; then
    sudo cp /etc/apt/sources.list /etc/apt/sources.list.bak
  fi

  # 使用清华源
  echo "Updating sources.list with other mirrors..."
  sudo sh -c 'echo "deb https://mirrors.tuna.tsinghua.edu.cn/debian bookworm main contrib non-free non-free-firmware\ndeb https://mirrors.tuna.tsinghua.edu.cn/debian-security bookworm-security main contrib non-free non-free-firmware\ndeb https://mirrors.tuna.tsinghua.edu.cn/debian bookworm-updates main contrib non-free non-free-firmware" > /etc/apt/sources.list'

  # 备份并更新树莓派专用源
  if ! [ -e /etc/apt/sources.list.d/raspi.list.bak ]; then
    sudo cp /etc/apt/sources.list.d/raspi.list /etc/apt/sources.list.d/raspi.list.bak
  fi

  sudo sh -c 'echo "deb https://mirrors.tuna.tsinghua.edu.cn/raspberrypi bookworm main" > /etc/apt/sources.list.d/raspi.list'

  # 更新软件包列表
  echo "Updating package list..."
  sudo apt update

  echo "Done! Your sources.list has been updated with Aliyun mirrors while keeping the release name 'bookworm'."
else
  echo "# Using default sources."
fi

# 安装必要的软件包
echo "# Install required software."
sudo apt update
sudo apt upgrade -y
sudo apt install -y libopenblas-dev libatlas3-base libcamera-dev python3-opencv portaudio19-dev
sudo apt install -y util-linux procps hostapd iproute2 iw haveged dnsmasq iptables espeak

# 创建Python虚拟环境
echo "# Create a Python virtual environment."
cd $PWD
python -m venv --system-site-packages ugv-env

echo "# Activate a Python virtual environment."

# 安装Python依赖
echo "# Install dependencies from requirements.txt"
if $use_index; then
  sudo -H -u $USER bash -c 'source $PWD/ugv-env/bin/activate && pip install -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt && deactivate'
else
  sudo -H -u $USER bash -c 'source $PWD/ugv-env/bin/activate && pip install -r requirements.txt && deactivate'
fi

# 添加用户到dialout组以使用串口
echo "# Add current user to group so it can use serial."
sudo usermod -aG dialout $USER

# 配置音频
echo "# Audio Config."
sudo cp -v -f /home/$(logname)/robot_car/robot_body/asound.conf /etc/asound.conf

# 配置OAK相机
sudo cp -v -f /home/$(logname)/robot_car/robot_body/config/99-dai.rules /etc/udev/rules.d/99-dai.rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# 完成提示
echo "Setup completed. Please to reboot your Raspberry Pi for the changes to take effect."

echo "Use the command below to run app.py onboot."

echo "sudo chmod +x autorun.sh"

echo "./autorun.sh"