# Semantic Memory — CLI 命令参考

## 基础命令

### `add` — 添加记忆

```bash
python scripts/run.py add "记忆内容" [--tags 标签1,标签2] [--importance 0.8]
```

**示例**:
```bash
python scripts/run.py add "今天讨论了项目进展" --tags "工作,AI" --importance 0.8
```

**参数**:
| 参数 | 说明 |
|------|------|
| `text` | 记忆内容（必填） |
| `--tags` | 标签，逗号分隔（可选） |
| `--importance` | 重要性 0.0-1.0（默认 0.5） |

---

### `search` — 语义搜索

```bash
python scripts/run.py search <查询文本> [--top-k 5] [--tag 标签] [--kb 知识库名]
```

**示例**:
```bash
# 搜索相关记忆
python scripts/run.py search "项目进展"

# 限制结果数
python scripts/run.py search "张三" --top-k 3

# 在指定知识库搜索
python scripts/run.py search "Python教程" --kb "学习资料"
```

**返回字段**:
```json
{
  "results": [
    {
      "id": "mem_abc123",
      "text": "记忆内容",
      "tags": ["工作"],
      "importance": 0.8,
      "effective_importance": 0.75,
      "score": 0.8923,
      "timestamp": "2026-05-09T12:00:00"
    }
  ],
  "count": 3
}
```

---

### `recall` — 语义召回（上下文构建）

```bash
python scripts/run.py recall <查询文本> [--top-k 5] [--max-chars 3000] [--tag 标签] [--kb 知识库名]
```

**示例**:
```bash
# 召回相关记忆，格式化为上下文
python scripts/run.py recall "项目进展如何" --max-chars 2000

# 输出格式
# [1] (importance:0.80, tags:工作) 今天讨论了项目进展...
# [2] (importance:0.65, tags:AI) 继续完善AI模型...
```

**适用场景**: 将召回结果直接注入 Agent 对话上下文

---

### `list` — 列出记忆

```bash
python scripts/run.py list [--tag 标签] [--limit 50] [--sort timestamp|importance]
```

**示例**:
```bash
# 最近 20 条
python scripts/run.py list --limit 20

# 按重要性排序
python scripts/run.py list --sort importance --limit 10

# 筛选标签
python scripts/run.py list --tag "工作"
```

---

### `get` — 获取单条记忆

```bash
python scripts/run.py get <记忆ID>
```

---

### `tag` — 添加标签

```bash
python scripts/run.py tag <记忆ID> <标签1,标签2>
```

---

### `importance` — 设置重要性

```bash
python scripts/run.py importance <记忆ID> <0.0-1.0>
```

---

### `edit` — 编辑内容

```bash
python scripts/run.py edit <记忆ID> <新内容>
```

---

### `delete` — 删除记忆

```bash
python scripts/run.py delete <记忆ID>
```

---

## 知识库命令

### `kb create` — 创建知识库

```bash
python scripts/run.py kb create <名称> [--desc 描述]
```

### `kb list` — 列出知识库

```bash
python scripts/run.py kb list
```

### `kb add` — 添加文档

```bash
python scripts/run.py kb add <知识库名> <文件路径> [--tags 标签]
```

**支持格式**: `.txt`, `.md`, `.pdf`, `.docx`

### `kb query` — 查询知识库

```bash
python scripts/run.py kb query <知识库名> <问题> [--top-k 5]
```

### `kb delete` — 删除知识库

```bash
python scripts/run.py kb delete <知识库名>
```

---

## 导入命令

### `import` — 导入单个文件

```bash
python scripts/run.py import <文件路径> --kb <知识库名> [--tags 标签]
```

### `import-dir` — 批量导入目录

```bash
python scripts/run.py import-dir <目录路径> --kb <知识库名> [--tags 标签]
```

---

## 配置命令

### `config get` — 查看配置

```bash
python scripts/run.py config get [key]
```

### `config set` — 设置配置

```bash
python scripts/run.py config set <key> <value>
```

**示例**:
```bash
# 修改搜索结果数
python scripts/run.py config set search_top_k 10

# 切换中文模型
python scripts/run.py config set model_id bge-small-zh-v1.5

# 关闭敏感信息过滤
python scripts/run.py config set sensitive_filter_enabled false
```

### `config reset` — 重置配置

```bash
python scripts/run.py config reset
```

---

## 维护命令

### `stats` — 统计信息

```bash
python scripts/run.py stats
```

### `forget` — 自动遗忘

```bash
# 预览（不实际删除）
python scripts/run.py forget

# 实际执行遗忘
python scripts/run.py forget --apply
```

### `clear` — 清空记忆

```bash
python scripts/run.py clear --confirm
```

### `encrypt` / `unlock` — 加密管理

```bash
python scripts/run.py encrypt <密码>
python scripts/run.py unlock <密码>
```

### `metrics` — 性能指标

```bash
python scripts/run.py metrics
```

---

## 特殊模式

### 交互模式

```bash
python scripts/run.py --interactive
# 或
python scripts/run.py -i
```

提供菜单式交互界面，适合不熟悉命令行的用户。

### API 服务模式

```bash
# 启动 REST API
python scripts/api_server.py --port 8765

# 开发模式（热重载）
python scripts/api_server.py --port 8765 --reload --log-level debug
```

API 文档: `http://localhost:8765/docs`

---

## 快速参考表

| 操作 | 命令 |
|------|------|
| 添加记忆 | `run.py add "内容" --tags "标签" --importance 0.8` |
| 语义搜索 | `run.py search "查询"` |
| 语义召回 | `run.py recall "查询" --max-chars 3000` |
| 列出记忆 | `run.py list --limit 20 --sort importance` |
| 查看统计 | `run.py stats` |
| 创建知识库 | `run.py kb create 我的知识库` |
| 导入文件 | `run.py import doc.pdf --kb 我的知识库` |
| 修改配置 | `run.py config set search_top_k 10` |
| 交互模式 | `run.py -i` |
| 启动 API | `python api_server.py --port 8765` |
