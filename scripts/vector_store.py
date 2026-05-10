#!/usr/bin/env python3
"""
from __future__ import annotations
Semantic Memory — FAISS 向量存储引擎
嵌入式本地向量数据库，支持增量更新、IVF 索引、毫秒级检索
"""
import os
import sys
import json
import time
import numpy as np

# ─── 路径 ──────────────────────────────────────────────────
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_QCLAW_BASE = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))
DATA_DIR = os.path.join(
    os.environ.get("QCLAW_DATA", os.path.join(_QCLAW_BASE, "data")),
    "semantic-memory",
)


class VectorStore:
    """
    基于 FAISS 的本地向量存储
    - 小规模 (<10000): 使用 IndexFlatIP（精确内积搜索）
    - 大规模 (≥10000): 自动升级为 IndexIVFFlat（IVF 倒排索引）
    - 数据持久化: FAISS 索引文件 + JSON 元数据
    """

    def __init__(self, store_dir: str, dim: int = 384):
        self.store_dir = store_dir
        self.dim = dim
        os.makedirs(store_dir, exist_ok=True)

        self._index_path = os.path.join(store_dir, "index.faiss")
        self._meta_path = os.path.join(store_dir, "metadata.json")

        self._metadata: dict = {}  # id -> {text, tags, importance, timestamp, ...}
        self._id_to_idx: dict = {}  # memory_id -> faiss internal index
        self._idx_to_id: dict = {}  # faiss internal index -> memory_id
        self._next_idx: int = 0

        import faiss
        self._faiss = faiss

        # 加载或初始化
        self._load()

    def _load(self):
        """从磁盘加载索引和元数据"""
        if os.path.exists(self._meta_path):
            with open(self._meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self._metadata = data.get("metadata", {})
            self._id_to_idx = {k: v for k, v in data.get("id_to_idx", {}).items()}
            self._idx_to_id = {int(k): v for k, v in data.get("idx_to_id", {}).items()}
            self._next_idx = data.get("next_idx", 0)

        if os.path.exists(self._index_path):
            # Use Python open() to support Unicode paths on Windows
            with open(self._index_path, "rb") as f:
                buf = np.frombuffer(f.read(), dtype=np.uint8)
            self._index = self._faiss.deserialize_index(buf)
        else:
            self._index = self._faiss.IndexFlatIP(self.dim)

        # 大规模时自动升级为 IVF
        self._maybe_upgrade_index()

    def _maybe_upgrade_index(self):
        """当向量数 ≥ 10000 时自动升级为 IVF 索引"""
        n = self._index.ntotal
        if n >= 10000 and not isinstance(self._index, self._faiss.IndexIVFFlat):
            nlist = min(int(np.sqrt(n)), 256)  # IVF 聚类数
            quantizer = self._faiss.IndexFlatIP(self.dim)
            ivf = self._faiss.IndexIVFFlat(quantizer, self.dim, nlist,
                                            self._faiss.METRIC_INNER_PRODUCT)
            # 训练 IVF
            vectors = self._index.reconstruct_n(0, n)
            ivf.train(vectors)
            ivf.add(vectors)
            ivf.nprobe = min(nlist // 4, 16)  # 搜索时探测的聚类数
            self._index = ivf
            print(f"[semantic-memory] Upgraded to IVF index (nlist={nlist}, nprobe={ivf.nprobe})",
                  flush=True, file=sys.stderr)

    def save(self):
        """持久化索引和元数据到磁盘"""
        # Use faiss.serialize_index + Python open() to support Unicode paths
        buf = self._faiss.serialize_index(self._index)
        with open(self._index_path, "wb") as f:
            f.write(buf)
        data = {
            "metadata": self._metadata,
            "id_to_idx": self._id_to_idx,
            "idx_to_id": {str(k): v for k, v in self._idx_to_id.items()},
            "next_idx": self._next_idx,
        }
        with open(self._meta_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add(self, memory_id: str, vector: np.ndarray, meta: dict):
        """添加一条记忆向量"""
        assert vector.shape == (self.dim,), f"Vector dim mismatch: {vector.shape} vs {self.dim})"

        vec = vector.reshape(1, -1).astype(np.float32)
        self._index.add(vec)

        idx = self._next_idx
        self._next_idx += 1

        self._id_to_idx[memory_id] = idx
        self._idx_to_id[idx] = memory_id
        self._metadata[memory_id] = meta

        # 检查是否需要升级索引
        self._maybe_upgrade_index()

    def add_batch(self, memory_ids: list, vectors: np.ndarray, metas: list):
        """批量添加记忆向量"""
        assert vectors.shape[1] == self.dim
        vecs = vectors.astype(np.float32)
        self._index.add(vecs)

        for i, (mid, meta) in enumerate(zip(memory_ids, metas)):
            idx = self._next_idx
            self._next_idx += 1
            self._id_to_idx[mid] = idx
            self._idx_to_id[idx] = mid
            self._metadata[mid] = meta

        self._maybe_upgrade_index()

    def search(self, query_vector: np.ndarray, top_k: int = 5,
               filter_fn=None) -> list:
        """
        语义检索
        query_vector: shape=(dim,)
        top_k: 返回最相似的 K 条
        filter_fn: 可选过滤函数 (metadata_dict) -> bool
        返回: [(memory_id, score, metadata), ...]
        """
        vec = query_vector.reshape(1, -1).astype(np.float32)

        # 搜索更多候选，以便过滤后仍有足够结果
        search_k = min(top_k * 3, self._index.ntotal) if filter_fn else top_k
        search_k = max(search_k, 1)

        scores, indices = self._index.search(vec, search_k)

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            mid = self._idx_to_id.get(int(idx))
            if mid is None:
                continue
            meta = self._metadata.get(mid, {})
            if filter_fn and not filter_fn(meta):
                continue
            results.append((mid, float(score), meta))
            if len(results) >= top_k:
                break

        return results

    def delete(self, memory_id: str) -> bool:
        """
        删除一条记忆
        FAISS 不支持直接删除，采用标记删除 + 重建策略
        """
        if memory_id not in self._metadata:
            return False

        # 从元数据中移除
        del self._metadata[memory_id]
        if memory_id in self._id_to_idx:
            idx = self._id_to_idx.pop(memory_id)
            self._idx_to_id.pop(idx, None)

        # 重建索引（去掉已删除的向量）
        self._rebuild_index()
        return True

    def _rebuild_index(self):
        """从元数据重建 FAISS 索引（删除操作后调用）"""
        # 收集所有仍存活的向量
        remaining_ids = list(self._metadata.keys())
        if not remaining_ids:
            self._index = self._faiss.IndexFlatIP(self.dim)
            self._id_to_idx = {}
            self._idx_to_id = {}
            self._next_idx = 0
            return

        # 从旧索引中提取向量
        old_vectors = []
        valid_ids = []
        for mid in remaining_ids:
            if mid in self._id_to_idx:
                old_idx = self._id_to_idx[mid]
                try:
                    vec = self._index.reconstruct(int(old_idx))
                    old_vectors.append(vec)
                    valid_ids.append(mid)
                except Exception:
                    continue

        if not old_vectors:
            self._index = self._faiss.IndexFlatIP(self.dim)
            self._id_to_idx = {}
            self._idx_to_id = {}
            self._next_idx = 0
            return

        # 创建新索引
        vectors = np.vstack(old_vectors).astype(np.float32)
        self._index = self._faiss.IndexFlatIP(self.dim)
        self._index.add(vectors)

        # 重建映射
        self._id_to_idx = {}
        self._idx_to_id = {}
        for i, mid in enumerate(valid_ids):
            self._id_to_idx[mid] = i
            self._idx_to_id[i] = mid
            self._metadata[mid]["_reindexed"] = True
        self._next_idx = len(valid_ids)

        # 检查是否需要升级
        self._maybe_upgrade_index()

    def update(self, memory_id: str, vector: np.ndarray, meta: dict):
        """更新一条记忆（删除旧的，添加新的）"""
        self.delete(memory_id)
        self.add(memory_id, vector, meta)

    def get_meta(self, memory_id: str) -> dict | None:
        """获取记忆元数据"""
        return self._metadata.get(memory_id)

    def list_all(self, tag: str = None, limit: int = 100,
                 sort_by: str = "timestamp") -> list:
        """列出所有记忆，可选按标签过滤"""
        items = []
        for mid, meta in self._metadata.items():
            if tag and tag not in meta.get("tags", []):
                continue
            items.append((mid, meta))

        # 排序
        if sort_by == "timestamp":
            items.sort(key=lambda x: x[1].get("timestamp", 0), reverse=True)
        elif sort_by == "importance":
            items.sort(key=lambda x: x[1].get("importance", 0), reverse=True)

        return items[:limit]

    @property
    def count(self) -> int:
        return len(self._metadata)

    def clear(self):
        """清空所有记忆"""
        self._index = self._faiss.IndexFlatIP(self.dim)
        self._metadata = {}
        self._id_to_idx = {}
        self._idx_to_id = {}
        self._next_idx = 0
