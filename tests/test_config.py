"""config.py 单元测试"""
import pytest
import sys, os, json, tempfile, shutil

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))


class TestConfigDefaults:
    """测试默认配置"""

    def test_load_defaults(self):
        # Patch CONFIG_PATH to a temp file that doesn't exist
        from config import load_config, DEFAULTS, CONFIG_PATH, _reset_module
        _reset_module() if hasattr(sys.modules["config"], "_reset_module") else None

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp.close()
        os.remove(tmp.name)

        # Patch the module
        import config as config_mod
        old_path = config_mod.CONFIG_PATH
        config_mod.CONFIG_PATH = tmp.name

        try:
            cfg = config_mod.load_config()
            # Check key defaults
            assert cfg["model_id"] == "all-MiniLM-L6-v2"
            assert cfg["chunk_max_chars"] == 512
            assert cfg["search_top_k"] == 5
            assert cfg["search_min_score"] == 0.2
            assert cfg["half_life_days"] == 30
            assert cfg["min_importance"] == 0.1
            assert cfg["dedup_enabled"] is True
            assert cfg["dedup_threshold"] == 0.95
            assert cfg["sensitive_filter_enabled"] is True
            assert cfg["metrics_enabled"] is True
        finally:
            config_mod.CONFIG_PATH = old_path
            if os.path.exists(tmp.name):
                os.remove(tmp.name)

    def test_defaults_are_complete(self):
        from config import DEFAULTS
        required_keys = [
            "model_id", "chunk_max_chars", "chunk_overlap",
            "search_top_k", "search_min_score",
            "half_life_days", "min_importance",
            "dedup_enabled", "dedup_threshold",
            "sensitive_filter_enabled", "metrics_enabled",
        ]
        for key in required_keys:
            assert key in DEFAULTS, f"Missing default key: {key}"


class TestConfigPersistence:
    """测试配置的持久化"""

    def test_save_only_diffs(self):
        import config as config_mod

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp_path = tmp.name
        tmp.close()

        old_path = config_mod.CONFIG_PATH
        config_mod.CONFIG_PATH = tmp_path
        try:
            # Save a config with only one change
            config_mod.save_config({"model_id": "bge-small-zh-v1.5"})

            with open(tmp_path, "r", encoding="utf-8") as f:
                saved = json.load(f)

            # Only the changed key should be saved
            assert "model_id" in saved
            assert saved["model_id"] == "bge-small-zh-v1.5"
            # Other defaults should not be saved
            assert "chunk_max_chars" not in saved
        finally:
            config_mod.CONFIG_PATH = old_path
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_set_get_single_key(self):
        import config as config_mod

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp_path = tmp.name
        tmp.close()

        old_path = config_mod.CONFIG_PATH
        config_mod.CONFIG_PATH = tmp_path
        try:
            config_mod.set_config("search_min_score", 0.5)
            val = config_mod.get_config("search_min_score")
            assert val == 0.5

            # Type coercion: string "true" → bool True
            config_mod.set_config("dedup_enabled", "true")
            val = config_mod.get_config("dedup_enabled")
            assert val is True
        finally:
            config_mod.CONFIG_PATH = old_path
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_reset_config(self):
        import config as config_mod

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp_path = tmp.name
        tmp.close()

        old_path = config_mod.CONFIG_PATH
        config_mod.CONFIG_PATH = tmp_path
        try:
            # Set a custom value
            config_mod.set_config("chunk_max_chars", 2048)
            assert config_mod.get_config("chunk_max_chars") == 2048

            # Reset
            config_mod.reset_config()
            assert config_mod.get_config("chunk_max_chars") == 512

            # Config file should be deleted
            assert not os.path.exists(tmp_path)
        finally:
            config_mod.CONFIG_PATH = old_path
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    def test_reset_nonexistent(self):
        import config as config_mod

        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp_path = tmp.name
        tmp.close()

        old_path = config_mod.CONFIG_PATH
        config_mod.CONFIG_PATH = tmp_path
        os.remove(tmp_path)
        try:
            result = config_mod.reset_config()
            assert result["chunk_max_chars"] == 512
        finally:
            config_mod.CONFIG_PATH = old_path


class TestConfigEdgeCases:
    """边界情况"""

    def test_missing_file_returns_defaults(self):
        import config as config_mod
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp_path = tmp.name
        tmp.close()
        os.remove(tmp_path)

        old_path = config_mod.CONFIG_PATH
        config_mod.CONFIG_PATH = tmp_path
        try:
            cfg = config_mod.load_config()
            assert cfg["model_id"] == "all-MiniLM-L6-v2"
        finally:
            config_mod.CONFIG_PATH = old_path

    def test_corrupted_json_returns_defaults(self):
        import config as config_mod
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)
        tmp_path = tmp.name
        tmp.close()

        old_path = config_mod.CONFIG_PATH
        config_mod.CONFIG_PATH = tmp_path
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write("{ invalid json }")

            # Should not raise, should fall back to defaults
            cfg = config_mod.load_config()
            assert cfg["model_id"] == "all-MiniLM-L6-v2"
        finally:
            config_mod.CONFIG_PATH = old_path
            if os.path.exists(tmp_path):
                os.remove(tmp_path)