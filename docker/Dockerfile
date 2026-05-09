FROM python:3.11-slim

LABEL maintainer="QClaw / OpenClaw Community"
LABEL description="Semantic Memory — OpenClaw Local Semantic Memory & Retrieval System"

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NO_COLOR=1

WORKDIR /app

# 安装系统依赖（FAISS 需要）
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY scripts/ ./scripts/
COPY SKILL.md .
COPY README.md .

# 创建数据目录
ENV QCLAW_DATA=/data
RUN mkdir -p $QCLAW_DATA/semantic-memory/{memories,kb,models,logs}

# 暴露端口
EXPOSE 8765

# 默认启动 API 服务
CMD ["python", "scripts/api_server.py", "--host", "0.0.0.0", "--port", "8765"]

# 可选启动命令
# CMD ["python", "scripts/run.py", "stats"]
# CMD ["python", "-c", "from scripts.installer import main; main()"]
