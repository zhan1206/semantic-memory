#!/usr/bin/env python3
"""
Semantic Memory — ONNX Embedding 引擎
内置量化小模型，CPU 极速推理，自动下载模型+分词器
"""
import os
import sys
import json
import time
import hashlib
import numpy as np

# ─── 路径配置 ───────────────────────────────────────────────
SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
# Resolve data dir: scripts/ -> semantic-memory/ -> skills/ -> .qclaw/ -> data/semantic-memory/
_QCLAW_BASE = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))
DATA_DIR = os.path.join(
    os.environ.get("QCLAW_DATA", os.path.join(_QCLAW_BASE, "data")),
    "semantic-memory",
)
MODEL_DIR = os.path.join(DATA_DIR, "models")
os.makedirs(MODEL_DIR, exist_ok=True)

# ─── 模型注册表 ─────────────────────────────────────────────
MODEL_REGISTRY = {
    "all-MiniLM-L6-v2": {
        "dim": 384,
        "max_len": 256,
        "pooling": "mean",
        "desc": "英文/多语言通用 (~30MB ONNX INT8)",
        "repo": "Xenova/all-MiniLM-L6-v2",
        "files": {
            "model.onnx": "onnx/model_quantized.onnx",
            "tokenizer.json": "tokenizer.json",
            "config.json": "config.json",
        },
        "lang": "en",
    },
    "bge-small-zh-v1.5": {
        "dim": 512,
        "max_len": 512,
        "pooling": "cls",
        "desc": "中文专用 (~30MB ONNX INT8)",
        "repo": "Xenova/bge-small-zh-v1.5",
        "files": {
            "model.onnx": "onnx/model_quantized.onnx",
            "tokenizer.json": "tokenizer.json",
            "config.json": "config.json",
        },
        "lang": "zh",
    },
}
DEFAULT_MODEL = "all-MiniLM-L6-v2"

# HuggingFace 镜像站（国内用户优先）
MIRROR_URLS = [
    "https://hf-mirror.com",
    "https://huggingface.co",
]


# ─── 自动模型下载 ──────────────────────────────────────────
def _download_file(url: str, dest: str, desc: str = ""):
    """带进度和重试的 HTTP 下载"""
    import urllib.request
    import urllib.error

    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "SemanticMemory/1.0"})
            with urllib.request.urlopen(req, timeout=120) as resp:
                total = int(resp.headers.get("Content-Length", 0)) or 0
                done = 0
                with open(dest + ".tmp", "wb") as f:
                    while True:
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        done += len(chunk)
                        if total and done % (512 * 1024) < 65536:
                            pct = done * 100 // total
                            print(f"\r  [{pct:3d}%] {done // 1024}KB/{total // 1024}KB",
                                  end="", flush=True)
            # 原子重命名
            if os.path.exists(dest):
                os.remove(dest)
            os.rename(dest + ".tmp", dest)
            print(flush=True, file=sys.stderr)
            return True
        except Exception as e:
            if os.path.exists(dest + ".tmp"):
                os.remove(dest + ".tmp")
            if attempt < 2:
                print(f"\n  Retry {attempt + 2}...", flush=True, file=sys.stderr)
                time.sleep(2)
            else:
                print(f"\n  Download failed: {e}", flush=True, file=sys.stderr)
    return False


def _ensure_model(model_id: str) -> str:
    """确保模型文件已下载，返回模型目录路径"""
    meta = MODEL_REGISTRY[model_id]
    model_dir = os.path.join(MODEL_DIR, model_id)
    os.makedirs(model_dir, exist_ok=True)

    all_exist = True
    for fname in meta["files"]:
        if not os.path.exists(os.path.join(model_dir, fname)):
            all_exist = False
            break

    if all_exist:
        return model_dir

    # 尝试各镜像站
    for mirror in MIRROR_URLS:
        repo = meta["repo"]
        success = True
        for fname, remote_path in meta["files"].items():
            dest = os.path.join(model_dir, fname)
            if os.path.exists(dest):
                continue
            url = f"{mirror}/{repo}/resolve/main/{remote_path}"
            print(f"[semantic-memory] Downloading {model_id}/{fname}...", flush=True, file=sys.stderr)
            if not _download_file(url, dest):
                success = False
                break
        if success:
            return model_dir
        else:
            # 清理不完整的下载
            for fname in meta["files"]:
                p = os.path.join(model_dir, fname)
                if os.path.exists(p):
                    os.remove(p)

    raise RuntimeError(f"Failed to download model '{model_id}' from all mirrors")


# ─── 依赖检查 ──────────────────────────────────────────────
def _ensure_deps():
    """确保核心依赖已安装"""
    try:
        import onnxruntime
        import faiss
        from tokenizers import Tokenizer
        return True
    except ImportError:
        sys.path.insert(0, SKILL_DIR)
        from installer import main as install_main
        install_main()
        return True


# ─── ONNX 编码器 ──────────────────────────────────────────
class EmbeddingEngine:
    """
    基于 ONNX Runtime 的 Embedding 引擎
    使用 HuggingFace tokenizers 做分词，onnxruntime 做推理
    """

    def __init__(self, model_id: str = DEFAULT_MODEL):
        _ensure_deps()

        self.model_id = model_id
        self.meta = MODEL_REGISTRY[model_id]
        self._dim = self.meta["dim"]
        self._max_len = self.meta["max_len"]
        self._pooling = self.meta["pooling"]

        # 下载模型
        model_dir = _ensure_model(model_id)

        # 加载分词器
        from tokenizers import Tokenizer
        tok_path = os.path.join(model_dir, "tokenizer.json")
        self._tokenizer = Tokenizer.from_file(tok_path)
        self._tokenizer.enable_truncation(max_length=self._max_len)
        self._tokenizer.enable_padding(length=self._max_len)

        # 加载 ONNX 模型
        import onnxruntime as ort
        model_path = os.path.join(model_dir, "model.onnx")
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.intra_op_num_threads = min(4, os.cpu_count() or 1)
        opts.inter_op_num_threads = 1
        self._session = ort.InferenceSession(model_path, opts)

        # 读取 ONNX 输入/输出名
        self._input_names = [inp.name for inp in self._session.get_inputs()]
        self._output_name = self._session.get_outputs()[0].name

        print(f"[semantic-memory] OK Engine ready: {model_id} dim={self._dim}", flush=True, file=sys.stderr)

    @property
    def dimension(self) -> int:
        return self._dim

    def encode(self, texts: list | str) -> np.ndarray:
        """
        文本 → 向量
        texts: str 或 list[str]
        返回: np.ndarray shape=(N, dim), dtype=float32, L2-normalized
        """
        if isinstance(texts, str):
            texts = [texts]

        # 分词
        encoded = self._tokenizer.encode_batch(texts)
        input_ids = np.array([e.ids for e in encoded], dtype=np.int64)
        attention_mask = np.array([e.attention_mask for e in encoded], dtype=np.int64)

        # 构建 ONNX 输入
        feed = {
            "input_ids": input_ids,
            "attention_mask": attention_mask,
        }
        # 某些模型还需要 token_type_ids
        if "token_type_ids" in self._input_names:
            token_type_ids = np.zeros_like(input_ids, dtype=np.int64)
            feed["token_type_ids"] = token_type_ids

        # 推理
        outputs = self._session.run([self._output_name], feed)
        token_embeddings = outputs[0]  # (N, seq_len, dim)

        # 池化
        if self._pooling == "mean":
            # Mean Pooling: 只对非 padding 位置取均值
            mask_expanded = attention_mask[:, :, np.newaxis].astype(np.float32)
            sum_emb = np.sum(token_embeddings * mask_expanded, axis=1)
            sum_mask = np.clip(mask_expanded.sum(axis=1), a_min=1e-9, a_max=None)
            embeddings = sum_emb / sum_mask
        elif self._pooling == "cls":
            # CLS Pooling: 取第一个 token 的输出
            embeddings = token_embeddings[:, 0, :]
        else:
            embeddings = token_embeddings[:, 0, :]

        # L2 归一化
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1, norms)
        embeddings = embeddings / norms

        return embeddings.astype(np.float32)

    def encode_single(self, text: str) -> np.ndarray:
        """单条文本编码，返回 1D 向量"""
        return self.encode([text])[0]


# ─── 语言检测 ──────────────────────────────────────────────
def _detect_chinese_ratio(text: str) -> float:
    """检测文本中中文字符占比"""
    if not text:
        return 0.0
    cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    return cn / len(text)


def auto_encode(texts: list | str, engine_map: dict = None) -> np.ndarray:
    """
    自动语言检测：中文占比较高时用 bge-small-zh，否则用 all-MiniLM-L6-v2
    """
    if isinstance(texts, str):
        texts = [texts]

    # 统计中文字符占比
    all_text = " ".join(texts)
    cn_ratio = _detect_chinese_ratio(all_text)

    # 如果有 bge-small-zh 模型且中文占比较高，使用中文模型
    use_zh = cn_ratio > 0.3 and "bge-small-zh-v1.5" in MODEL_REGISTRY

    if engine_map and use_zh and "zh" in engine_map:
        return engine_map["zh"].encode(texts)

    # 默认用英文模型
    if engine_map and "en" in engine_map:
        return engine_map["en"].encode(texts)

    # 没有 engine_map 时自动创建
    model_id = "bge-small-zh-v1.5" if use_zh else DEFAULT_MODEL
    engine = EmbeddingEngine(model_id)
    return engine.encode(texts)


# ─── 便捷函数 ──────────────────────────────────────────────
_global_engine = None


def get_engine(model_id: str = None) -> EmbeddingEngine:
    """获取全局编码器实例（懒加载单例）"""
    global _global_engine
    if _global_engine is None or (model_id and _global_engine.model_id != model_id):
        _global_engine = EmbeddingEngine(model_id or DEFAULT_MODEL)
    return _global_engine


if __name__ == "__main__":
    # 简单测试
    print("=== Semantic Memory Embedding Engine Test ===")
    engine = get_engine()
    vec = engine.encode_single("Hello, world!")
    print(f"Vector dim: {len(vec)}, norm: {np.linalg.norm(vec):.4f}")
    print(f"First 5 values: {vec[:5]}")

    # 中文测试
    vec_zh = engine.encode_single("你好，世界！")
    print(f"Chinese vector norm: {np.linalg.norm(vec_zh):.4f}")
