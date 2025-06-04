#!/bin/bash

# 进入当前用户主目录下的logs目录
dir=~/logs
cd "$dir" || { echo "日志目录不存在: $dir"; exit 1; }

echo "正在实时查看 $dir/body.log ..."
tail -f body.log 