# Semantic Memory — 技术架构

## 概览

Semantic Memory 采用模块化设计，各模块职责单一，通过标准 Python API 互相调用。

```
┌─────────────────────────────────────────────────────────┐
│                    CLI / API / Hook                      │
├─────────────────────────────────────────────────────────┤
│                   memory_manager.py                      │
│  (Facade: 记忆 CRUD + 知识库 + 加密 + 统计)             │
├──────────────────┬──────────────────┬───────────────────┤
│    core.py       │  vector_store.py │ sensitive_filter  │
│  ONNX Embedding  │  FAISS Vector DB │  doc_parser.py   │
│  < 50ms CPU      │  Auto IVF Index  │  PDF/DOCX/TXT    │
├──────────────────┴──────────────────┴───────────────────┤
│                   config.py                              │
│             JSON 配置 + 差量保存                         │
└─────────────────────────────────────────────────────────┘
         ↓ ONNX Model (~46MB)
     HuggingFace Hub / hf-mirror.com
```

## 模块说明

### 1. core.py — ONNX Embedding 引擎

**职责**: 加载 ONNX 量化模型，将文本编码为 384 维向量

**核心接口**:
```python
encode(texts: list[str]) -> np.ndarray  # shape: (N, 384), float32
model_id: str                               # 当前模型 ID
dimension: int                               # 向量维度
```

**模型支持**:
- `all-MiniLM-L6-v2` (384d, ~46MB) — 默认，英文通用
- `bge-small-zh-v1.5` (512d, ~70MB) — 中文优化

**自动下载**: 首次使用时自动从 HuggingFace 下载，失败时自动切换 hf-mirror.com 国内镜像

**性能**: Intel i5 上 ~30-50ms/次（批量越大越快）

### 2. vector_store.py — FAISS 向量存储

**职责**: 管理 FAISS 索引（`IndexFlatL2` → `IndexIVFFlat` 自动升级）

**核心接口**:
```python
add(id: str, vec: np.ndarray, meta: dict)
search(query_vec: np.ndarray, top_k: int, filter_fn=None) -> list
update(id: str, vec: np.ndarray, meta: dict)
delete(id: str) -> bool
clear()
save()   # 持久化到磁盘
count   # 当前索引大小
```

**索引策略**:
- < 500 条：`IndexFlatL2`（线性扫描，精度 100%）
- ≥ 500 条：自动升级为 `IndexIVFFlat`（IVF×16×sqrt(N)，加速 10-50×）

**文件格式**:
- `index.faiss` — FAISS 二进制索引
- `meta.jsonl` — 每行一条记忆元数据

### 3. memory_manager.py — 业务逻辑层

**职责**: 组合 core + vector_store + sensitive_filter，提供完整的记忆管理 API

**核心概念**:

| 概念 | 说明 |
|------|------|
| Memory | 单条记忆，含 text, tags, importance, timestamp |
| KB (Knowledge Base) | 独立向量空间，用于文档知识库 |
| Chunk | 大文本分块后的片段（≤512字符） |
| Effective Importance | importance × 衰减系数（时间衰减） |

**重要性衰减公式**:
```
effective_importance = importance × 0.5^(days_elapsed / half_life_days)
```

**去重逻辑**:
- 使用余弦相似度与现有记忆比较
- 相似度 ≥ dedup_threshold（默认 0.95）→ 标记为 dedup，更新原记忆时间戳

**敏感过滤**:
- 启用时（默认），先调用 `sensitive_filter.sanitize()` 再存入
- 纯敏感内容（如纯 API Key）拒绝存储，返回 `filtered:`

### 4. sensitive_filter.py — 脱敏引擎

**职责**: 检测并脱敏敏感信息

**检测类型**:
- API Keys: `sk-*`, `AKIA*`, Bearer Token
- 密码: `password=`, `密码是`
- 身份证号、手机号、银行卡号
- 私钥: `-----BEGIN RSA PRIVATE KEY-----`
- JWT Token

**脱敏策略**: 检测到敏感信息 → 替换为 `[REDACTED_<TYPE>]`

### 5. doc_parser.py — 文档解析

**支持格式**:
- `.txt`, `.md` — 纯文本
- `.pdf` — PDFMiner
- `.docx` — python-docx

**分块策略**:
1. 按段落分割（`\n\n`）
2. 段落 > 512字符 → 按句子分割
3. 句子仍 > 512字符 → 硬截断 + 50字符重叠

### 6. config.py — 配置管理

**持久化策略**: 只保存与默认值的差异（差量保存）

**默认配置**:
```json
{
  "model_id": "all-MiniLM-L6-v2",
  "chunk_max_chars": 512,
  "chunk_overlap": 64,
  "search_top_k": 5,
  "search_min_score": 0.2,
  "half_life_days": 30,
  "min_importance": 0.1,
  "dedup_enabled": true,
  "dedup_threshold": 0.95,
  "sensitive_filter_enabled": true,
  "metrics_enabled": true
}
```

## 数据目录结构

```
~/.qclaw/data/semantic-memory/
├── config.json              # 用户配置（差量）
├── memories/                # 记忆向量库
│   ├── index.faiss
│   └── meta.jsonl
├── kb/                      # 知识库目录
│   ├── {kb_name}/
│   │   ├── index.faiss
│   │   └── meta.jsonl
│   └── ...
└── logs/
    └── semantic-memory.log   # 日志文件（轮转，5MB/个，保留3份）
```

## 安全说明

- **无网络依赖**: 全部在本地运行，模型文件也本地缓存
- **可选加密**: Fernet (AES-256-CBC) 加密 `memories/` 目录，密钥由密码 PBKDF2 派生
- **敏感信息过滤**: 默认启用，防止 API Key 等敏感内容被存储
