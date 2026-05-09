# 🤝 贡献指南

感谢您对 Semantic Memory 的关注与贡献！

## 开发环境设置

```bash
# 1. 克隆仓库
git clone https://github.com/zhan1206/semantic-memory.git
cd semantic-memory

# 2. 创建虚拟环境
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
.venv\Scripts\activate          # Windows

# 3. 安装依赖
pip install -e ".[dev,docs]"

# 4. 运行测试（验证环境）
pytest tests/ -v --tb=short
```

## 代码规范

### Python 风格

遵循 **PEP 8**，使用 **Black** 格式化：

```bash
# 安装格式工具
pip install black isort flake8

# 格式化代码
black scripts/ tests/

# 导入排序
isort scripts/ tests/

# 代码检查
flake8 scripts/ tests/ --max-line-length=100 --ignore=E501,W503
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 模块/文件 | 小写下划线 | `doc_parser.py` |
| 类 | 大驼峰 | `MemoryManager` |
| 函数/方法 | 小写下划线 | `batch_add_memories` |
| 常量 | 大写下划线 | `MAX_CHUNK_SIZE` |
| 类型变量 | 大驼峰 | `T = TypeVar("T")` |

### 文档字符串

所有公开函数/类需有文档字符串：

```python
def search(
    query: str,
    top_k: int = 5,
    tag: str = None,
) -> list[dict]:
    """
    语义搜索记忆

    Args:
        query: 自然语言查询
        top_k: 返回结果数量
        tag: 标签过滤（可选）

    Returns:
        匹配的记忆列表，每项含 id/text/score/tags/importance

    Raises:
        ValueError: query 为空时抛出

    Example:
        >>> mgr = MemoryManager()
        >>> results = mgr.search("张三说了什么", top_k=3)
        >>> print(results[0]["text"])
    """
    ...
```

## 测试规范

### 测试结构

```python
# tests/test_memory_manager.py
import pytest
from scripts.memory_manager import MemoryManager


class TestMemoryAdd:
    """MemoryManager.add() 的测试"""

    def test_add_basic(self, clean_data_dir):
        """基本添加功能"""
        mgr = MemoryManager(data_dir=clean_data_dir)
        mem_id = mgr.add("测试记忆", importance=0.5)
        assert mem_id is not None
        assert len(mem_id) > 0

    def test_add_empty_text_raises(self, clean_data_dir):
        """空文本应抛出 ValueError"""
        mgr = MemoryManager(data_dir=clean_data_dir)
        with pytest.raises(ValueError, match="empty"):
            mgr.add("")

    def test_add_with_tags(self, clean_data_dir):
        """带标签添加"""
        mgr = MemoryManager(data_dir=clean_data_dir)
        mem_id = mgr.add("工作内容", tags=["工作", "重要"])
        assert mem_id is not None
```

### Fixtures 说明

`conftest.py` 提供以下 fixtures：

| Fixture | 说明 |
|---------|------|
| `mock_data_dir` | Session 级临时目录（所有测试共享） |
| `clean_data_dir` | 函数级干净临时目录 |
| `patch_data_dir` | 自动将 DATA_DIR 指向测试目录 |
| `sample_texts` | 标准测试文本集（中文/英文/模拟敏感信息） |
| `mock_encoder` | 确定性 Mock 向量引擎（维度 384） |

### Mock Encoder 使用

```python
def test_search_with_mock(memory_manager, mock_encoder):
    """使用 Mock 引擎测试搜索"""
    mgr = memory_manager
    mgr._encoder = mock_encoder  # 替换为 Mock
    mgr.add("测试文本")
    results = mgr.search("测试", top_k=1)
    assert len(results) == 1
```

## Git 提交规范

采用 [Conventional Commits](https://www.conventionalcommits.org/)：

```
<type>(<scope>): <subject>

[optional body]

[optional footer]
```

类型：

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(kb): add XLSX parsing support` |
| `fix` | Bug 修复 | `fix(search): correct score calculation` |
| `docs` | 文档 | `docs: update README installation` |
| `test` | 测试 | `test(batch): add batch import tests` |
| `refactor` | 重构 | `refactor(core): extract encoder class` |
| `perf` | 性能 | `perf(vector): use batch encode` |
| `chore` | 维护 | `chore: bump pytest version` |

示例：

```bash
git commit -m "feat(doc_parser): add PDF table extraction

- Detect table-like structures from PDF text
- Convert to Markdown table format
- Handle merged cells in DOCX tables

Closes #12"
```

## Pull Request 流程

1. **Fork** 并创建特性分支
   ```bash
   git checkout -b feature/pdf-table-extraction
   ```

2. **编写代码 + 测试**

3. **确保测试通过**
   ```bash
   pytest tests/ -v --tb=short
   ```

4. **提交并推送**
   ```bash
   git push origin feature/pdf-table-extraction
   ```

5. **创建 Pull Request**，描述：
   - 改动内容
   - 解决的问题
   - 测试方式
   - 截图/截图（如有 UI 改动）

## 分支管理

- `main` — 稳定版本，始终可部署
- `feature/xxx` — 功能开发分支
- `fix/xxx` — Bug 修复分支
- `docs/xxx` — 文档更新分支

## 问题反馈

提交 Issue 时，请包含：

- **环境信息**：Python 版本、操作系统、Docker 版本（如适用）
- **复现步骤**：最小可复现代码
- **期望行为 vs 实际行为**
- **完整错误信息**（含 Traceback）

## 代码审查要点

Reviewers 关注：

- [ ] 功能正确性
- [ ] 测试覆盖率（新增代码有对应测试）
- [ ] 文档完整性（README / docstring）
- [ ] 性能影响（大规模数据测试）
- [ ] 安全影响（敏感信息处理）
- [ ] 向后兼容性（不破坏现有 API）

---

**一起让 Semantic Memory 变得更好！** 🚀
