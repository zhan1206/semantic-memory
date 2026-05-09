# 🧠 Semantic Memory

> 为 AI Agent 打造的本地语义记忆与检索系统 — 完全离线，保护隐私

[![GitHub stars](https://img.shields.io/github/stars/zhan1206/semantic-memory?style=flat-square&logo=github)](https://github.com/zhan1206/semantic-memory)
[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=flat-square)](LICENSE)
[![Offline](https://img.shields.io/badge/Offline-100%25-brightgreen?style=flat-square&logo=shield)](README.md)
[![Vector DB: FAISS](https://img.shields.io/badge/Vector%20DB-FAISS-orange?style=flat-square&logo=apache)](https://github.com/facebookresearch/faiss)
[![Embedding: ONNX](https://img.shields.io/badge/Embedding-ONNX%20Runtime-blue?style=flat-square&logo=onnx)](https://onnxruntime.ai/)

## 🎯 是什么

Semantic Memory 是 OpenClaw Agent 的长期记忆模块，基于 **ONNX + FAISS** 实现**完全离线的向量语义检索**，无需任何 API Key，不依赖云服务，数据完全保留在本地。

核心能力：

- **🔍 语义搜索** — 输入自然语言，瞬间在全量记忆中检索相关内容
- **💾 记忆管理** — 添加、编辑、删除、标签化、重要性评分
- **📚 知识库** — 多文档管理、批量导入、文档问答
- **🤖 AI 上下文召回** — 自动为 AI 提供相关记忆作为上下文
- **⚡ 完全离线** — ONNX 模型本地推理，零网络依赖

---

## 🚀 快速开始

### 安装依赖

```bash
# 克隆或进入项目目录
cd semantic-memory

# 安装核心依赖
pip install -r requirements.txt

# 仅核心功能（不含文档解析）
pip install onnxruntime faiss-cpu numpy chardet

# 完整安装（含 PDF/DOCX/XLSX 解析）
pip install PyPDF2 python-docx openpyxl python-pptx cryptography

# 可选：Web UI
pip install streamlit

# 可选：API 服务
pip install fastapi uvicorn
```

### 首次运行（自动下载模型）

```python
from memory_manager import MemoryManager

mgr = MemoryManager()  # 首次自动下载 ~100MB ONNX 模型
```

### 基础用法

```python
from memory_manager import MemoryManager

mgr = MemoryManager()

# ── 添加记忆 ──
mem_id = mgr.add(
    text="今天和张三讨论了 AI 项目进展，效果很好。",
    tags=["工作", "AI项目"],
    importance=0.8,
    source="conversation",
)
print(f"记忆已保存: {mem_id}")

# ── 语义搜索 ──
results = mgr.search("AI 项目进展如何？", top_k=5)
for r in results:
    print(f"  相似度 {r['score']:.2%} | {r['text'][:50]}...")

# ── AI 上下文召回 ──
context = mgr.recall("张三的项目讨论", max_chars=2000)
print(context)  # 可直接粘贴给大模型

# ── 知识库 ──
mgr.create_kb("我的文档库", "存放工作文档")
```

---

## 📖 详细用法

### 1. 添加记忆

```python
# 单条记忆
mem_id = mgr.add(
    text="用户偏好在微信沟通",
    tags=["用户", "偏好"],
    importance=0.9,
    source="manual",
)

# 批量添加
mem_ids = mgr.batch_add([
    {"text": "张三负责前端", "tags": ["工作"]},
    {"text": "李四负责后端", "tags": ["工作"]},
])

# 自动分块（长文本自动切分）
mem_id = mgr.add("长文本内容..." * 100, auto_chunk=True)
```

### 2. 语义搜索

```python
# 标准搜索
results = mgr.search(
    query="张三的联系方式",
    top_k=5,               # 返回数量
    tag="工作",             # 标签过滤（可选）
    min_score=0.5,          # 最低相似度（可选）
    kb_name="我的文档库",   # 知识库搜索（可选）
)

for r in results:
    print(f"[{r['score']:.2%}] {r['text']}")
    print(f"  标签: {r['tags']} | 重要性: {r['importance']:.1f}")
```

### 3. AI 上下文召回

专为 AI 对话设计，自动将相关记忆格式化为连贯上下文：

```python
# 生成 AI 可直接使用的上下文
context = mgr.recall(
    query="用户的工作偏好",
    max_chars=3000,     # 最大字符数
    top_k=10,
)

# 效果示例：
# [记忆 abc123] 今天和张三讨论了AI项目进展，效果很好。
# [记忆 def456] 用户偏好通过微信沟通。
```

### 4. 知识库

将文档库与记忆系统隔离管理：

```python
# 创建知识库
mgr.create_kb("我的文档库", description="存放工作相关文档")

# 导入文档
from doc_parser import import_file_to_kb, import_directory_to_kb

# 单文件导入
import_file_to_kb("report.pdf", "我的文档库")

# 批量导入整个目录
import_directory_to_kb("./documents/", "我的文档库", tags=["归档"])

# 知识库语义搜索
results = mgr.query_kb("我的文档库", "年度报告摘要", top_k=3)
```

### 5. 交互式 CLI

```bash
python scripts/interactive.py
```

```
╔══════════════════════════════════════════════════════╗
║         Semantic Memory 交互式管理                  ║
╚══════════════════════════════════════════════════════╝

  [1] 💾 添加记忆
  [2] 🔍 语义搜索
  [3] 📋 记忆列表
  [4] 🗑️  删除记忆
  [5] 📚 知识库
  [6] ⚙️  配置管理
  [7] 📊 统计信息
  [0] 🚪 退出

请选择操作: _
```

Shell 自动补全（bash / zsh / fish）：

```bash
# bash
echo 'eval "$(python -m memory.completion bash)"' >> ~/.bashrc

# zsh
echo 'eval "$(python -m memory.completion zsh)"' >> ~/.zshrc

# fish
python -m memory.completion fish > ~/.config/fish/completions/memory.fish
```

### 6. Web UI

```bash
streamlit run scripts/streamlit_app.py
```

提供 7 个页面：

| 页面 | 功能 |
|------|------|
| 🔍 语义搜索 | 输入自然语言，秒级检索 |
| 💾 添加记忆 | 单条或批量导入文件 |
| 📋 记忆列表 | 分页浏览、搜索、删除 |
| 📊 统计信息 | 标签分布、来源统计、性能指标 |
| 📚 知识库 | 创建、导入、查询文档库 |
| ⚙️ 配置管理 | 可视化修改所有配置项 |
| 🏗️ 批量操作 | 批量删除、标签管理、导出 |

### 7. REST API 服务

```bash
python -m uvicorn scripts.api_server:app --reload --port 8765
```

主要端点：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 |
| POST | `/memory/add` | 添加记忆 |
| POST | `/memory/search` | 语义搜索 |
| POST | `/memory/recall` | AI 上下文召回 |
| GET | `/memory/list` | 列出记忆 |
| DELETE | `/memory/{id}` | 删除记忆 |
| GET | `/kb/list` | 列出知识库 |
| POST | `/kb/{name}/query` | 知识库查询 |
| GET | `/stats` | 系统统计 |

### 8. Docker 部署

```bash
# 构建镜像
docker build -t semantic-memory .

# 运行（自动下载模型）
docker run -p 8765:8765 \
    -v $(pwd)/data:/app/data \
    semantic-memory

# 或使用 Docker Compose
docker compose up -d
```

API 文档：http://localhost:8765/docs

---

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                     Semantic Memory                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐ │
│  │  用户界面层   │     │  API 服务层   │     │  CLI 层      │ │
│  │              │     │              │     │              │ │
│  │ Streamlit UI │     │  FastAPI     │     │ interactive  │ │
│  │ Streamlit    │     │  REST API    │     │ CLI          │ │
│  │ Web App     │     │  /docs       │     │ shell comp.  │ │
│  └──────┬───────┘     └──────┬───────┘     └──────┬───────┘ │
│         │                    │                    │          │
│         └────────────────────┼────────────────────┘          │
│                              │                               │
│                    ┌─────────▼─────────┐                     │
│                    │  MemoryManager     │                     │
│                    │  (统一入口)         │                     │
│                    └─────────┬─────────┘                     │
│                              │                               │
│         ┌────────────────────┼────────────────────┐          │
│         │                    │                    │          │
│  ┌──────▼──────┐   ┌────────▼────────┐  ┌────────▼────────┐ │
│  │  记忆操作    │   │   检索模块       │  │   文档解析       │ │
│  │             │   │                 │  │                 │ │
│  │ add()      │   │ search()        │  │ doc_parser.py   │ │
│  │ delete()   │   │ recall()        │  │ PDF表格提取     │ │
│  │ update()   │   │ query_kb()      │  │ XLSX/PPTX      │ │
│  │ tag()      │   │ similarity()    │  │ DOCX表格      │ │
│  │ list()     │   │                 │  │                 │ │
│  └──────┬─────┘   └────────┬────────┘  └────────┬────────┘ │
│         │                   │                    │          │
│  ┌──────▼───────────────────▼────────────────────▼──────┐   │
│  │                     核心层                           │   │
│  │                                                       │   │
│  │  ┌──────────────┐  ┌────────────────┐  ┌──────────┐  │   │
│  │  │  VectorStore  │  │ ONNX Embedding │  │ Config   │  │   │
│  │  │  FAISS Index  │  │  BGE-small-zh  │  │ Logger   │  │   │
│  │  └──────────────┘  └────────────────┘  └──────────┘  │   │
│  │                                                       │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**数据流向**：

```
用户输入 ──→ MemoryManager.add() ──→ Text → ONNX Encoder ──→ 向量
                                          ↓                   ↓
                                     [chunk text]      FAISS Index
                                          ↓                   ↓
                                     JSON metadata    ID mapping
                                          ↓                   ↓
                                     memories/ ←──────────────┘
```

---

## 📁 项目文件结构

```
semantic-memory/
├── scripts/
│   ├── __init__.py          # 包入口
│   ├── core.py               # ONNX Embedding 引擎
│   ├── vector_store.py       # FAISS 向量存储
│   ├── memory_manager.py     # 记忆管理器（核心 API）
│   ├── config.py             # 配置管理
│   ├── sensitive_filter.py   # 敏感信息过滤
│   ├── logging.py            # 统一日志模块
│   ├── batch.py              # 批量操作 API
│   ├── interactive.py        # 交互式 CLI
│   ├── retry.py              # 指数退避重试装饰器
│   ├── doc_parser.py         # 多格式文档解析（PDF表格、XLSX、PPTX）
│   ├── streamlit_app.py      # Web UI（Streamlit）
│   ├── api_server.py         # FastAPI REST 服务
│   └── completion/           # Shell 自动补全
│       ├── bash_completion
│       ├── zsh_completion
│       └── fish_completion
├── tests/
│   ├── conftest.py           # pytest 配置 + fixtures
│   ├── test_core.py          # ONNX 引擎测试（待补充）
│   ├── test_vector_store.py
│   ├── test_memory_manager.py
│   ├── test_config.py
│   ├── test_sensitive_filter.py
│   └── test_batch.py
├── data/                     # 数据目录（自动创建）
│   ├── memories/             # 记忆 JSON 文件
│   ├── kb/                   # 知识库数据
│   ├── models/               # ONNX 模型缓存
│   └── logs/                 # 日志文件
├── .github/
│   └── workflows/
│       └── ci.yml            # GitHub Actions CI/CD
├── Dockerfile                # Docker 镜像构建
├── docker-compose.yml        # Docker Compose 编排
├── docker/
│   └── README.md             # Docker 部署指南
├── docs/
│   └── api_examples.md       # API 使用示例
├── requirements.txt           # Python 依赖
├── pyproject.toml            # 项目元数据 + pytest 配置
├── CONTRIBUTING.md           # 贡献指南
├── LICENSE                   # MIT License
└── README.md                 # 本文件
```

---

## ⚙️ 配置参考

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| `model_id` | `"BAAI/bge-small-zh-v1.5"` | ONNX 模型标识 |
| `device` | `"cpu"` | 运行设备（`cpu` / `cuda`） |
| `search_top_k` | `5` | 默认返回数量 |
| `search_min_score` | `0.0` | 最低相似度阈值 |
| `half_life_days` | `14.0` | 记忆半衰期（天） |
| `min_importance` | `0.2` | 低价值记忆阈值 |
| `dedup_threshold` | `0.95` | 去重相似度阈值 |
| `dedup_enabled` | `true` | 启用去重 |
| `sensitive_filter_enabled` | `true` | 启用敏感信息过滤 |
| `metrics_enabled` | `true` | 启用性能统计 |
| `chunk_max_chars` | `500` | 文本分块最大字符数 |
| `chunk_overlap` | `50` | 分块重叠字符数 |

配置文件路径：`~/.semantic_memory/config.json`（或通过 `SEMANTIC_MEMORY_DATA_DIR` 环境变量覆盖）

---

## 🧪 测试

```bash
# 运行全部测试
pytest tests/ -v

# 运行并生成覆盖率报告
pytest tests/ -v --cov=scripts --cov-report=html

# 仅运行单元测试（不含集成测试）
pytest tests/ -v -m "not integration"

# 单个测试文件
pytest tests/test_memory_manager.py -v
```

> **注意**：部分测试（如 ONNX 模型加载）需要网络连接下载模型，属于集成测试。

---

## 🔧 常见问题

**Q: 首次运行报 `FileNotFoundError: model not found`？**

首次启动会自动下载 ~100MB 的 ONNX 模型。如遇网络问题，可手动下载：
```python
from scripts.core import download_model
download_model()  # 重新下载模型
```

**Q: 如何指定模型存储位置？**

```python
import os
os.environ["SEMANTIC_MEMORY_DATA_DIR"] = "/path/to/data"
mgr = MemoryManager()  # 模型和数据将存放在此目录
```

**Q: 模型下载失败/超时？**

使用代理或手动下载：
```bash
# 设置代理
export HTTP_PROXY=http://127.0.0.1:7890
export HTTPS_PROXY=http://127.0.0.1:7890
python -c "from memory_manager import MemoryManager; MemoryManager()"
```

**Q: Docker 中 GPU 加速？**

```dockerfile
# Dockerfile.gpu（使用 onnxruntime-gpu）
FROM semantic-memory:latest
RUN pip install onnxruntime-gpu
```

```bash
docker run --gpus all -p 8765:8765 semantic-memory:gpu
```

**Q: 如何迁移数据到新机器？**

整个 `data/` 目录即数据，复制到新机器对应位置即可。FAISS 索引与模型均在首次启动时自动重建。

**Q: 记忆数量很多后搜索变慢？**

`bge-small-zh-v1.5` 模型维度 512，在 10 万条记忆内搜索性能良好。如需更大规模，可切换到 `bge-base-zh-v1.5`（维度 768）或使用 GPU。

---

## 🛠️ 扩展与定制

### 添加新的 Embedding 模型

```python
from scripts.core import ONNXEmbeddingEngine

class MyEncoder(ONNXEmbeddingEngine):
    def __init__(self):
        super().__init__(model_id="your-model-id")

mgr = MemoryManager(encoder=MyEncoder())
```

### 自定义记忆过滤器

```python
def my_filter(text: str) -> str:
    # 自定义过滤逻辑
    return text.replace("内部代号", "[已脱敏]")

from memory_manager import MemoryManager
mgr = MemoryManager(custom_filters=[my_filter])
```

### 知识库插件（文档解析器）

```python
# 在 doc_parser.py 中注册新的解析器
PARSERS[".odt"] = _parse_odt  # 添加 ODT 支持
```

---

## 📋 待完成功能

- [ ] `test_core.py` — ONNX 引擎单元测试（需要 mock ONNX Runtime）
- [ ] 通用重试机制 — API 调用和记忆操作添加 `@retry` 装饰器
- [ ] Streamlit Web UI — 完整可视化界面（进行中）
- [x] 文档截图 — ✅ README 截图已完成（见上方演示图）；视频演示待录制
- [ ] PDF 表格智能解析 — 复杂 PDF 表格结构识别
- [ ] GitHub Actions CI Token — 需要无 Token 方式配置（可用 `GITHUB_TOKEN`）

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/my-feature`
3. 提交更改：`git commit -am 'Add some feature'`
4. 推送分支：`git push origin feature/my-feature`
5. 创建 Pull Request

贡献指南详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📄 License

MIT License — 详见 [LICENSE](LICENSE) 文件。
