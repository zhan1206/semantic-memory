#!/usr/bin/env python3
"""
Semantic Memory — FastAPI REST API 服务
提供 HTTP 接口访问语义记忆系统
启动: python api_server.py [--host 0.0.0.0] [--port 8765] [--reload]
"""
import os
import sys
import argparse
import logging
from typing import Optional

# ─── 路径设置 ──────────────────────────────────────────────
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SKILL_DIR)

# 延迟导入（让 core.py 的模型下载逻辑能正确工作）
from memory_manager import MemoryManager
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

# ─── 日志 ──────────────────────────────────────────────────
logger = logging.getLogger("api_server")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(sys.stderr)
handler.setFormatter(logging.Formatter("[api] %(levelname)s %(message)s"))
logger.addHandler(handler)

# ─── 全局 Manager ──────────────────────────────────────────
_manager: Optional[MemoryManager] = None


def get_manager() -> MemoryManager:
    global _manager
    if _manager is None:
        _manager = MemoryManager()
    return _manager


# ─── FastAPI App ───────────────────────────────────────────
app = FastAPI(
    title="Semantic Memory API",
    description="OpenClaw 本地语义记忆与检索系统 — REST API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS：允许前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Request / Response 模型 ────────────────────────────────
class AddMemoryRequest(BaseModel):
    text: str = Field(..., min_length=1, description="记忆文本内容")
    tags: list[str] = Field(default_factory=list, description="标签列表")
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="重要性 0.0-1.0")
    source: str = Field(default="api", description="来源标记")
    skip_filter: bool = Field(default=False, description="跳过敏感信息过滤")


class EditMemoryRequest(BaseModel):
    text: str = Field(..., min_length=1)


class TagMemoryRequest(BaseModel):
    tags: list[str] = Field(..., min_length=1)


class SetImportanceRequest(BaseModel):
    importance: float = Field(..., ge=0.0, le=1.0)


class AddToKBRequest(BaseModel):
    text: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    source_file: Optional[str] = None


class QueryKBRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)


class ConfigSetRequest(BaseModel):
    key: str
    value: str


# ─── 健康检查 ──────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "service": "semantic-memory"}


# ─── 记忆 CRUD ─────────────────────────────────────────────
@app.post("/memories", response_model=dict)
async def add_memory(req: AddMemoryRequest):
    """添加一条记忆"""
    mgr = get_manager()
    try:
        result = mgr.add(
            text=req.text,
            tags=req.tags,
            importance=req.importance,
            source=req.source,
            skip_filter=req.skip_filter,
        )
        if result.startswith("filtered:"):
            raise HTTPException(status_code=422, detail=f"记忆被过滤: {result}")
        if result.startswith("dedup:"):
            return {"status": "deduplicated", "memory_id": result.split(":", 1)[1]}
        return {"status": "added", "memory_id": result}
    except Exception as e:
        logger.error(f"add_memory failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories", response_model=list)
async def list_memories(
    tag: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500),
    sort: str = Query(default="timestamp", pattern="^(timestamp|importance)$"),
):
    """列出记忆"""
    mgr = get_manager()
    try:
        return mgr.list_memories(tag=tag, limit=limit, sort_by=sort)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memories/{memory_id}", response_model=dict)
async def get_memory(memory_id: str):
    """获取单条记忆"""
    mgr = get_manager()
    result = mgr.get(memory_id)
    if result is None:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return result


@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    """删除记忆"""
    mgr = get_manager()
    ok = mgr.delete(memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"status": "deleted", "memory_id": memory_id}


@app.patch("/memories/{memory_id}/text", response_model=dict)
async def edit_memory(memory_id: str, req: EditMemoryRequest):
    """编辑记忆内容"""
    mgr = get_manager()
    ok = mgr.edit(memory_id, req.text)
    if not ok:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"status": "updated", "memory_id": memory_id}


@app.patch("/memories/{memory_id}/tags", response_model=dict)
async def tag_memory(memory_id: str, req: TagMemoryRequest):
    """添加标签"""
    mgr = get_manager()
    ok = mgr.tag(memory_id, req.tags)
    if not ok:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"status": "tagged", "memory_id": memory_id, "tags": req.tags}


@app.patch("/memories/{memory_id}/importance", response_model=dict)
async def set_importance(memory_id: str, req: SetImportanceRequest):
    """设置重要性"""
    mgr = get_manager()
    ok = mgr.set_importance(memory_id, req.importance)
    if not ok:
        raise HTTPException(status_code=404, detail="记忆不存在")
    return {"status": "updated", "memory_id": memory_id}


# ─── 语义搜索 ──────────────────────────────────────────────
@app.get("/search", response_model=dict)
async def search(
    q: str = Query(..., min_length=1, description="查询文本"),
    top_k: int = Query(default=5, ge=1, le=50),
    tag: Optional[str] = None,
    kb: Optional[str] = None,
    min_score: Optional[float] = Query(default=None, ge=0.0, le=1.0),
):
    """语义搜索记忆"""
    mgr = get_manager()
    try:
        results = mgr.search(
            query=q,
            top_k=top_k,
            tag=tag,
            kb_name=kb,
            min_score=min_score or None,
        )
        return {"query": q, "results": results, "count": len(results)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/recall", response_model=dict)
async def recall(
    q: str = Query(..., min_length=1),
    top_k: int = Query(default=5, ge=1, le=20),
    tag: Optional[str] = None,
    kb: Optional[str] = None,
    max_chars: int = Query(default=3000, ge=100, le=50000),
):
    """语义召回，格式化为上下文文本"""
    mgr = get_manager()
    results = mgr.search(query=q, top_k=top_k, tag=tag, kb_name=kb)

    # 组装上下文
    context_parts = []
    total_chars = 0
    truncated = False

    for r in results:
        text = r["text"]
        if total_chars + len(text) + 1 > max_chars:
            truncated = True
            break
        context_parts.append(f"[记忆 {r['id']}] {text}")
        total_chars += len(text) + 1

    context = "\n\n".join(context_parts)
    return {
        "query": q,
        "context": context,
        "count": len(context_parts),
        "truncated": truncated,
        "total_chars": total_chars,
        "results": results,
    }


# ─── 知识库 ────────────────────────────────────────────────
@app.post("/kb", response_model=dict)
async def create_kb(name: str = Body(...), description: str = Body("")):
    """创建知识库"""
    mgr = get_manager()
    result = mgr.create_kb(name, description=description)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.get("/kb", response_model=list)
async def list_kbs():
    """列出知识库"""
    mgr = get_manager()
    return mgr.list_kbs()


@app.delete("/kb/{kb_name}")
async def delete_kb(kb_name: str):
    """删除知识库"""
    mgr = get_manager()
    result = mgr.delete_kb(kb_name)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@app.post("/kb/{kb_name}/documents", response_model=dict)
async def add_to_kb(kb_name: str, req: AddToKBRequest):
    """向知识库添加文档"""
    mgr = get_manager()
    result = mgr.add_to_kb(kb_name, req.text, source_file=req.source_file, tags=req.tags)
    return result


@app.post("/kb/{kb_name}/query", response_model=dict)
async def query_kb(kb_name: str, req: QueryKBRequest):
    """在知识库中检索"""
    mgr = get_manager()
    results = mgr.query_kb(kb_name, req.question, top_k=req.top_k)
    return {"question": req.question, "results": results, "count": len(results)}


# ─── 统计与维护 ─────────────────────────────────────────────
@app.get("/stats", response_model=dict)
async def stats():
    """获取统计信息"""
    mgr = get_manager()
    return mgr.stats()


@app.get("/metrics", response_model=dict)
async def metrics():
    """获取性能指标"""
    mgr = get_manager()
    return mgr.stats().get("metrics", {})


@app.post("/forget", response_model=dict)
async def forget(apply: bool = Body(default=False)):
    """自动遗忘低价值记忆"""
    mgr = get_manager()
    results = mgr.auto_forget(dry_run=not apply)
    return {"mode": "apply" if apply else "dry_run", "count": len(results), "items": results[:20]}


# ─── 配置 ───────────────────────────────────────────────────
@app.get("/config", response_model=dict)
async def get_config(key: Optional[str] = None):
    """获取配置"""
    from config import load_config, get_config as cfg_get
    if key:
        val = cfg_get(key)
        return {"key": key, "value": val}
    return load_config()


@app.post("/config", response_model=dict)
async def set_config(req: ConfigSetRequest):
    """设置配置"""
    import json
    from config import set_config as cfg_set
    try:
        value = json.loads(req.value)
    except (json.JSONDecodeError, ValueError):
        value = req.value
    result = cfg_set(req.key, value)
    return {"status": "updated", "key": req.key, "value": result.get(req.key)}


# ─── 错误处理 ───────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


# ─── 启动入口 ───────────────────────────────────────────────
def run():
    parser = argparse.ArgumentParser(description="Semantic Memory API Server")
    parser.add_argument("--host", default="127.0.0.1", help="绑定地址")
    parser.add_argument("--port", type=int, default=8765, help="端口")
    parser.add_argument("--reload", action="store_true", help="开发模式热重载")
    parser.add_argument("--log-level", default="info",
                        choices=["debug", "info", "warning", "error"])
    args = parser.parse_args()

    level_map = {"debug": "debug", "info": "info", "warning": "warning", "error": "error"}
    log_level = getattr(logging, level_map[args.log_level].upper())

    logger.info(f"Starting Semantic Memory API Server on {args.host}:{args.port}")
    logger.info(f"API docs: http://{args.host}:{args.port}/docs")

    uvicorn.run(
        "api_server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level=args.log_level,
    )


if __name__ == "__main__":
    run()
