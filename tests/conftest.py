#!/usr/bin/env python3
"""
pytest 配置：全局 fixtures 和测试环境隔离
"""
import os
import sys
import tempfile
import shutil
import pytest

# 将 scripts 目录加入路径，确保测试导入模块而非已安装的包
SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(SKILL_DIR, "scripts")
sys.path.insert(0, SCRIPTS_DIR)

# 测试用临时数据目录（pytest fixtures 提供）
@pytest.fixture(scope="session")
def mock_data_dir():
    """Session 级临时目录，所有测试共享"""
    tmp = tempfile.mkdtemp(prefix="sm_test_")
    yield tmp
    shutil.rmtree(tmp, ignore_errors=True)


@pytest.fixture
def clean_data_dir(mock_data_dir):
    """每个测试函数独立的干净子目录"""
    sub = os.path.join(mock_data_dir, os.urandom(8).hex())
    os.makedirs(sub, exist_ok=True)
    yield sub
    shutil.rmtree(sub, ignore_errors=True)


@pytest.fixture(autouse=True)
def patch_data_dir(monkeypatch, clean_data_dir):
    """自动将所有模块的 DATA_DIR 指向测试临时目录"""
    # 找到所有已加载模块，patch 它们的 DATA_DIR
    for mod_name in list(sys.modules.keys()):
        if mod_name in ("core", "vector_store", "memory_manager", "config"):
            mod = sys.modules.get(mod_name)
            if mod and hasattr(mod, "DATA_DIR"):
                monkeypatch.setattr(mod, "DATA_DIR", clean_data_dir)
            # 重新设置子目录
            for sub in ("memories", "kb", "models"):
                path = os.path.join(clean_data_dir, sub)
                os.makedirs(path, exist_ok=True)
                if hasattr(mod, sub.upper() + "_DIR"):
                    monkeypatch.setattr(mod, sub.upper() + "_DIR", path)


@pytest.fixture
def sample_texts():
    """标准测试文本集"""
    return {
        "cn_short": "今天和张三讨论了AI项目进展，效果很好。",
        "cn_long": "Python 是一种广泛使用的高级编程语言，由 Guido van Rossum 于1991年首次发布。它强调代码的可读性，使用缩进作为语句分组的方法。Python 支持多种编程范式，包括结构化、过程式、反射式、面向对象和函数式编程。它拥有庞大而全面的标准库，通常被称为'batteries included'。",
        "en_short": "The weather is nice today.",
        "en_long": "Machine learning is a subset of artificial intelligence that enables systems to learn and improve from experience without being explicitly programmed. It focuses on developing computer programs that can access data and use it to learn for themselves. The process of learning begins with observations or data, such as examples, direct experience, or instruction, in order to look for patterns in data and make better decisions in the future based on the examples that we provide.",
        "api_key": "sk-abc123def456ghi789jkl012mno345pqr678stuv901wxyz",
        "password": "密码是 MyP@ssw0rd123，请勿泄露",
        "id_card": "身份证号 110101199001011234 银行卡 6222021234567890123",
    }


@pytest.fixture
def mock_encoder():
    """模拟的 Embedding 引擎（返回确定性向量）"""
    import numpy as np
    class MockEncoder:
        def __init__(self):
            self.model_id = "mock-model"
            self._dim = 384

        @property
        def dimension(self):
            return self._dim

        def encode(self, texts):
            if isinstance(texts, str):
                texts = [texts]
            # 简单的词袋哈希向量（确定性）
            import hashlib
            vectors = []
            for t in texts:
                vec = np.zeros(self._dim, dtype=np.float32)
                words = t.replace(" ", "").replace("\n", "")
                for i, c in enumerate(words[:100]):
                    h = int(hashlib.md5((c + str(i)).encode()).hexdigest(), 16)
                    vec[h % self._dim] += 1
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec = vec / norm
                vectors.append(vec)
            # Always return 2D array (N, dim)
            return np.vstack(vectors).astype(np.float32) if len(vectors) > 1 else np.array([vectors[0]], dtype=np.float32)

        def encode_single(self, text):
            return self.encode(text)

    return MockEncoder()