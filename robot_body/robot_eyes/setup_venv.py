#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
from pathlib import Path

def install_system_dependencies():
    """安装系统依赖"""
    print("安装系统依赖...")
    try:
        # 检测系统类型
        if os.path.exists('/etc/debian_version'):  # Debian/Ubuntu/Raspberry Pi OS
            subprocess.run(['sudo', 'apt-get', 'update'])
            subprocess.run(['sudo', 'apt-get', 'install', '-y', 
                          'libcap-dev',  # 用于 python-prctl
                          'python3-dev',  # Python 开发头文件
                          'libatlas-base-dev',  # 用于 numpy
                          'libhdf5-dev',  # 用于 h5py
                          'libopenjp2-7',  # 用于 Pillow
                          'libtiff5',  # 用于 Pillow
                          'libavcodec-dev',  # 用于 opencv
                          'libavformat-dev',
                          'libswscale-dev',
                          'libv4l-dev',
                          'libxvidcore-dev',
                          'libx264-dev',
                          'libjpeg-dev',
                          'libpng-dev',
                          'libtiff-dev',
                          'libgstreamer1.0-dev',
                          'libgstreamer-plugins-base1.0-dev',
                          'libgstreamer-plugins-bad1.0-dev',
                          'gstreamer1.0-plugins-base',
                          'gstreamer1.0-plugins-good',
                          'gstreamer1.0-plugins-bad',
                          'gstreamer1.0-plugins-ugly',
                          'gstreamer1.0-libav',
                          'gstreamer1.0-tools',
                          'gstreamer1.0-x',
                          'gstreamer1.0-alsa',
                          'gstreamer1.0-gl',
                          'gstreamer1.0-gtk3',
                          'gstreamer1.0-qt5',
                          'gstreamer1.0-pulseaudio'
                          ])
        elif sys.platform == "darwin":  # macOS
            subprocess.run(['brew', 'install', 
                          'libcap',  # 用于 python-prctl
                          'python@3.9',  # Python 开发头文件
                          'opencv',  # OpenCV
                          'numpy',  # NumPy
                          'hdf5',  # 用于 h5py
                          'jpeg',  # 用于 Pillow
                          'libtiff',  # 用于 Pillow
                          'libpng'  # 用于 Pillow
                          ])
        print("系统依赖安装完成")
    except Exception as e:
        print(f"安装系统依赖时出错: {e}")
        sys.exit(1)

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
    
    # 安装系统依赖
    install_system_dependencies()
    
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