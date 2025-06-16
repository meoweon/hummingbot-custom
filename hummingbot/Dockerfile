# 设置基础镜像，使用 continuumio/miniconda3:latest
FROM continuumio/miniconda3:latest AS builder

# 安装系统依赖，确保最小化镜像大小
# - libusb-1.0, gcc, g++, python3-dev 用于 Hummingbot 的编译和运行
# - 清理 apt 缓存以减小镜像体积
RUN apt-get update && \
    apt-get install -y sudo libusb-1.0 gcc g++ python3-dev && \
    rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /home/hummingbot

# 创建 conda 环境
# - 复制 environment.yml 并创建 hummingbot 环境
# - 清理 conda 缓存
COPY setup/environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml && \
    conda clean -afy && \
    rm /tmp/environment.yml

# 复制 Hummingbot 项目文件
COPY bin/ bin/
COPY hummingbot/ hummingbot/
COPY scripts/ scripts/
COPY controllers/ controllers/
COPY scripts/ scripts-copy/
COPY setup.py .
COPY LICENSE .
COPY README.md .

# 设置 bash 为默认 shell，使用登录模式 (-l) 以加载 .bashrc 或 .bash_profile
SHELL ["/bin/bash", "-lc"]

# 初始化 conda 并配置 .bashrc 和 .bash_profile
# - 运行 conda init bash，确保生成正确的 shell 初始化代码
# - 在 .bashrc 中添加 conda 初始化和自动激活
# - 在 .bash_profile 中确保加载 .bashrc，兼容登录 shell
RUN /opt/conda/bin/conda init bash && \
    echo '. /opt/conda/etc/profile.d/conda.sh' >> /root/.bashrc && \
    echo 'conda activate hummingbot' >> /root/.bashrc && \
    echo '[ -f /root/.bashrc ] && . /root/.bashrc' > /root/.bash_profile

# 安装 pip 依赖
COPY setup/pip_packages.txt /tmp/pip_packages.txt
RUN python3 -m pip install --no-deps -r /tmp/pip_packages.txt && \
    rm /tmp/pip_packages.txt

# 编译 Hummingbot 的 C++ 扩展
RUN python3 setup.py build_ext --inplace -j 8 && \
    rm -rf build/ && \
    find . -type f -name "*.cpp" -delete

# 安装 Hummingbot 包
RUN pip install -e .

# 创建最终发布镜像
FROM continuumio/miniconda3:latest AS release

# 设置镜像元数据
LABEL maintainer="Fede Cardoso @dardonacci <federico@hummingbot.org>"
ARG BRANCH=""
ARG COMMIT=""
ARG BUILD_DATE=""
deal branch=${BRANCH}
LABEL commit=${COMMIT}
LABEL date=${BUILD_DATE}

# 设置环境变量
ENV COMMIT_SHA=${COMMIT}
ENV COMMIT_BRANCH=${BRANCH}
ENV BUILD_DATE=${BUILD_DATE}
ENV INSTALLATION_TYPE=docker

# 安装系统依赖
RUN apt-get update && \
    apt-get install -y sudo libusb-1.0 && \
    rm -rf /var/lib/apt/lists/*

# 创建挂载点
RUN mkdir -p /home/hummingbot/conf \
             /home/hummingbot/conf/connectors \
             /home/hummingbot/conf/strategies \
             /home/hummingbot/conf/controllers \
             /home/hummingbot/conf/scripts \
             /home/hummingbot/logs \
             /home/hummingbot/data \
             /home/hummingbot/certs \
             /home/hummingbot/scripts \
             /home/hummingbot/controllers

# 设置工作目录
WORKDIR /home/hummingbot

# 从 builder 阶段复制构建产物
COPY --from=builder /opt/conda/ /opt/conda/
COPY --from=builder /home/ /home/

# 设置 bash 为默认 shell
SHELL ["/bin/bash", "-lc"]

# 配置 .bashrc 和 .bash_profile
# - 与 builder 阶段一致，确保登录和非登录 shell 都加载 conda
# . /opt/conda/etc/profile.d/conda.sh
RUN /opt/conda/bin/conda init bash && \
    echo '. /opt/conda/etc/profile.d/conda.sh' >> /root/.bashrc && \
    echo 'conda activate hummingbot' >> /root/.bashrc && \
    echo '[ -f /root/.bashrc ] && . /root/.bashrc' > /root/.bash_profile

# 设置默认命令为交互式 bash 终端
# - 使用登录 shell (-l) 确保加载 .bash_profile 和 .bashrc
CMD ["/bin/bash", "-l"]