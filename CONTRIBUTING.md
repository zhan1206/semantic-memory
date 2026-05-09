# Contributing to Semantic Memory

感谢您对 Semantic Memory 项目的兴趣！欢迎提交 Issue 和 Pull Request。

## 开发环境

### 1. 克隆项目

```bash
git clone https://github.com/zhan1206/semantic-memory.git
cd semantic-memory
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# 或
.venv\Scripts\Activate.ps1       # Windows PowerShell
```

### 3. 安装依赖

```bash
# 开发依赖（包含测试、FastAPI、文档解析等全部可选功能）
pip install -e ".[all]"

# 仅核心功能
pip install -r requirements.txt
```

### 4. 运行测试

```bash
# 全部测试
pytest tests/ -v

# 带覆盖率
pytest tests/ -v --cov=scripts --cov-report=html --cov-report=term

# 单个测试文件
pytest tests/test_memory_manager.py -v

# 仅快速测试（跳过向量检索等耗时测试）
pytest tests/ -v -m "not slow"
```

## 项目结构

```
scripts/
├── core.py           # ONNX 引擎 — 修改此处需同步更新 tests/test_core.py
├── vector_store.py   # FAISS 存储 — 修改此处需同步更新 tests/test_vector_store.py
├── memory_manager.py # 业务逻辑 — 修改此处需同步更新 tests/test_memory_manager.py
├── sensitive_filter.py# 脱敏规则 — 修改此处需同步更新 tests/test_sensitive_filter.py
├── doc_parser.py     # 文档解析 — 修改此处需同步更新 tests/test_doc_parser.py
├── config.py         # 配置管理 — 修改此处需同步更新 tests/test_config.py
├── run.py            # CLI 入口
├── api_server.py     # FastAPI 服务
└── logging.py        # 日志模块
```

## 代码规范

### Python

- 遵循 **PEP 8**，行长度 ≤ 88 字符（Black 默认）
- 所有新模块需包含 docstring
- 公开 API 需写 type hints
- 中文注释优先（项目文档），英文注释次之（复杂逻辑说明）

### 测试规范

- 所有 `scripts/` 模块应有对应 `tests/test_<module>.py`
- 测试使用 pytest fixture 管理临时数据目录
- Mock ONNX 模型避免测试依赖真实模型文件
- 测试文件名: `test_<module_name>.py`
- 测试函数名: `test_<method>_<scenario>`

### 提交规范

提交信息格式（参考 [Conventional Commits](https://www.conventionalcommits.org/)）:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

类型:
- `feat`: 新功能
- `fix`: 错误修复
- `docs`: 文档更新
- `test`: 测试相关
- `refactor`: 重构
- `perf`: 性能优化
- `chore`: 构建/工具变更

示例:
```
feat(memory_manager): add batch_add for bulk memory insertion

Closes #12
```

## 新功能流程

1. **讨论**: 先开 Issue 描述需求，获得认可后再实现
2. **分支**: 从 `main` 创建功能分支 `feature/xxx` 或 `fix/xxx`
3. **测试**: 新功能必须有对应测试，覆盖率不下降
4. **文档**: 更新 README.md、references/、SKILL.md（如有必要）
5. **PR**: 描述清楚改动内容、原因、测试结果

## API 开发

### FastAPI 服务开发

```bash
# 开发模式（热重载）
python scripts/api_server.py --reload --log-level debug

# 测试 API
curl http://localhost:8765/health
curl http://localhost:8765/docs  # Swagger UI
```

### API 变更

- 所有新端点需在 `api_server.py` 中有对应 Pydantic 模型
- 变更 API 需更新 API 版本（如 `/v1/...`）
- 破坏性变更需递增主版本号

## 发布流程

1. 更新 `pyproject.toml` 中的版本号
2. 更新 `CHANGELOG.md`
3. 创建 GitHub Release
4. GitHub Actions 自动发布到 PyPI（如配置了）

## 问题排查

### 模型下载失败

```bash
# 手动下载
python -c "
from scripts.core import _ensure_model
_ensure_model('all-MiniLM-L6-v2')
"

# 使用国内镜像
export HF_ENDPOINT=https://hf-mirror.com
python scripts/run.py search test
```

### FAISS 索引损坏

```bash
# 备份旧索引，重建
cp ~/.qclaw/data/semantic-memory/memories/index.faiss ~/index.faiss.bak
python scripts/run.py clear --confirm
# 重新导入
```

### 内存不足

```bash
# 减少 IVF nprobe（加速但降低精度）
python scripts/run.py config set search_top_k 3
```

## 联系方式

- GitHub Issues: https://github.com/zhan1206/semantic-memory/issues
- 欢迎提交 PR，默认合并策略为 squash merge
