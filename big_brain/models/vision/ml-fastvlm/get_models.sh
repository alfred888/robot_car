#!/usr/bin/env bash
#
# For licensing see accompanying LICENSE_MODEL file.
# Copyright (C) 2025 Apple Inc. All Rights Reserved.
#

# 创建模型目录
MODELS_DIR="$HOME/models/fastvlm"
mkdir -p "$MODELS_DIR"

# 下载模型
wget https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_0.5b_stage2.zip -P "$MODELS_DIR"
wget https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_0.5b_stage3.zip -P "$MODELS_DIR"
wget https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_1.5b_stage2.zip -P "$MODELS_DIR"
wget https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_1.5b_stage3.zip -P "$MODELS_DIR"
wget https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_7b_stage2.zip -P "$MODELS_DIR"
wget https://ml-site.cdn-apple.com/datasets/fastvlm/llava-fastvithd_7b_stage3.zip -P "$MODELS_DIR"

# 解压模型
cd "$MODELS_DIR"
unzip -qq llava-fastvithd_0.5b_stage2.zip
unzip -qq llava-fastvithd_0.5b_stage3.zip
unzip -qq llava-fastvithd_1.5b_stage2.zip
unzip -qq llava-fastvithd_1.5b_stage3.zip
unzip -qq llava-fastvithd_7b_stage2.zip
unzip -qq llava-fastvithd_7b_stage3.zip

# 清理
rm llava-fastvithd_0.5b_stage2.zip
rm llava-fastvithd_0.5b_stage3.zip
rm llava-fastvithd_1.5b_stage2.zip
rm llava-fastvithd_1.5b_stage3.zip
rm llava-fastvithd_7b_stage2.zip
rm llava-fastvithd_7b_stage3.zip

echo "模型已下载并解压到: $MODELS_DIR"
