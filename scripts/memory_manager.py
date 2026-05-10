#!/usr/bin/env python3
"""
from __future__ import annotations
Semantic Memory — 记忆管理器
长期记忆 CRUD + 重要性/时间衰减 + 跨会话知识库 + 去重 + 性能监控
"""
import os
import sys
import json
import time
import uuid
import re
from datetime import datetime, timezone

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_QCLAW_BASE = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))
DATA_DIR = os.path.join(
    os.environ.get("QCLAW_DATA", os.path.join(_QCLAW_BASE, "data")),
    "semantic-memory",
)
MEMORY_DIR = os.path.join(DATA_DIR, "memories")
KB_DIR = os.path.join(DATA_DIR, "kb")

os.makedirs(MEMORY_DIR, exist_ok=True)
os.makedirs(KB_DIR, exist_ok=True)

# ─── 配置管理 ──────────────────────────────────────────────
from config import load_config as _load_config

# ─── 时间衰减参数（默认值，可被配置覆盖）──────────────────────
HALF_LIFE_DAYS = 30
MIN_IMPORTANCE = 0.1


def _decay_factor(timestamp: float, importance: float, half_life: float = None) -> float:
    """计算时间衰减后的有效重要性"""
    if half_life is None:
        half_life = HALF_LIFE_DAYS
    age_days = (time.time() - timestamp) / 86400
    return importance * (0.5 ** (age_days / half_life))


# ─── 性能监控 ──────────────────────────────────────────────
class Metrics:
    """轻量级性能指标收集器"""

    def __init__(self, metrics_dir: str):
        self._path = os.path.join(metrics_dir, "metrics.json")
        self._data = self._load()

    def _load(self) -> dict:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {
            "add_count": 0,
            "search_count": 0,
            "dedup_count": 0,
            "filter_count": 0,
            "search_total_ms": 0.0,
            "add_total_ms": 0.0,
            "errors": 0,
            "last_updated": None,
        }

    def _save(self):
        self._data["last_updated"] = datetime.now(timezone.utc).isoformat()
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def record_add(self, elapsed_ms: float, dedup: bool = False, filtered: bool = False):
        self._data["add_count"] += 1
        self._data["add_total_ms"] += elapsed_ms
        if dedup:
            self._data["dedup_count"] += 1
        if filtered:
            self._data["filter_count"] += 1
        self._save()

    def record_search(self, elapsed_ms: float):
        self._data["search_count"] += 1
        self._data["search_total_ms"] += elapsed_ms
        self._save()

    def record_error(self):
        self._data["errors"] += 1
        self._save()

    def summary(self) -> dict:
        d = dict(self._data)
        if d["search_count"] > 0:
            d["search_avg_ms"] = round(d["search_total_ms"] / d["search_count"], 2)
        else:
            d["search_avg_ms"] = 0
        if d["add_count"] > 0:
            d["add_avg_ms"] = round(d["add_total_ms"] / d["add_count"], 2)
        else:
            d["add_avg_ms"] = 0
        return d


class MemoryManager:
    """记忆管理器 — 统一管理记忆的增删改查和知识库"""

    def __init__(self, encoder=None, model_id: str = None):
        self._encoder = encoder
        self._model_id = model_id
        self._store = None
        self._kb_stores = {}
        self._config = _load_config()
        metrics_enabled = self._config.get("metrics_enabled", True)
        self._metrics = Metrics(DATA_DIR) if metrics_enabled else None

    def _get_encoder(self):
        if self._encoder is None:
            from core import get_engine
            model = self._model_id or self._config.get("model_id")
            self._encoder = get_engine(model)
        return self._encoder

    def _get_store(self) -> "VectorStore":
        if self._store is None:
            from vector_store import VectorStore
            dim = self._get_encoder().dimension
            self._store = VectorStore(MEMORY_DIR, dim=dim)
        return self._store

    def _get_kb_store(self, kb_name: str) -> "VectorStore":
        if kb_name not in self._kb_stores:
            from vector_store import VectorStore
            dim = self._get_encoder().dimension
            kb_path = os.path.join(KB_DIR, kb_name)
            os.makedirs(kb_path, exist_ok=True)
            self._kb_stores[kb_name] = VectorStore(kb_path, dim=dim)
        return self._kb_stores[kb_name]

    # ─── 去重 ────────────────────────────────────────────────

    def _check_duplicate(self, text: str) -> str | None:
        """
        检查文本是否与已有记忆高度重复
        返回: 重复记忆的 ID，或 None
        """
        threshold = self._config.get("dedup_threshold", 0.95)
        encoder = self._get_encoder()
        query_vec = encoder.encode_single(text)
        store = self._get_store()

        # 搜索 top 1 最相似的
        results = store.search(query_vec, top_k=1)
        if results:
            mid, score, meta = results[0]
            if score >= threshold:
                return mid
        return None

    # ─── 记忆 CRUD ────────────────────────────────────────

    def add(self, text: str, tags: list = None, importance: float = 0.5,
            source: str = "manual", metadata: dict = None, skip_filter: bool = False) -> str:
        """
        添加一条记忆
        text: 记忆文本内容
        tags: 标签列表
        importance: 重要性 0.0-1.0
        source: 来源
        metadata: 额外元数据
        skip_filter: 跳过敏感信息过滤
        返回: memory_id 或 "filtered:xxx" 或 "dedup:xxx"
        """
        t0 = time.time()
        dedup = False
        filtered = False

        # 敏感信息过滤
        if not skip_filter:
            filter_enabled = self._config.get("sensitive_filter_enabled", True)
            if filter_enabled:
                from sensitive_filter import should_store, sanitize
                should, reason = should_store(text)
                if not should:
                    filtered = True
                    if self._metrics:
                        self._metrics.record_add(0, filtered=True)
                    return f"filtered:{reason}"
                text = sanitize(text)

        # 去重检查
        if self._config.get("dedup_enabled", True):
            dup_id = self._check_duplicate(text)
            if dup_id:
                dedup = True
                store = self._get_store()
                meta = store.get_meta(dup_id)
                if meta:
                    meta["importance"] = min(1.0, meta.get("importance", 0.5) + 0.05)
                    meta["duplicate_count"] = meta.get("duplicate_count", 0) + 1
                    store.save()
                if self._metrics:
                    self._metrics.record_add(0, dedup=True)
                return f"dedup:{dup_id}"

        memory_id = str(uuid.uuid4())[:12]
        now = time.time()

        encoder = self._get_encoder()
        vector = encoder.encode_single(text)

        meta = {
            "text": text,
            "tags": tags or [],
            "importance": importance,
            "source": source,
            "timestamp": now,
            "created_at": datetime.fromtimestamp(now, tz=timezone.utc).isoformat(),
            "access_count": 0,
            "last_accessed": now,
        }
        if metadata:
            meta.update(metadata)

        store = self._get_store()
        store.add(memory_id, vector, meta)
        store.save()

        elapsed_ms = (time.time() - t0) * 1000
        if self._metrics:
            self._metrics.record_add(elapsed_ms)

        return memory_id

    def add_conversation(self, role: str, content: str, session_id: str = None):
        """
        自动存储对话消息（由对话 Hook 调用）
        """
        # 敏感信息过滤
        filter_enabled = self._config.get("sensitive_filter_enabled", True)
        if filter_enabled:
            from sensitive_filter import should_store, sanitize
            should, reason = should_store(content)
            if not should:
                return
            content = sanitize(content)

        importance = self._config.get("conversation_importance", 0.3)
        max_chars = self._config.get("chunk_max_chars", 512)
        overlap = self._config.get("chunk_overlap", 64)

        tags = ["conversation", role]
        if session_id:
            tags.append(f"session:{session_id}")

        chunks = self._chunk_text(content, max_chars=max_chars, overlap=overlap)
        for i, chunk in enumerate(chunks):
            self.add(
                text=chunk,
                tags=tags,
                importance=importance,
                source="conversation",
                skip_filter=True,
                metadata={"chunk_index": i, "total_chunks": len(chunks)},
            )

    def search(self, query: str, top_k: int = None, tag: str = None,
               kb_name: str = None, min_importance: float = 0.0,
               min_score: float = None) -> list:
        """语义检索记忆"""
        if top_k is None:
            top_k = self._config.get("search_top_k", 5)
        if min_score is None:
            min_score = self._config.get("search_min_score", 0.2)

        t0 = time.time()
        encoder = self._get_encoder()
        query_vec = encoder.encode_single(query)

        if kb_name:
            store = self._get_kb_store(kb_name)
        else:
            store = self._get_store()

        def filter_fn(meta):
            if tag and tag not in meta.get("tags", []):
                return False
            half_life = self._config.get("half_life_days", HALF_LIFE_DAYS)
            eff_importance = _decay_factor(
                meta.get("timestamp", 0), meta.get("importance", 0.5), half_life
            )
            if eff_importance < min_importance:
                return False
            return True

        results = store.search(query_vec, top_k=top_k, filter_fn=filter_fn)

        boost = self._config.get("recall_importance_boost", 0.02)
        output = []
        for mid, score, meta in results:
            if score < min_score:
                continue
            meta["access_count"] = meta.get("access_count", 0) + 1
            meta["last_accessed"] = time.time()
            meta["importance"] = min(1.0, meta.get("importance", 0.5) + boost)

            half_life = self._config.get("half_life_days", HALF_LIFE_DAYS)
            eff_imp = _decay_factor(meta.get("timestamp", 0), meta.get("importance", 0.5), half_life)
            output.append({
                "id": mid,
                "text": meta.get("text", ""),
                "score": score,
                "effective_importance": round(eff_imp, 4),
                "tags": meta.get("tags", []),
                "importance": meta.get("importance", 0.5),
                "timestamp": meta.get("timestamp", 0),
                "created_at": meta.get("created_at", ""),
                "source": meta.get("source", ""),
            })

        store.save()

        elapsed_ms = (time.time() - t0) * 1000
        if self._metrics:
            self._metrics.record_search(elapsed_ms)

        return output

    def get(self, memory_id: str) -> dict | None:
        """获取单条记忆"""
        store = self._get_store()
        meta = store.get_meta(memory_id)
        if meta is None:
            return None
        half_life = self._config.get("half_life_days", HALF_LIFE_DAYS)
        eff_imp = _decay_factor(meta.get("timestamp", 0), meta.get("importance", 0.5), half_life)
        return {
            "id": memory_id,
            "text": meta.get("text", ""),
            "tags": meta.get("tags", []),
            "importance": meta.get("importance", 0.5),
            "effective_importance": round(eff_imp, 4),
            "source": meta.get("source", ""),
            "created_at": meta.get("created_at", ""),
            "access_count": meta.get("access_count", 0),
            "duplicate_count": meta.get("duplicate_count", 0),
        }

    def list_memories(self, tag: str = None, limit: int = 50,
                      sort_by: str = "timestamp") -> list:
        """列出记忆"""
        store = self._get_store()
        items = store.list_all(tag=tag, limit=limit, sort_by=sort_by)
        result = []
        for mid, meta in items:
            half_life = self._config.get("half_life_days", HALF_LIFE_DAYS)
            eff_imp = _decay_factor(meta.get("timestamp", 0), meta.get("importance", 0.5), half_life)
            result.append({
                "id": mid,
                "text": meta.get("text", "")[:100] + ("..." if len(meta.get("text", "")) > 100 else ""),
                "tags": meta.get("tags", []),
                "importance": meta.get("importance", 0.5),
                "effective_importance": round(eff_imp, 4),
                "created_at": meta.get("created_at", ""),
            })
        return result

    def tag(self, memory_id: str, tags: list) -> bool:
        """给记忆添加标签"""
        store = self._get_store()
        meta = store.get_meta(memory_id)
        if meta is None:
            return False
        existing = set(meta.get("tags", []))
        existing.update(tags)
        meta["tags"] = list(existing)
        store.save()
        return True

    def set_importance(self, memory_id: str, importance: float) -> bool:
        """设置记忆重要性"""
        store = self._get_store()
        meta = store.get_meta(memory_id)
        if meta is None:
            return False
        meta["importance"] = max(0.0, min(1.0, importance))
        store.save()
        return True

    def edit(self, memory_id: str, new_text: str) -> bool:
        """编辑记忆内容（需要重新向量化）"""
        store = self._get_store()
        meta = store.get_meta(memory_id)
        if meta is None:
            return False
        encoder = self._get_encoder()
        new_vec = encoder.encode_single(new_text)
        meta["text"] = new_text
        meta["edited_at"] = datetime.now(timezone.utc).isoformat()
        store.update(memory_id, new_vec, meta)
        store.save()
        return True

    def delete(self, memory_id: str) -> bool:
        """删除一条记忆"""
        store = self._get_store()
        ok = store.delete(memory_id)
        if ok:
            store.save()
        return ok

    def clear(self, confirm: bool = False) -> bool:
        """清空所有记忆"""
        if not confirm:
            return False
        store = self._get_store()
        store.clear()
        store.save()
        return True

    def stats(self) -> dict:
        """获取记忆统计"""
        store = self._get_store()
        encoder = self._get_encoder()
        all_items = store.list_all(limit=999999)
        total = len(all_items)

        by_tag = {}
        by_source = {}
        for mid, meta in all_items:
            for t in meta.get("tags", []):
                by_tag[t] = by_tag.get(t, 0) + 1
            src = meta.get("source", "unknown")
            by_source[src] = by_source.get(src, 0) + 1

        half_life = self._config.get("half_life_days", HALF_LIFE_DAYS)
        min_imp = self._config.get("min_importance", MIN_IMPORTANCE)
        low_value = 0
        for _, meta in all_items:
            eff = _decay_factor(meta.get("timestamp", 0), meta.get("importance", 0.5), half_life)
            if eff < min_imp:
                low_value += 1

        result = {
            "total_memories": total,
            "model": self._encoder.model_id if self._encoder else "unknown",
            "dimension": encoder.dimension,
            "by_tag": by_tag,
            "by_source": by_source,
            "low_value_count": low_value,
            "index_type": type(store._index).__name__,
        }

        # 附加性能指标
        if self._metrics:
            result["metrics"] = self._metrics.summary()

        return result

    # ─── 自动遗忘 ─────────────────────────────────────────

    def auto_forget(self, dry_run: bool = True) -> list:
        """自动遗忘低价值记忆"""
        min_imp = self._config.get("min_importance", MIN_IMPORTANCE)
        half_life = self._config.get("half_life_days", HALF_LIFE_DAYS)

        store = self._get_store()
        all_items = store.list_all(limit=999999)
        forgotten = []

        for mid, meta in all_items:
            eff = _decay_factor(
                meta.get("timestamp", 0), meta.get("importance", 0.5), half_life
            )
            if "\u91cd\u8981" in meta.get("tags", []):
                continue
            if eff < min_imp:
                forgotten.append({
                    "id": mid,
                    "text": meta.get("text", "")[:80],
                    "effective_importance": round(eff, 4),
                })
                if not dry_run:
                    store.delete(mid)

        if not dry_run and forgotten:
            store.save()

        return forgotten

    # ─── 知识库管理 ────────────────────────────────────────

    def create_kb(self, name: str, description: str = "") -> dict:
        """创建知识库"""
        kb_path = os.path.join(KB_DIR, name)
        if os.path.exists(kb_path):
            return {"error": f"知识库 '{name}' 已存在"}
        os.makedirs(kb_path, exist_ok=True)

        kb_meta = {
            "name": name,
            "description": description,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "document_count": 0,
        }
        with open(os.path.join(kb_path, "kb_meta.json"), "w", encoding="utf-8") as f:
            json.dump(kb_meta, f, ensure_ascii=False, indent=2)

        return {"status": "created", "name": name}

    def list_kbs(self) -> list:
        """列出所有知识库"""
        if not os.path.exists(KB_DIR):
            return []
        result = []
        for name in os.listdir(KB_DIR):
            kb_meta_path = os.path.join(KB_DIR, name, "kb_meta.json")
            if os.path.exists(kb_meta_path):
                with open(kb_meta_path, "r", encoding="utf-8") as f:
                    result.append(json.load(f))
            else:
                result.append({"name": name})
        return result

    def add_to_kb(self, kb_name: str, text: str, source_file: str = None,
                  tags: list = None) -> str:
        """向知识库添加文本内容"""
        store = self._get_kb_store(kb_name)
        encoder = self._get_encoder()

        max_chars = self._config.get("chunk_max_chars", 512)
        overlap = self._config.get("chunk_overlap", 64)
        chunks = self._chunk_text(text, max_chars=max_chars, overlap=overlap)
        chunk_ids = []
        for i, chunk in enumerate(chunks):
            chunk_id = str(uuid.uuid4())[:12]
            vector = encoder.encode_single(chunk)
            meta = {
                "text": chunk,
                "tags": tags or [],
                "source_file": source_file,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "importance": 0.7,
                "timestamp": time.time(),
            }
            store.add(chunk_id, vector, meta)
            chunk_ids.append(chunk_id)

        store.save()

        kb_meta_path = os.path.join(KB_DIR, kb_name, "kb_meta.json")
        if os.path.exists(kb_meta_path):
            with open(kb_meta_path, "r", encoding="utf-8") as f:
                kb_meta = json.load(f)
            kb_meta["document_count"] = kb_meta.get("document_count", 0) + 1
            with open(kb_meta_path, "w", encoding="utf-8") as f:
                json.dump(kb_meta, f, ensure_ascii=False, indent=2)

        return f"Added {len(chunk_ids)} chunks to '{kb_name}'"

    def query_kb(self, kb_name: str, question: str, top_k: int = 5) -> list:
        """在知识库中语义检索"""
        return self.search(question, top_k=top_k, kb_name=kb_name)

    def delete_kb(self, kb_name: str) -> dict:
        """删除知识库"""
        import shutil
        kb_path = os.path.join(KB_DIR, kb_name)
        if not os.path.exists(kb_path):
            return {"error": f"知识库 '{kb_name}' 不存在"}
        shutil.rmtree(kb_path)
        if kb_name in self._kb_stores:
            del self._kb_stores[kb_name]
        return {"status": "deleted", "name": kb_name}

    # ─── 加密 ──────────────────────────────────────────────

    def encrypt(self, password: str) -> dict:
        """加密记忆库"""
        try:
            from cryptography.fernet import Fernet
            import base64
            key = base64.urlsafe_b64encode(
                __import__("hashlib").pbkdf2_hmac(
                    "sha256", password.encode(), b"semantic-memory-salt", 100000
                )[:32]
            )
            fernet = Fernet(key)

            store = self._get_store()
            store.save()

            for fname in ["index.faiss", "metadata.json"]:
                fpath = os.path.join(MEMORY_DIR, fname)
                if os.path.exists(fpath):
                    with open(fpath, "rb") as f:
                        data = f.read()
                    encrypted = fernet.encrypt(data)
                    with open(fpath + ".enc", "wb") as f:
                        f.write(encrypted)
                    os.remove(fpath)

            return {"status": "encrypted"}
        except ImportError:
            return {"error": "加密功能需要 cryptography 库，请运行: pip install cryptography"}

    def unlock(self, password: str) -> dict:
        """解密记忆库"""
        try:
            from cryptography.fernet import Fernet, InvalidToken
            import base64

            key = base64.urlsafe_b64encode(
                __import__("hashlib").pbkdf2_hmac(
                    "sha256", password.encode(), b"semantic-memory-salt", 100000
                )[:32]
            )
            fernet = Fernet(key)

            decrypted_files = []
            for fname in ["index.faiss", "metadata.json"]:
                enc_path = os.path.join(MEMORY_DIR, fname + ".enc")
                if os.path.exists(enc_path):
                    with open(enc_path, "rb") as f:
                        encrypted = f.read()
                    try:
                        data = fernet.decrypt(encrypted)
                    except InvalidToken:
                        return {"error": "密码错误或数据已损坏"}
                    with open(os.path.join(MEMORY_DIR, fname), "wb") as f:
                        f.write(data)
                    os.remove(enc_path)
                    decrypted_files.append(fname)

            # 重新加载
            self._store = None
            return {"status": "unlocked", "decrypted_files": decrypted_files}
        except ImportError:
            return {"error": "加密功能需要 cryptography 库"}

    # ─── 文本分块 ──────────────────────────────────────────

    @staticmethod
    def _chunk_text(text: str, max_chars: int = 512, overlap: int = 64) -> list:
        """
        智能文本分块
        - 优先按段落分割
        - 超长段落按句子分割
        - 超长句子强制截断（防止 >10MB 文档的单句过巨）
        - 支持重叠窗口
        """
        if len(text) <= max_chars:
            return [text]

        # 按段落分割
        paragraphs = re.split(r'\n\s*\n|\n', text)
        chunks = []
        current_chunk = ""

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue

            if len(current_chunk) + len(para) + 1 <= max_chars:
                current_chunk = (current_chunk + "\n" + para).strip() if current_chunk else para
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                # 如果单个段落就超长，按句子再分
                if len(para) > max_chars:
                    sentences = re.split(r'(?<=[。！？.!?])\s*', para)
                    current_chunk = ""
                    for sent in sentences:
                        # 超长句子强制截断（大文档防护）
                        if len(sent) > max_chars:
                            # 按固定长度截断
                            for j in range(0, len(sent), max_chars):
                                sub = sent[j:j + max_chars]
                                if current_chunk and len(current_chunk) + len(sub) + 1 <= max_chars:
                                    current_chunk = (current_chunk + " " + sub).strip()
                                else:
                                    if current_chunk:
                                        chunks.append(current_chunk)
                                    current_chunk = sub
                        elif len(current_chunk) + len(sent) + 1 <= max_chars:
                            current_chunk = (current_chunk + " " + sent).strip() if current_chunk else sent
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sent
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        # 添加重叠
        if overlap > 0 and len(chunks) > 1:
            overlapped = [chunks[0]]
            for i in range(1, len(chunks)):
                prev_tail = chunks[i - 1][-overlap:] if len(chunks[i - 1]) > overlap else chunks[i - 1]
                overlapped.append(prev_tail + " " + chunks[i])
            return overlapped

        return chunks


    # ─── 批量操作 ─────────────────────────────────────────

    def batch_add(
        self,
        items: list[dict | tuple],
        tags: list[str] | None = None,
        importance: float | None = None,
        progress: bool = False,
    ) -> dict:
        """
        批量添加多条记忆

        Args:
            items: 支持两种格式：
                   - dict: {"text": str, "tags": list, "importance": float}
                   - tuple: (text, tags, importance) 三元组
            tags: 每条记忆的默认标签（覆盖 dict 中的 tags）
            importance: 每条记忆的默认重要性（覆盖 dict 中的 importance）
            progress: 是否显示进度

        Returns:
            {"added": [id1, id2, ...], "failed": [{"item": ..., "error": "..."}],
             "total": N, "success": M}
        """
        results = {"added": [], "failed": [], "total": len(items), "success": 0}
        for i, item in enumerate(items):
            if progress and i % 10 == 0:
                logger.info(f"批量添加进度: {i}/{len(items)}")

            try:
                if isinstance(item, dict):
                    text = item["text"]
                    item_tags = tags if tags is not None else item.get("tags")
                    item_imp = importance if importance is not None else item.get("importance")
                else:
                    text, item_tags, item_imp = item
                    item_tags = tags if tags is not None else item_tags
                    item_imp = importance if importance is not None else item_imp

                mid = self.add(text, tags=item_tags, importance=item_imp)
                results["added"].append(mid)
                results["success"] += 1
            except Exception as e:
                results["failed"].append({"item": str(item)[:100], "error": str(e)})

        if progress:
            logger.info(f"批量添加完成: 成功 {results['success']}/{results['total']}")
        return results

    def batch_search(
        self,
        queries: list[str],
        top_k: int = 5,
        n_results: int = 10,
    ) -> dict[int, list[dict]]:
        """
        批量搜索多条查询

        Args:
            queries: 查询列表
            top_k: 每条查询返回的最相关记忆数
            n_results: 总体返回数量上限

        Returns:
            {query_index: [results...], ...}
        """
        return {
            i: self.search(q, top_k=top_k, n_results=n_results)
            for i, q in enumerate(queries)
        }


if __name__ == "__main__":
    mgr = MemoryManager()

    # 批量添加示例
    batch = [
        {"text": "今天和李四讨论了项目计划", "tags": ["工作"], "importance": 0.8},
        {"text": "AI 助手可以帮助写代码和文档", "tags": ["技术"], "importance": 0.7},
        {"text": "下周要去北京出差", "tags": ["出差"], "importance": 0.9},
    ]
    result = mgr.batch_add(batch, progress=True)
    print(f"批量添加结果: 成功 {result['success']}/{result['total']}")

    # 批量搜索示例
    search_results = mgr.batch_search(["项目计划", "出差安排"])
    for idx, results in search_results.items():
        print(f"\n查询 {idx}: 找到 {len(results)} 条")
