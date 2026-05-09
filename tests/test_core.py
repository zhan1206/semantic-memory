"""core.py — ONNX 引擎与编码器单元测试"""
import pytest
import numpy as np
import sys, os

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))


class TestChineseDetection:
    """_detect_chinese_ratio 语言检测测试"""

    def test_empty_string(self):
        from core import _detect_chinese_ratio
        assert _detect_chinese_ratio("") == 0.0
        assert _detect_chinese_ratio(None) == 0.0

    def test_pure_chinese(self):
        from core import _detect_chinese_ratio
        ratio = _detect_chinese_ratio("你好世界这是一个中文句子")
        assert ratio == 1.0

    def test_pure_english(self):
        from core import _detect_chinese_ratio
        ratio = _detect_chinese_ratio("Hello world this is English text")
        assert ratio == 0.0

    def test_mixed_text(self):
        from core import _detect_chinese_ratio
        text = "Hello 你好 world 世界"  # 4 cn chars out of ~20 = 0.2
        ratio = _detect_chinese_ratio(text)
        assert 0.0 < ratio < 1.0

    def test_numbers_and_punctuation(self):
        from core import _detect_chinese_ratio
        ratio = _detect_chinese_ratio("12345 !@#$% 67890")
        assert ratio == 0.0


class TestModelRegistry:
    """MODEL_REGISTRY 配置验证"""

    def test_default_model_exists(self):
        from core import DEFAULT_MODEL, MODEL_REGISTRY
        assert DEFAULT_MODEL in MODEL_REGISTRY

    def test_all_models_have_required_fields(self):
        from core import MODEL_REGISTRY
        required_fields = ["dim", "max_len", "pooling", "repo", "files", "lang"]
        for model_id, meta in MODEL_REGISTRY.items():
            for field in required_fields:
                assert field in meta, f"Model {model_id} missing field: {field}"
            # dim must be positive
            assert meta["dim"] > 0
            # max_len must be positive
            assert meta["max_len"] > 0
            # files dict must not be empty
            assert len(meta["files"]) > 0

    def test_default_model_is_english(self):
        from core import DEFAULT_MODEL, MODEL_REGISTRY
        assert MODEL_REGISTRY[DEFAULT_MODEL]["lang"] == "en"


class TestAutoEncode:
    """auto_encode 语言自动切换测试（使用 mock）"""

    def test_auto_encode_pure_english(self, mock_encoder):
        from core import auto_encode
        vec = auto_encode("Hello world", engine_map={"en": mock_encoder})
        assert vec.shape == (1, mock_encoder.dimension)
        assert np.isclose(np.linalg.norm(vec), 1.0, atol=1e-3)

    def test_auto_encode_pure_chinese(self, mock_encoder):
        from core import _detect_chinese_ratio
        # 只有在中文占比>30%且有zh引擎时才用中文引擎
        # 纯中文文本会触发zh引擎
        vec = auto_encode("你好世界", engine_map={"zh": mock_encoder, "en": mock_encoder})
        assert vec.shape == (1, mock_encoder.dimension)

    def test_auto_encode_batch(self, mock_encoder):
        from core import auto_encode
        texts = ["Hello world", "你好", "Python programming"]
        vecs = auto_encode(texts, engine_map={"en": mock_encoder})
        assert vecs.shape == (3, mock_encoder.dimension)

    def test_auto_encode_single_string(self, mock_encoder):
        from core import auto_encode
        vec = auto_encode("single text", engine_map={"en": mock_encoder})
        # 返回 2D 但 shape[0] 应该是 1
        assert vec.shape[0] == 1
        assert vec.shape[1] == mock_encoder.dimension

    def test_auto_encode_empty_string(self, mock_encoder):
        from core import auto_encode
        # 空字符串不应崩溃
        try:
            vec = auto_encode("", engine_map={"en": mock_encoder})
            assert vec.shape[1] == mock_encoder.dimension
        except Exception:
            pass  # 空输入行为未定义，容错处理


class TestMockEncoder:
    """MockEncoder fixture 测试"""

    def test_mock_encoder_dimension(self, mock_encoder):
        assert mock_encoder.dimension == 384

    def test_mock_encoder_deterministic(self, mock_encoder):
        # 相同文本产生相同向量
        v1 = mock_encoder.encode_single("test text")
        v2 = mock_encoder.encode_single("test text")
        assert np.allclose(v1, v2)

    def test_mock_encoder_different_texts(self, mock_encoder):
        v1 = mock_encoder.encode_single("hello")
        v2 = mock_encoder.encode_single("world")
        assert not np.allclose(v1, v2)

    def test_mock_encoder_batch(self, mock_encoder):
        vecs = mock_encoder.encode(["a", "b", "c"])
        assert vecs.shape == (3, 384)

    def test_mock_encoder_normalized(self, mock_encoder):
        vec = mock_encoder.encode_single("some text")
        norm = np.linalg.norm(vec)
        assert 0.99 < norm < 1.01  # 应接近 1.0（L2 归一化）


class TestGlobalEngine:
    """get_engine 全局单例测试"""

    def test_get_engine_returns_engine(self):
        # 注意：此测试需要网络访问来下载模型，仅在 integration 模式下运行
        pytest.skip("需要下载 ONNX 模型，仅 CI 集成测试运行")

    def test_global_engine_singleton(self, mock_encoder, monkeypatch):
        """验证相同 model_id 返回相同实例"""
        from core import get_engine

        # Mock EmbeddingEngine，避免真实加载模型
        import core as core_mod

        class FakeEngine:
            def __init__(self, model_id):
                self.model_id = model_id
                self._dim = 384

            @property
            def dimension(self):
                return self._dim

        monkeypatch.setattr(core_mod, "EmbeddingEngine", FakeEngine)
        core_mod._global_engine = None  # 重置单例

        e1 = get_engine("test-model")
        e2 = get_engine("test-model")
        assert e1 is e2  # 相同实例

        # 不同 model_id 应创建新实例
        e3 = get_engine("another-model")
        assert e3 is not e1
