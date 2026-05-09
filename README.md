# Semantic Memory

**OpenClaw 本地语义记忆与检索系统**

基于 ONNX + FAISS 的完全离线语义记忆系统，支持本地 Embedding 模型推理、向量检索、自动遗忘和知识库管理。

## 项目结构

```
semantic-memory/
├── scripts/
│   ├── core.py              # ONNX Embedding 引擎（CPU 推理）
│   ├── vector_store.py      # FAISS 向量存储（自动 IVF 索引）
│   ├── memory_manager.py    # 记忆 CRUD + 知识库 + 加密
│   ├── sensitive_filter.py  # 敏感信息自动脱敏
│   ├── doc_parser.py        # PDF/DOCX/TXT 文档解析
│   ├── config.py            # JSON 配置管理
│   ├── installer.py         # 依赖自动安装
│   ├── logging.py           # 统一日志（彩色 + 文件轮转）
│   ├── run.py               # CLI 入口（30+ 命令）
│   ├── api_server.py        # FastAPI REST API 服务
│   ├── interactive.py       # 交互式 CLI 模式
│   └── batch.py             # 批量操作工具
├── tests/                   # pytest 测试套件
│   ├── conftest.py          # 全局 fixtures
│   ├── test_sensitive_filter.py
│   ├── test_config.py
│   ├── test_vector_store.py
│   ├── test_memory_manager.py
│   └── test_doc_parser.py
├── references/
│   ├── architecture.md      # 技术架构文档
│   └── commands.md          # CLI 命令参考
├── shell/                   # Shell 自动补全脚本
│   ├── semantic-memory.bash
│   ├── semantic-memory.zsh
│   └── semantic-memory.fish
├── docker/                  # Docker 支持
│   └── Dockerfile
├── tests/                   # 测试套件
├── SKILL.md                 # OpenClaw Skill 元数据
├── pyproject.toml           # 项目配置（setuptools + pytest）
└── requirements.txt         # 依赖列表
```

## 快速开始

### 1. 安装依赖

```bash
# 自动安装（推荐）
python scripts/installer.py

# 或用 pip
pip install -r requirements.txt
```

### 2. CLI 基本操作

```bash
# 添加记忆
python scripts/run.py add "今天和张三讨论了AI项目进展" --tags "工作" --importance 0.8

# 语义搜索
python scripts/run.py search "张三讨论了什么" --top-k 3

# 召回并格式化为上下文
python scripts/run.py recall "项目进展如何" --max-chars 2000

# 查看统计
python scripts/run.py stats

# 交互模式
python scripts/run.py --interactive
```

### 3. 启动 API 服务

```bash
# REST API
python scripts/api_server.py --port 8765

# 访问文档 http://localhost:8765/docs
```

### 4. Docker 部署

```bash
cd docker
docker build -t semantic-memory .
docker run -p 8765:8765 -v ~/.qclaw/data:/data semantic-memory
```

## 开发

### 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行全部测试
pytest tests/ -v

# 覆盖率报告
pytest tests/ -v --cov=semantic_memory --cov-report=html
```

### 启动 API 服务（开发模式）

```bash
python scripts/api_server.py --host 0.0.0.0 --port 8765 --reload --log-level debug
```

## 主要特性

- 🧠 **本地 Embedding**：ONNX 量化模型，CPU 极速推理（<50ms）
- 🔍 **语义检索**：FAISS 向量数据库，自动 IVF 索引升级
- 📚 **知识库**：跨会话文档管理，支持 PDF/DOCX/TXT
- 🔒 **隐私优先**：100% 离线，敏感信息自动脱敏
- ⏰ **自动遗忘**：重要性衰减 + 低价值清理
- 🔐 **可选加密**：Fernet 对称加密（AES-256）
- 🌐 **API 服务**：FastAPI REST 接口，支持 Docker 部署

## 配置

配置文件位于 `~/.qclaw/data/semantic-memory/config.json`。

```bash
# 查看配置
python scripts/run.py config get

# 修改配置
python scripts/run.py config set search_top_k 10
python scripts/run.py config set model_id bge-small-zh-v1.5  # 中文模型
python scripts/run.py config set half_life_days 60           # 延长半衰期
```

## License

MIT
