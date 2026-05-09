# Semantic Memory — API 使用示例

本文件展示 Semantic Memory REST API 的完整使用方法。

## 基础信息

- **Base URL**: `http://localhost:8765`
- **API Docs**: `http://localhost:8765/docs`（Swagger UI）
- **ReDoc**: `http://localhost:8765/redoc`

## 启动服务

```bash
# 启动 API 服务
python scripts/api_server.py --port 8765

# 开发模式（热重载）
python scripts/api_server.py --port 8765 --reload --log-level debug
```

## cURL 示例

### 健康检查

```bash
curl http://localhost:8765/health
# {"status": "ok", "service": "semantic-memory"}
```

### 添加记忆

```bash
# 基础添加
curl -X POST http://localhost:8765/memories \
  -H "Content-Type: application/json" \
  -d '{"text": "今天和张三讨论了AI项目进展，计划下周发布v1版本", "tags": ["工作", "AI"], "importance": 0.8}'

# 跳过敏感过滤（管理员）
curl -X POST http://localhost:8765/memories \
  -H "Content-Type: application/json" \
  -d '{"text": "some content", "skip_filter": true}'
```

### 语义搜索

```bash
# 搜索记忆
curl "http://localhost:8765/search?q=AI项目&top_k=5"

# 按标签搜索
curl "http://localhost:8765/search?q=项目进展&tag=工作&top_k=3"
```

### 召回并格式化为上下文

```bash
# 语义召回，最大 2000 字符
curl "http://localhost:8765/recall?q=项目进展如何&max_chars=2000"
```

### 列出记忆

```bash
# 列出最近 20 条
curl "http://localhost:8765/memories?limit=20"

# 按标签过滤
curl "http://localhost:8765/memories?tag=工作&limit=50"

# 按重要性排序
curl "http://localhost:8765/memories?sort=importance&limit=20"
```

### 记忆操作

```bash
# 获取单条记忆
curl http://localhost:8765/memories/{memory_id}

# 编辑记忆
curl -X PATCH http://localhost:8765/memories/{memory_id}/text \
  -H "Content-Type: application/json" \
  -d '{"text": "更新后的内容"}'

# 添加标签
curl -X PATCH http://localhost:8765/memories/{memory_id}/tags \
  -H "Content-Type: application/json" \
  -d '{"tags": ["重要", "已审核"]}'

# 设置重要性
curl -X PATCH http://localhost:8765/memories/{memory_id}/importance \
  -H "Content-Type: application/json" \
  -d '{"importance": 0.95}'

# 删除记忆
curl -X DELETE http://localhost:8765/memories/{memory_id}
```

### 知识库操作

```bash
# 创建知识库
curl -X POST http://localhost:8765/kb \
  -H "Content-Type: application/json" \
  -d '{"name": "项目文档", "description": "AI项目相关文档"}'

# 列出知识库
curl http://localhost:8765/kb

# 向知识库添加文档
curl -X POST http://localhost:8765/kb/项目文档/documents \
  -H "Content-Type: application/json" \
  -d '{"text": "项目计划：v1.0版本将于下周发布。", "tags": ["计划"]}'

# 查询知识库
curl -X POST http://localhost:8765/kb/项目文档/query \
  -H "Content-Type: application/json" \
  -d '{"question": "v1.0什么时候发布", "top_k": 5}'

# 删除知识库
curl -X DELETE http://localhost:8765/kb/项目文档
```

### 统计与维护

```bash
# 统计信息
curl http://localhost:8765/stats

# 性能指标
curl http://localhost:8765/metrics

# 预览遗忘（不实际删除）
curl -X POST http://localhost:8765/forget

# 执行遗忘（实际删除）
curl -X POST http://localhost:8765/forget \
  -H "Content-Type: application/json" \
  -d '{"apply": true}'
```

### 配置管理

```bash
# 查看全部配置
curl http://localhost:8765/config

# 查看单个配置
curl "http://localhost:8765/config?key=search_top_k"

# 设置配置
curl -X POST http://localhost:8765/config \
  -H "Content-Type: application/json" \
  -d '{"key": "search_top_k", "value": "10"}'

# 设置布尔值
curl -X POST http://localhost:8765/config \
  -H "Content-Type: application/json" \
  -d '{"key": "dedup_enabled", "value": "true"}'
```

## Python SDK 示例（requests 库）

```python
import requests

BASE = "http://localhost:8765"


def add_memory(text, tags=None, importance=0.5):
    """添加记忆"""
    resp = requests.post(f"{BASE}/memories", json={
        "text": text,
        "tags": tags or [],
        "importance": importance,
    })
    resp.raise_for_status()
    return resp.json()


def search_memories(query, top_k=5, tag=None):
    """语义搜索"""
    params = {"q": query, "top_k": top_k}
    if tag:
        params["tag"] = tag
    resp = requests.get(f"{BASE}/search", params=params)
    resp.raise_for_status()
    return resp.json()


def build_context(query, max_chars=3000):
    """语义召回，构建上下文"""
    resp = requests.get(f"{BASE}/recall", params={
        "q": query,
        "max_chars": max_chars,
    })
    resp.raise_for_status()
    return resp.json()


# 使用示例
if __name__ == "__main__":
    # 添加记忆
    result = add_memory(
        "今天讨论了项目进展，计划下周发布v1版本",
        tags=["工作", "AI"],
        importance=0.8,
    )
    print(f"Added: {result}")

    # 搜索
    results = search_memories("项目进展", top_k=3)
    for r in results["results"]:
        print(f"  [{r['id']}] {r['text'][:80]}...")

    # 构建上下文
    ctx = build_context("项目进展如何")
    print(f"\n上下文（{ctx['count']}条记忆，{ctx['total_chars']}字）:\n{ctx['context']}")
```

## JavaScript/Node.js 示例

```javascript
const BASE = "http://localhost:8765";

async function api(endpoint, options = {}) {
  const url = new URL(endpoint, BASE);
  const resp = await fetch(url.toString(), {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!resp.ok) throw new Error(`API Error: ${resp.status}`);
  return resp.json();
}

async function main() {
  // 搜索记忆
  const results = await api(`/search?q=项目进展&top_k=5`);
  results.results.forEach(r => {
    console.log(`[${r.id}] ${r.text.slice(0, 80)}...`);
  });

  // 召回上下文
  const ctx = await api(`/recall?q=项目进展如何&max_chars=2000`);
  console.log(ctx.context);
}

main().catch(console.error);
```

## 在 OpenClaw Agent 中调用

```python
# 在 OpenClaw skill 的脚本中使用
import requests

MEMORY_API = "http://localhost:8765"

def remember_context(query, max_chars=5000):
    """在 agent 中获取相关记忆作为上下文"""
    resp = requests.get(
        f"{MEMORY_API}/recall",
        params={"q": query, "max_chars": max_chars},
        timeout=5,
    )
    if resp.status_code == 200:
        data = resp.json()
        if data["context"]:
            return f"\n[相关记忆]\n{data['context']}\n[/相关记忆]\n"
    return ""
```

## 错误码

| HTTP 状态码 | 含义 |
|---|---|
| 200 | 成功 |
| 400 | 请求格式错误 |
| 404 | 资源不存在（记忆/知识库 ID 错误） |
| 422 | 记忆被过滤（包含敏感信息） |
| 500 | 服务器内部错误 |
