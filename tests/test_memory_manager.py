"""memory_manager.py 单元测试"""
import pytest
import numpy as np
import sys, os, tempfile, shutil

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))


def _make_norm_vec(dim=384):
    """生成随机 L2 归一化向量"""
    v = np.random.randn(dim).astype(np.float32)
    v = v / np.linalg.norm(v)
    return v


class TestMemoryManagerCRUD:
    """记忆 CRUD 测试"""

    @pytest.fixture
    def mgr(self, clean_data_dir):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import memory_manager as mm_mod
        # Patch DATA_DIR
        old_data_dir = mm_mod.DATA_DIR
        old_mem_dir = mm_mod.MEMORY_DIR
        old_kb_dir = mm_mod.KB_DIR
        mm_mod.DATA_DIR = clean_data_dir
        mm_mod.MEMORY_DIR = os.path.join(clean_data_dir, "memories")
        mm_mod.KB_DIR = os.path.join(clean_data_dir, "kb")
        os.makedirs(mm_mod.MEMORY_DIR, exist_ok=True)
        os.makedirs(mm_mod.KB_DIR, exist_ok=True)

        mgr = mm_mod.MemoryManager()
        yield mgr

        mm_mod.DATA_DIR = old_data_dir
        mm_mod.MEMORY_DIR = old_mem_dir
        mm_mod.KB_DIR = old_kb_dir

    def test_add_and_get(self, mgr):
        mid = mgr.add("测试记忆内容", tags=["测试"], importance=0.8)
        assert mid not in ("filtered:", "dedup:")

        retrieved = mgr.get(mid)
        assert retrieved is not None
        assert retrieved["text"] == "测试记忆内容"
        assert retrieved["tags"] == ["测试"]
        assert retrieved["importance"] == 0.8

    def test_add_filtered(self, mgr):
        """敏感信息应被过滤"""
        mid = mgr.add("sk-abc123def456ghi789jkl012mno345pqr678stuv901wxyz")
        assert mid.startswith("filtered:")

    def test_search(self, mgr):
        mgr.add("Python 是一种编程语言", tags=["编程"])
        mgr.add("今天天气很好", tags=["生活"])
        mgr.add("JavaScript 用于网页开发", tags=["编程"])

        results = mgr.search("编程语言", top_k=5)
        assert len(results) >= 1
        texts = [r["text"] for r in results]
        assert any("Python" in t or "JavaScript" in t for t in texts)

    def test_tag(self, mgr):
        mid = mgr.add("记忆内容")
        ok = mgr.tag(mid, ["重要", "工作"])
        assert ok is True

        m = mgr.get(mid)
        assert "重要" in m["tags"]
        assert "工作" in m["tags"]

    def test_set_importance(self, mgr):
        mid = mgr.add("内容")
        mgr.set_importance(mid, 0.9)
        m = mgr.get(mid)
        assert m["importance"] == 0.9

    def test_edit(self, mgr):
        mid = mgr.add("原始内容")
        ok = mgr.edit(mid, "修改后的内容")
        assert ok is True
        m = mgr.get(mid)
        assert m["text"] == "修改后的内容"

    def test_delete(self, mgr):
        mid = mgr.add("待删除记忆")
        ok = mgr.delete(mid)
        assert ok is True
        assert mgr.get(mid) is None

    def test_list_memories(self, mgr):
        for i in range(10):
            mgr.add(f"记忆 {i}")
        items = mgr.list_memories(limit=5)
        assert len(items) == 5

    def test_stats(self, mgr):
        mgr.add("内容 A", tags=["a"])
        mgr.add("内容 B", tags=["b"])
        mgr.add("内容 C", tags=["a"])
        stats = mgr.stats()
        assert stats["total_memories"] == 3
        assert stats["by_tag"]["a"] == 2
        assert stats["by_tag"]["b"] == 1


class TestDedup:
    """去重测试"""

    @pytest.fixture
    def mgr(self, clean_data_dir):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import memory_manager as mm_mod
        old = mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR
        mm_mod.DATA_DIR = clean_data_dir
        mm_mod.MEMORY_DIR = os.path.join(clean_data_dir, "memories")
        mm_mod.KB_DIR = os.path.join(clean_data_dir, "kb")
        os.makedirs(mm_mod.MEMORY_DIR, exist_ok=True)
        os.makedirs(mm_mod.KB_DIR, exist_ok=True)
        yield mm_mod.MemoryManager()
        mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR = old

    def test_duplicate_detected(self, mgr):
        mgr.add("今天讨论了项目进展", importance=0.8)
        result = mgr.add("今天讨论了项目进展")  # 完全相同
        assert result.startswith("dedup:")

    def test_importance_boosted_on_dedup(self, mgr):
        mid = mgr.add("重要讨论内容", importance=0.6)
        mgr.add("重要讨论内容")  # dedup
        m = mgr.get(mid)
        assert m["importance"] > 0.6


class TestKnowledgeBase:
    """知识库测试"""

    @pytest.fixture
    def mgr(self, clean_data_dir):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import memory_manager as mm_mod
        old = mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR
        mm_mod.DATA_DIR = clean_data_dir
        mm_mod.MEMORY_DIR = os.path.join(clean_data_dir, "memories")
        mm_mod.KB_DIR = os.path.join(clean_data_dir, "kb")
        os.makedirs(mm_mod.MEMORY_DIR, exist_ok=True)
        os.makedirs(mm_mod.KB_DIR, exist_ok=True)
        yield mm_mod.MemoryManager()
        mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR = old

    def test_create_and_list_kb(self, mgr):
        result = mgr.create_kb("Python笔记", description="Python学习")
        assert result["status"] == "created"

        kbs = mgr.list_kbs()
        assert len(kbs) == 1
        assert kbs[0]["name"] == "Python笔记"

    def test_add_to_kb(self, mgr):
        mgr.create_kb("笔记")
        result = mgr.add_to_kb("笔记", "Python 有丰富的标准库。")
        assert "chunks" in result

    def test_query_kb(self, mgr):
        mgr.create_kb("笔记")
        mgr.add_to_kb("笔记", "Python 是一种高级编程语言。")
        results = mgr.query_kb("笔记", "Python", top_k=3)
        assert len(results) >= 1

    def test_delete_kb(self, mgr):
        mgr.create_kb("临时笔记")
        result = mgr.delete_kb("临时笔记")
        assert result["status"] == "deleted"


class TestTextChunking:
    """文本分块测试"""

    def test_short_text_unchanged(self):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import memory_manager as mm_mod
        chunks = mm_mod.MemoryManager._chunk_text("短文本", max_chars=512)
        assert len(chunks) == 1
        assert chunks[0] == "短文本"

    def test_long_text_split(self):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import memory_manager as mm_mod
        # 制造一个超长文本
        long_text = "这是测试句子。" * 200  # 约 3000 字
        chunks = mm_mod.MemoryManager._chunk_text(long_text, max_chars=512, overlap=64)
        assert len(chunks) >= 2
        for c in chunks:
            assert len(c) <= 512 + 100  # 允许小量超出


class TestAutoForget:
    """自动遗忘测试"""

    @pytest.fixture
    def mgr(self, clean_data_dir):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import memory_manager as mm_mod
        old = mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR
        mm_mod.DATA_DIR = clean_data_dir
        mm_mod.MEMORY_DIR = os.path.join(clean_data_dir, "memories")
        mm_mod.KB_DIR = os.path.join(clean_data_dir, "kb")
        os.makedirs(mm_mod.MEMORY_DIR, exist_ok=True)
        os.makedirs(mm_mod.KB_DIR, exist_ok=True)
        yield mm_mod.MemoryManager()
        mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR = old

    def test_dry_run(self, mgr):
        """dry_run 不实际删除"""
        mgr.add("低价值记忆", importance=0.05)
        results = mgr.auto_forget(dry_run=True)
        assert len(results) >= 1

    def test_apply_forgets(self, mgr):
        """--apply 实际删除"""
        mgr.add("低价值记忆", importance=0.05)
        mgr.add("重要记忆", importance=0.9, tags=["重要"])
        results = mgr.auto_forget(dry_run=False)
        assert len(results) == 1  # 重要记忆不应被遗忘