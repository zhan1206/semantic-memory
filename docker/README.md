# 🐳 Docker 部署指南

本文档说明如何使用 Docker 运行 Semantic Memory 服务。

## 前提条件

- Docker 20.10+ 
- Docker Compose 2.0+（可选）
- 4GB+ 可用内存

## 快速启动

### 使用 Docker Compose（推荐）

```bash
# 启动服务
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

服务启动后：
- **API 服务**: http://localhost:8765
- **API 文档**: http://localhost:8765/docs
- **Streamlit UI**: http://localhost:8501

### 使用 Docker 直接运行

```bash
# 构建镜像
docker build -t semantic-memory:latest .

# 运行容器（前台）
docker run -p 8765:8765 -p 8501:8501 \
    -v $(pwd)/data:/app/data \
    semantic-memory:latest

# 运行容器（后台）
docker run -d -p 8765:8765 -p 8501:8501 \
    --name semantic-memory \
    -v $(pwd)/data:/app/data \
    semantic-memory:latest
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `PORT` | `8765` | API 服务端口 |
| `SEMANTIC_MEMORY_DATA_DIR` | `/app/data` | 数据目录（容器内） |
| `MODEL_ID` | `BAAI/bge-small-zh-v1.5` | ONNX 模型 |
| `DEVICE` | `cpu` | 运行设备 |

## 持久化存储

数据默认保存在容器内的 `/app/data`。建议将其映射到宿主机目录：

```bash
docker run -v /your/local/path:/app/data semantic-memory:latest
```

宿主机数据目录结构：

```
data/
├── memories/     # 记忆 JSON 文件
├── kb/           # 知识库数据
├── models/       # ONNX 模型缓存
└── logs/         # 日志文件
```

## GPU 加速

如需使用 GPU 加速（需要 NVIDIA GPU + nvidia-docker）：

```dockerfile
# 使用 onnxruntime-gpu 基础镜像
FROM semantic-memory:latest
RUN pip install onnxruntime-gpu
```

```bash
# 运行（需要 nvidia-container-toolkit）
docker run --gpus all -p 8765:8765 semantic-memory:gpu
```

## 健康检查

```bash
# 检查容器健康状态
docker inspect --format='{{.State.Health.Status}}' semantic-memory

# 手动检查
curl http://localhost:8765/health
```

预期响应：`{"status": "ok", "model": "BAAI/bge-small-zh-v1.5", ...}`

## 日志查看

```bash
# 实时日志
docker compose logs -f

# 仅 API 日志
docker compose logs -f api

# 仅 Streamlit 日志
docker compose logs -f streamlit

# 查看历史日志
docker compose logs --tail=100
```

## 数据备份

```bash
# 备份（运行时）
tar czvf semantic-memory-backup.tar.gz data/

# 恢复
tar xzvf semantic-memory-backup.tar.gz
```

## 端口冲突

如果 8765 或 8501 端口被占用，修改 `docker-compose.yml` 中的端口映射：

```yaml
services:
  api:
    ports:
      - "9876:8765"  # 改为 9876
  streamlit:
    ports:
      - "8585:8501"  # 改为 8585
```

## 故障排查

**容器启动失败**
```bash
# 查看详细日志
docker compose up
```

**模型下载失败**
```bash
# 进入容器手动下载
docker exec -it semantic-memory bash
python -c "from memory_manager import MemoryManager; MemoryManager()"
```

**权限问题（Linux）**
```bash
# 设置目录权限
sudo chown -R 1000:1000 ./data
```

**macOS 性能问题**
macOS 上 Docker 文件共享较慢，建议将 `data` 目录放在容器内：
```yaml
# docker-compose.yml
volumes:
  - semantic-memory-data:/app/data

volumes:
  semantic-memory-data:
```
