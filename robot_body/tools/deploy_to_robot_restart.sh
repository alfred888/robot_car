#!/bin/bash

# 远程主机信息
ROBOT_USER=ws
ROBOT_HOST=ws
ROBOT_DIR=/home/ws/robot_car/robot_body

# 执行远程操作
ssh ${ROBOT_USER} << EOF
cd ${ROBOT_DIR}
git pull
bash restart_robot.sh
EOF 