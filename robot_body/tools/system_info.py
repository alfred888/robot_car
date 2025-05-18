#!/usr/bin/env python3
import os
import sys
import platform
import psutil
import subprocess
from datetime import datetime
import json

def get_cpu_info():
    """获取CPU信息"""
    cpu_info = {
        "model": platform.processor(),
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "max_frequency": psutil.cpu_freq().max if psutil.cpu_freq() else None,
        "current_frequency": psutil.cpu_freq().current if psutil.cpu_freq() else None,
        "usage_per_core": [f"{x}%" for x in psutil.cpu_percent(percpu=True)],
        "total_usage": f"{psutil.cpu_percent()}%"
    }
    return cpu_info

def get_memory_info():
    """获取内存信息"""
    memory = psutil.virtual_memory()
    swap = psutil.swap_memory()
    memory_info = {
        "total": f"{memory.total / (1024**3):.2f}GB",
        "available": f"{memory.available / (1024**3):.2f}GB",
        "used": f"{memory.used / (1024**3):.2f}GB",
        "percentage": f"{memory.percent}%",
        "swap_total": f"{swap.total / (1024**3):.2f}GB",
        "swap_used": f"{swap.used / (1024**3):.2f}GB",
        "swap_percentage": f"{swap.percent}%"
    }
    return memory_info

def get_disk_info():
    """获取磁盘信息"""
    partitions = psutil.disk_partitions()
    disk_info = []
    for partition in partitions:
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            disk_info.append({
                "device": partition.device,
                "mountpoint": partition.mountpoint,
                "fstype": partition.fstype,
                "total": f"{usage.total / (1024**3):.2f}GB",
                "used": f"{usage.used / (1024**3):.2f}GB",
                "free": f"{usage.free / (1024**3):.2f}GB",
                "percentage": f"{usage.percent}%"
            })
        except:
            continue
    return disk_info

def get_network_info():
    """获取网络信息"""
    network_info = {
        "hostname": platform.node(),
        "ip_addresses": [],
        "interfaces": []
    }
    
    # 获取所有网络接口
    interfaces = psutil.net_if_addrs()
    for interface, addrs in interfaces.items():
        interface_info = {
            "name": interface,
            "addresses": []
        }
        for addr in addrs:
            if addr.family == 2:  # IPv4
                interface_info["addresses"].append({
                    "type": "IPv4",
                    "address": addr.address,
                    "netmask": addr.netmask
                })
            elif addr.family == 10:  # IPv6
                interface_info["addresses"].append({
                    "type": "IPv6",
                    "address": addr.address,
                    "netmask": addr.netmask
                })
        network_info["interfaces"].append(interface_info)
    
    return network_info

def get_temperature():
    """获取温度信息"""
    try:
        temp = subprocess.check_output(['vcgencmd', 'measure_temp']).decode()
        return temp.strip().split('=')[1]
    except:
        return "N/A"

def get_gpu_info():
    """获取GPU信息"""
    try:
        gpu_mem = subprocess.check_output(['vcgencmd', 'get_mem', 'gpu']).decode()
        return gpu_mem.strip().split('=')[1]
    except:
        return "N/A"

def get_os_info():
    """获取操作系统信息"""
    os_info = {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version()
    }
    return os_info

def get_process_info():
    """获取进程信息"""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
        try:
            pinfo = proc.info
            if pinfo['cpu_percent'] > 0 or pinfo['memory_percent'] > 0:
                processes.append({
                    "pid": pinfo['pid'],
                    "name": pinfo['name'],
                    "cpu_percent": f"{pinfo['cpu_percent']}%",
                    "memory_percent": f"{pinfo['memory_percent']:.1f}%"
                })
        except:
            continue
    return sorted(processes, key=lambda x: float(x['cpu_percent'].strip('%')), reverse=True)[:10]

def main():
    """主函数"""
    system_info = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "os_info": get_os_info(),
        "cpu_info": get_cpu_info(),
        "memory_info": get_memory_info(),
        "disk_info": get_disk_info(),
        "network_info": get_network_info(),
        "temperature": get_temperature(),
        "gpu_memory": get_gpu_info(),
        "top_processes": get_process_info()
    }
    
    # 创建输出目录
    output_dir = "system_info"
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存为JSON文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = os.path.join(output_dir, f"system_info_{timestamp}.json")
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(system_info, f, indent=4, ensure_ascii=False)
    
    print(f"系统信息已保存到: {output_file}")
    
    # 打印摘要信息
    print("\n系统信息摘要:")
    print(f"时间: {system_info['timestamp']}")
    print(f"系统: {system_info['os_info']['system']} {system_info['os_info']['release']}")
    print(f"CPU: {system_info['cpu_info']['model']} ({system_info['cpu_info']['total_cores']}核)")
    print(f"内存: {system_info['memory_info']['total']} (使用率: {system_info['memory_info']['percentage']})")
    print(f"温度: {system_info['temperature']}")
    print(f"GPU内存: {system_info['gpu_memory']}")
    print("\n前5个最耗CPU的进程:")
    for proc in system_info['top_processes'][:5]:
        print(f"{proc['name']}: CPU {proc['cpu_percent']}, 内存 {proc['memory_percent']}")

if __name__ == "__main__":
    main() 