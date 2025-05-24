FROM nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y \
    python3.10 \
    python3-pip \
    git \
    wget \
    && rm -rf /var/lib/apt/lists/*

# 安装Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh \
    && bash miniconda.sh -b -p /opt/conda \
    && rm miniconda.sh

# 设置环境变量
ENV PATH="/opt/conda/bin:${PATH}"

# 创建conda环境
COPY environment.yml .
RUN conda env create -f environment.yml

# 复制项目文件
COPY . .

# 设置环境变量
ENV PYTHONPATH=/app

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["conda", "run", "-n", "fastvlm", "python", "start_socket_service_fastvlm.py"] 