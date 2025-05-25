#!/usr/bin/env python3
import os
import sys
import subprocess
import venv
from pathlib import Path

def run_command(cmd, description):
    """运行命令并处理错误"""
    print(f"\n{description}...")
    print(f"执行命令: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print("命令输出:")
            print(result.stdout)
        if result.stderr:
            print("警告/错误输出:")
            print(result.stderr)
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误: {e}")
        print(f"命令输出: {e.stdout}")
        print(f"错误输出: {e.stderr}")
        return False
    except Exception as e:
        print(f"执行命令时出错: {e}")
        return False

def install_system_dependencies():
    """安装系统依赖"""
    print("\n=== 开始安装系统依赖 ===")
    
    # 检测系统类型
    if os.path.exists('/etc/debian_version'):  # Debian/Ubuntu/Raspberry Pi OS
        # 更新包列表
        if not run_command(['sudo', 'apt-get', 'update'], "更新包列表"):
            print("更新包列表失败")
            return False
            
        # 安装基本开发工具
        if not run_command(['sudo', 'apt-get', 'install', '-y', 'build-essential'], "安装基本开发工具"):
            print("安装基本开发工具失败")
            return False
            
        # 安装 Python 开发包
        if not run_command(['sudo', 'apt-get', 'install', '-y', 'python3-dev'], "安装 Python 开发包"):
            print("安装 Python 开发包失败")
            return False
            
        # 安装 libcap 开发包
        if not run_command(['sudo', 'apt-get', 'install', '-y', 'libcap-dev'], "安装 libcap 开发包"):
            print("安装 libcap 开发包失败")
            return False
            
        # 安装其他依赖
        dependencies = [
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
        ]
        
        if not run_command(['sudo', 'apt-get', 'install', '-y'] + dependencies, "安装其他依赖"):
            print("安装其他依赖失败")
            return False
            
    elif sys.platform == "darwin":  # macOS
        # 检查是否安装了 Homebrew
        if not run_command(['which', 'brew'], "检查 Homebrew"):
            print("请先安装 Homebrew: https://brew.sh/")
            return False
            
        # 更新 Homebrew
        if not run_command(['brew', 'update'], "更新 Homebrew"):
            print("更新 Homebrew 失败")
            return False
            
        # 安装依赖
        dependencies = [
            'libcap',  # 用于 python-prctl
            'python@3.9',  # Python 开发头文件
            'opencv',  # OpenCV
            'numpy',  # NumPy
            'hdf5',  # 用于 h5py
            'jpeg',  # 用于 Pillow
            'libtiff',  # 用于 Pillow
            'libpng'  # 用于 Pillow
        ]
        
        print("\n准备安装以下依赖:")
        for dep in dependencies:
            print(f"- {dep}")
            
        if not run_command(['brew', 'install'] + dependencies, "安装 Homebrew 依赖"):
            print("安装 Homebrew 依赖失败")
            return False
    else:
        print(f"不支持的操作系统: {sys.platform}")
        return False
        
    print("\n=== 系统依赖安装完成 ===")
    return True

def check_venv():
    """检查虚拟环境是否存在，如果不存在则创建"""
    venv_path = Path(__file__).parent / "venv"
    if not venv_path.exists():
        print("\n=== 创建虚拟环境 ===")
        try:
            venv.create(venv_path, with_pip=True)
            print("虚拟环境创建完成")
        except Exception as e:
            print(f"创建虚拟环境时出错: {e}")
            return False
    return True

def install_requirements():
    """安装依赖包"""
    venv_python = Path(__file__).parent / "venv/bin/python"
    requirements = Path(__file__).parent / "requirements.txt"
    
    print("\n=== 安装 Python 依赖包 ===")
    
    # 升级 pip
    if not run_command([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], "升级 pip"):
        print("升级 pip 失败")
        return False
        
    # 安装依赖
    if not run_command([str(venv_python), "-m", "pip", "install", "-r", str(requirements)], "安装依赖包"):
        print("安装依赖包失败")
        return False
        
    print("依赖包安装完成")
    return True

def activate_venv():
    """激活虚拟环境"""
    venv_path = Path(__file__).parent / "venv"
    activate_script = venv_path / "bin/activate"
    python_path = venv_path / "bin/python"
    
    if not activate_script.exists():
        print(f"错误：找不到虚拟环境激活脚本: {activate_script}")
        return False
    
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
    if not install_system_dependencies():
        print("安装系统依赖失败，退出")
        sys.exit(1)
    
    # 检查虚拟环境
    if not check_venv():
        print("创建虚拟环境失败，退出")
        sys.exit(1)
    
    # 安装依赖
    if not install_requirements():
        print("安装 Python 依赖失败，退出")
        sys.exit(1)
    
    # 激活虚拟环境
    env, python_path = activate_venv()
    
    print("\n=== 虚拟环境设置完成！===")
    print(f"Python 解释器路径: {python_path}")
    print(f"PYTHONPATH: {env['PYTHONPATH']}")

if __name__ == "__main__":
    main() 