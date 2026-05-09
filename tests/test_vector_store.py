"""vector_store.py 单元测试"""
import pytest
import numpy as np
import sys, os, json, tempfile, shutil

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))


class TestVectorStoreBasic:
    """基础 CRUD 测试"""

    @pytest.fixture
    def vs(self, clean_data_dir):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        # Patch DATA_DIR in vector_store module
        import vector_store as vs_mod
        old_data_dir = vs_mod.DATA_DIR
        vs_mod.DATA_DIR = clean_data_dir

        store_dir = os.path.join(clean_data_dir, "memories_test")
        os.makedirs(store_dir, exist_ok=True)
        vs = vs_mod.VectorStore(store_dir, dim=384)
        yield vs

        vs_mod.DATA_DIR = old_data_dir

    def test_add_and_get(self, vs):
        vec = np.random.randn(384).astype(np.float32)
        vec = vec / np.linalg.norm(vec)

        vs.add("mem1", vec, {"text": "test memory", "tags": ["test"]})
        vs.save()

        meta = vs.get_meta("mem1")
        assert meta is not None
        assert meta["text"] == "test memory"
        assert meta["tags"] == ["test"]

    def test_search(self, vs):
        # 添加多个向量
        base = np.random.randn(384).astype(np.float32)
        base = base / np.linalg.norm(base)

        # 第一个向量相关度高
        v1 = base + np.random.randn(384).astype(np.float32) * 0.1
        v1 = v1 / np.linalg.norm(v1)
        vs.add("mem1", v1, {"text": "关于 Python 编程语言"})

        # 第二个向量相关度低
        v2 = np.random.randn(384).astype(np.float32)
        v2 = v2 / np.linalg.norm(v2)
        vs.add("mem2", v2, {"text": "完全不相关的内容"})

        results = vs.search(base, top_k=1)
        assert len(results) == 1
        assert results[0][0] == "mem1"

    def test_delete(self, vs):
        vec = np.random.randn(384).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        vs.add("mem1", vec, {"text": "to delete"})
        vs.save()

        ok = vs.delete("mem1")
        assert ok is True
        assert vs.get_meta("mem1") is None

    def test_update(self, vs):
        vec = np.random.randn(384).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        vs.add("mem1", vec, {"text": "original"})

        new_vec = np.random.randn(384).astype(np.float32)
        new_vec = new_vec / np.linalg.norm(new_vec)
        vs.update("mem1", new_vec, {"text": "updated"})

        meta = vs.get_meta("mem1")
        assert meta["text"] == "updated"

    def test_clear(self, vs):
        vec = np.random.randn(384).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        vs.add("mem1", vec, {})
        vs.add("mem2", vec, {})
        vs.save()

        vs.clear()
        assert vs.count == 0

    def test_filter_by_tag(self, vs):
        base = np.random.randn(384).astype(np.float32)
        base = base / np.linalg.norm(base)

        for i in range(5):
            v = base + np.random.randn(384).astype(np.float32) * 0.2
            v = v / np.linalg.norm(v)
            tags = ["work"] if i < 2 else ["personal"]
            vs.add(f"mem{i}", v, {"text": f"memory {i}", "tags": tags})

        def filter_work(meta):
            return "work" in meta.get("tags", [])

        results = vs.search(base, top_k=10, filter_fn=filter_work)
        assert all("work" in r[2]["tags"] for r in results)


class TestVectorStorePersistence:
    """持久化测试"""

    def test_save_and_reload(self):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import vector_store as vs_mod

        tmp = tempfile.mkdtemp(prefix="vs_persist_")
        store_dir = os.path.join(tmp, "mem")
        os.makedirs(store_dir)

        # 写入
        vs1 = vs_mod.VectorStore(store_dir, dim=384)
        vec = np.random.randn(384).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        vs1.add("mem1", vec, {"text": "persisted"})
        vs1.save()

        # 重新加载
        vs2 = vs_mod.VectorStore(store_dir, dim=384)
        assert vs2.count == 1
        assert vs2.get_meta("mem1")["text"] == "persisted"

        shutil.rmtree(tmp, ignore_errors=True)

    def test_unicode_path(self):
        """中文路径支持（Windows）"""
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import vector_store as vs_mod

        tmp = tempfile.mkdtemp(prefix="语义_")
        store_dir = os.path.join(tmp, "记忆库")
        os.makedirs(store_dir)

        vs = vs_mod.VectorStore(store_dir, dim=384)
        vec = np.random.randn(384).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        vs.add("mem1", vec, {"text": "中文内容测试"})
        vs.save()

        # 重新加载
        vs2 = vs_mod.VectorStore(store_dir, dim=384)
        assert vs2.get_meta("mem1")["text"] == "中文内容测试"

        shutil.rmtree(tmp, ignore_errors=True)


class TestVectorStoreEdgeCases:
    """边界情况"""

    def test_search_empty_index(self):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import vector_store as vs_mod
        tmp = tempfile.mkdtemp(prefix="vs_empty_")
        store_dir = os.path.join(tmp, "mem")
        os.makedirs(store_dir)

        vs = vs_mod.VectorStore(store_dir, dim=384)
        vec = np.random.randn(384).astype(np.float32)
        vec = vec / np.linalg.norm(vec)
        results = vs.search(vec, top_k=5)
        assert results == []

        shutil.rmtree(tmp, ignore_errors=True)

    def test_delete_nonexistent(self):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import vector_store as vs_mod
        tmp = tempfile.mkdtemp()
        store_dir = os.path.join(tmp, "mem")
        os.makedirs(store_dir)

        vs = vs_mod.VectorStore(store_dir, dim=384)
        ok = vs.delete("nonexistent_id")
        assert ok is False

        shutil.rmtree(tmp, ignore_errors=True)

    def test_list_all_with_limit(self):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import vector_store as vs_mod
        tmp = tempfile.mkdtemp()
        store_dir = os.path.join(tmp, "mem")
        os.makedirs(store_dir)

        vs = vs_mod.VectorStore(store_dir, dim=384)
        for i in range(20):
            vec = np.random.randn(384).astype(np.float32)
            vec = vec / np.linalg.norm(vec)
            vs.add(f"mem{i}", vec, {"text": f"mem {i}"})

        all_items = vs.list_all(limit=5)
        assert len(all_items) == 5

        shutil.rmtree(tmp, ignore_errors=True)