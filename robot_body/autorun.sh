#!/bin/bash

# 检查是否使用sudo运行脚本
if [ -n "$SUDO_USER" ] || [ -n "$SUDO_UID" ]; then
    echo "This script was executed with sudo."
    echo "Use './autorun.sh' instead of 'sudo ./autorun.sh'"
    echo "Exiting..."
    exit 1
fi

# 定义第一个定时任务及其调度计划 - 启动主应用程序
cron_job1="@reboot XDG_RUNTIME_DIR=/run/user/$(id -u) ~/robot_car/robot_body/ugv-env/bin/python ~/robot_car/robot_body/app.py >> ~/ugv.log 2>&1"

# 定义第二个定时任务 - 启动Jupyter服务
cron_job2="@reboot /bin/bash ~/robot_car/robot_body/start_jupyter.sh >> ~/jupyter_log.log 2>&1"

# 检查第一个定时任务是否已存在于用户的crontab中
if crontab -l | grep -q "$cron_job1"; then
    echo "First cron job is already set, no changes made."
else
    # 为用户添加第一个定时任务
    (crontab -l 2>/dev/null; echo "$cron_job1") | crontab -
    echo "First cron job added successfully."
fi

# 检查第二个定时任务是否已存在于用户的crontab中
if crontab -l | grep -q "$cron_job2"; then
    echo "Second cron job is already set, no changes made."
else
    # 为用户添加第二个定时任务
    (crontab -l 2>/dev/null; echo "$cron_job2") | crontab -
    echo "Second cron job added successfully."
fi

# 激活Python虚拟环境并生成Jupyter配置文件
source $PWD/ugv-env/bin/activate && jupyter notebook --generate-config

# 设置Jupyter配置文件路径
CONFIG_FILE=/home/$(logname)/.jupyter/jupyter_notebook_config.py

# 配置Jupyter无密码访问
if [ -f "$CONFIG_FILE" ]; then
    echo "c.NotebookApp.token = ''" >> $CONFIG_FILE
    echo "c.NotebookApp.password = ''" >> $CONFIG_FILE
    echo "JupyterLab: password/token = ''."
else
    echo "run jupyter notebook --generate-config failed."
fi

# 提示用户可以重启系统
echo "Now you can use the command below to reboot."
echo "sudo reboot"