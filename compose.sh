#!/bin/bash

# 脚本：安装 Docker Compose 插件以支持 `docker compose` 命令

# 设置错误退出
set -e

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 错误退出函数
error_exit() {
    log "错误：$1"
    exit 1
}

log "==== 开始安装 Docker Compose 插件 ===="

# 检查是否以 root 或 sudo 运行
log "检查是否以 root 或 sudo 运行..."
if [[ $EUID -ne 0 ]]; then
    error_exit "请以 root 用户或使用 sudo 运行此脚本。"
fi

# 检查 Docker 是否已安装
log "检查 Docker 是否已安装..."
if ! command -v docker >/dev/null 2>&1; then
    error_exit "未检测到 Docker，请先安装 Docker。参考：https://docs.docker.com/engine/install/"
fi

# 检查 Docker 服务状态
log "检查 Docker 服务状态..."
if ! systemctl is-active --quiet docker; then
    log "Docker 服务未运行，尝试启动..."
    systemctl start docker || error_exit "无法启动 Docker 服务，请检查：sudo systemctl status docker"
fi

# 获取最新 Docker Compose 版本
log "获取最新 Docker Compose 版本..."
COMPOSE_VERSION=$(curl -s https://api.github.com/repos/docker/compose/releases/latest | grep 'tag_name' | cut -d '"' -f 4)
if [ -z "$COMPOSE_VERSION" ]; then
    log "警告：无法获取最新版本，使用默认版本 v2.26.1"
    COMPOSE_VERSION="v2.26.1"
fi

# 创建插件目录
PLUGIN_DIR="/usr/local/lib/docker/cli-plugins"
log "创建插件目录（如果不存在）：$PLUGIN_DIR"
mkdir -p "$PLUGIN_DIR" || error_exit "无法创建目录 $PLUGIN_DIR"

# 下载 Docker Compose 插件
log "下载 Docker Compose 插件（版本 $COMPOSE_VERSION）..."
curl -SL "https://github.com/docker/compose/releases/download/${COMPOSE_VERSION}/docker-compose-linux-$(uname -m)" -o "${PLUGIN_DIR}/docker-compose" || error_exit "无法下载 Docker Compose 插件"

# 赋予执行权限
log "赋予执行权限..."
chmod +x "${PLUGIN_DIR}/docker-compose" || error_exit "无法设置执行权限"

# 重启 Docker 服务
log "重启 Docker 服务以加载插件..."
systemctl restart docker || error_exit "无法重启 Docker 服务，请检查：sudo systemctl status docker"

# 验证安装
log "验证安装版本..."
if docker compose version >/dev/null 2>&1; then
    log "Docker Compose 插件安装成功，版本：$(docker compose version)"
else
    error_exit "Docker Compose 插件安装失败。请检查：ls -l ${PLUGIN_DIR}/docker-compose 和 sudo systemctl status docker"
fi

log "✅ Docker Compose 安装完成"