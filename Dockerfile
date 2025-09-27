FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app/src
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PATH=/app/src/codelinter/command-line-tools/bin:$PATH
ENV NODE_VERSION=18.19.0
ENV NODE_HOME=/usr/local/node
ENV PATH=$NODE_HOME/bin:$PATH
ENV JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
ENV PATH=$JAVA_HOME/bin:$PATH

ENV DEBIAN_FRONTEND=noninteractive
RUN set -eux; \
    codename=$(awk -F= '/VERSION_CODENAME/{print $2}' /etc/os-release); \
    if [ -f /etc/apt/sources.list.d/debian.sources ]; then \
      sed -i 's|http://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources; \
      sed -i 's|https://deb.debian.org/debian|http://mirrors.aliyun.com/debian|g' /etc/apt/sources.list.d/debian.sources; \
      sed -i 's|http://security.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
      sed -i 's|https://security.debian.org/debian-security|http://mirrors.aliyun.com/debian-security|g' /etc/apt/sources.list.d/debian.sources; \
    else \
      printf 'deb http://mirrors.aliyun.com/debian %s main\n' "$codename" > /etc/apt/sources.list; \
      printf 'deb http://mirrors.aliyun.com/debian %s-updates main\n' "$codename" >> /etc/apt/sources.list; \
      printf 'deb http://mirrors.aliyun.com/debian-security %s-security main\n' "$codename" >> /etc/apt/sources.list; \
    fi; \
    apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    xz-utils \
    libgl1 \
    openjdk-21-jre-headless \
    && rm -rf /var/lib/apt/lists/*

# 安装 Node.js
RUN mkdir -p $NODE_HOME/bin && \
    cd /tmp && \
    wget https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz && \
    tar -xJf node-v${NODE_VERSION}-linux-x64.tar.xz -C /usr/local --strip-components=1 && \
    rm node-v${NODE_VERSION}-linux-x64.tar.xz && \
    ln -s /usr/local/bin/node $NODE_HOME/bin/node && \
    ln -s /usr/local/bin/npm $NODE_HOME/bin/npm && \
    node --version && \
    npm --version

# 复制依赖文件
COPY requirements.txt ./

# 安装Python依赖
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set global.extra-index-url https://pypi.tuna.tsinghua.edu.cn/simple && \
    pip config set global.trusted-host "mirrors.aliyun.com pypi.tuna.tsinghua.edu.cn"
RUN pip install -r requirements.txt

# 复制源代码
COPY src/ ./src/
COPY models/ ./models/
COPY server3.py ./
COPY upload.py ./

# 创建空文件
RUN mkdir -p /app/src/A21_C__open-harmony/entry && touch /app/src/A21_C__open-harmony/entry/result

# 暴露端口
EXPOSE 8000 8001

# 启动命令（进入 src 目录，后台启动 upload，再前台启动 server3）
CMD ["sh", "-c", "python -m upload & python server3.py"]