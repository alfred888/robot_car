#!/bin/bash
[ -f ~/.bashrc ] && source ~/.bashrc
cd ~/robot_car/robot_body/ && source ugv-env/bin/activate && jupyter lab --ip=0.0.0.0 --port=8888 --no-browser
