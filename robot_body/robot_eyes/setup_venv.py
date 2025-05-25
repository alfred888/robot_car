#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
from pathlib import Path

def check_venv():
    """检查虚拟环境是否存在，如果不存在则创建"""
    venv_path = Path(__file__).parent / "venv"
    if not venv_path.exists():
        print("创建虚拟环境...")
        venv.create(venv_path, with_pip=True)
        print("虚拟环境创建完成")
    return venv_path

def install_requirements():
    """安装依赖包"""
    venv_python = Path(__file__).parent / "venv/bin/python"
    requirements = Path(__file__).parent / "requirements.txt"
    
    print("安装依赖包...")
    # 先升级 pip
    subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"])
    # 安装依赖
    subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(requirements)])
    print("依赖包安装完成")

def activate_venv():
    """激活虚拟环境"""
    venv_path = Path(__file__).parent / "venv"
    activate_script = venv_path / "bin/activate"
    python_path = venv_path / "bin/python"
    
    if not activate_script.exists():
        print(f"错误：找不到虚拟环境激活脚本: {activate_script}")
        sys.exit(1)
    
    # 获取当前环境变量
    env = os.environ.copy()
    
    # 修改 PATH 环境变量
    env["PATH"] = str(venv_path / "bin") + os.pathsep + env["PATH"]
    
    # 设置 PYTHONPATH
    env["PYTHONPATH"] = str(Path(__file__).parent) + os.pathsep + env.get("PYTHONPATH", "")
    
    return env, str(python_path)

def main():
    """主函数"""
    # 检查系统类型
    if sys.platform == "win32":
        print("错误：此脚本不支持 Windows 系统")
        sys.exit(1)
    
    # 检查虚拟环境
    check_venv()
    
    # 安装依赖
    install_requirements()
    
    # 激活虚拟环境
    env, python_path = activate_venv()
    
    print("虚拟环境设置完成！")
    print(f"Python 解释器路径: {python_path}")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")

if __name__ == "__main__":
    main() 