#!/usr/bin/env python3
"""
独立环境创建脚本：
- 检查 conda 是否安装
- 创建 conda 环境 (Python 3.10)
- 安装项目依赖
"""
import os
import sys
import subprocess
from pathlib import Path

ENV_NAME = "fastvlm"
PYTHON_VERSION = "3.10"

def check_conda():
    """检查是否安装了conda"""
    try:
        subprocess.run(["conda", "--version"], check=True, capture_output=True)
        print("检测到 conda 已安装")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("错误: 未检测到 conda，请先安装 conda")
        sys.exit(1)

def create_conda_env():
    """创建 conda 环境"""
    # 检查环境是否已存在
    result = subprocess.run(["conda", "env", "list"], capture_output=True, text=True)
    if ENV_NAME in result.stdout:
        print(f"conda 环境 {ENV_NAME} 已存在")
        return
    
    print(f"正在创建 conda 环境: {ENV_NAME}")
    subprocess.run([
        "conda", "create", "-n", ENV_NAME,
        f"python={PYTHON_VERSION}", "-y"
    ], check=True)
    print(f"conda 环境 {ENV_NAME} 创建完成")

def install_dependencies():
    """安装项目依赖"""
    print("正在安装项目依赖...")
    
    # 基础依赖
    base_deps = [
        "opencv-python",
        "numpy",
        "pillow",
        "fastapi",
        "uvicorn",
        "websockets",
        "torch",
        "transformers",
        "peft",
        "sentencepiece"
    ]
    
    # 安装基础依赖
    for dep in base_deps:
        print(f"安装 {dep}...")
        subprocess.run([
            "conda", "run", "-n", ENV_NAME,
            "pip", "install", dep
        ], check=True)
    
    # 安装项目依赖
    print("安装项目依赖...")
    subprocess.run([
        "conda", "run", "-n", ENV_NAME,
        "pip", "install", "-e", "."
    ], check=True)
    
    print("所有依赖安装完成")

def main():
    check_conda()
    create_conda_env()
    install_dependencies()
    print(f"\n环境准备就绪！请使用以下命令激活环境：\nconda activate {ENV_NAME}")

if __name__ == "__main__":
    main()