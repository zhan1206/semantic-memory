"""doc_parser.py 单元测试"""
import pytest
import sys, os, tempfile

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))


class TestDocParserText:
    """纯文本解析测试"""

    def test_parse_utf8_txt(self):
        from doc_parser import _parse_text
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False,
                                           encoding="utf-8")
        tmp.write("第一行内容\n\n第二段内容\n这是第三行。")
        tmp.close()
        try:
            text = _parse_text(tmp.name)
            assert "第一行内容" in text
            assert "第二段内容" in text
        finally:
            os.remove(tmp.name)

    def test_parse_markdown(self):
        from doc_parser import _parse_text
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False,
                                           encoding="utf-8")
        tmp.write("# 标题\n\n这是正文。\n\n## 小节\n更多内容。")
        tmp.close()
        try:
            text = _parse_text(tmp.name)
            assert "标题" in text
            assert "正文" in text
        finally:
            os.remove(tmp.name)

    def test_parse_gbk_encoding(self):
        """GBK 编码中文文件"""
        from doc_parser import _parse_text
        # Use delete=False and manual cleanup to avoid file access issues on Linux
        tmp = tempfile.NamedTemporaryFile(mode="wb", suffix=".txt", delete=False)
        content = "这是 GBK 编码的文件内容。\n第二行。"
        tmp.write(content.encode("gbk"))
        tmp.close()
        try:
            text = _parse_text(tmp.name)
            assert "GBK" in text or "内容" in text
        finally:
            os.remove(tmp.name)


class TestDocParserUnsupported:
    """不支持的格式测试"""

    def test_unsupported_format(self):
        from doc_parser import parse_file
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".xyz", delete=False)
        tmp.write("dummy")
        tmp.close()
        try:
            with pytest.raises(ValueError, match="不支持"):
                parse_file(tmp.name)
        finally:
            os.remove(tmp.name)


class TestImportFileToKB:
    """导入文件测试"""

    @pytest.fixture
    def clean_kb_env(self, clean_data_dir):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import memory_manager as mm_mod
        old = mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR
        mm_mod.DATA_DIR = clean_data_dir
        mm_mod.MEMORY_DIR = os.path.join(clean_data_dir, "memories")
        mm_mod.KB_DIR = os.path.join(clean_data_dir, "kb")
        os.makedirs(mm_mod.MEMORY_DIR, exist_ok=True)
        os.makedirs(mm_mod.KB_DIR, exist_ok=True)
        yield
        mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR = old

    def test_import_nonexistent_file(self, clean_kb_env):
        from doc_parser import import_file_to_kb
        result = import_file_to_kb("/nonexistent/file.txt", "kb1")
        assert "error" in result

    def test_import_directory_missing(self, clean_kb_env):
        from doc_parser import import_directory_to_kb
        result = import_directory_to_kb("/nonexistent/dir", "kb1")
        assert "error" in result


class TestImportDirectoryToKB:
    """批量导入测试"""

    @pytest.fixture
    def clean_kb_env(self, clean_data_dir):
        sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))
        import memory_manager as mm_mod
        old = mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR
        mm_mod.DATA_DIR = clean_data_dir
        mm_mod.MEMORY_DIR = os.path.join(clean_data_dir, "memories")
        mm_mod.KB_DIR = os.path.join(clean_data_dir, "kb")
        os.makedirs(mm_mod.MEMORY_DIR, exist_ok=True)
        os.makedirs(mm_mod.KB_DIR, exist_ok=True)
        yield
        mm_mod.DATA_DIR, mm_mod.MEMORY_DIR, mm_mod.KB_DIR = old

    def test_import_directory_batch(self, clean_kb_env):
        from doc_parser import import_directory_to_kb
        from memory_manager import MemoryManager

        tmpdir = tempfile.mkdtemp(prefix="doc_import_")
        # 创建临时文本文件
        for i in range(3):
            fpath = os.path.join(tmpdir, f"doc{i}.txt")
            with open(fpath, "w", encoding="utf-8") as f:
                f.write(f"文档 {i} 的内容。\n这是一个测试文档。")

        try:
            mgr = MemoryManager()
            mgr.create_kb("test_kb")
            result = import_directory_to_kb(tmpdir, "test_kb")
            assert result["status"] == "batch_imported"
            assert result["success"] == 3
            assert result["failed"] == 0
        finally:
            import shutil
            shutil.rmtree(tmpdir, ignore_errors=True)