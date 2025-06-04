#!/bin/bash

# 远程主机信息
ROBOT_USER=ws
ROBOT_HOST=ws   # 如果 ws 不是主机名，请改为实际主机名或IP
LOG_DIR=~/logs

# 远程执行 tail -f
ssh ${ROBOT_USER}@${ROBOT_HOST} "cd /home/${ROBOT_USER}/logs && tail -f body.log"