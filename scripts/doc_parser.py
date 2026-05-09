#!/usr/bin/env python3
"""
Semantic Memory — 文档解析器
支持 PDF / TXT / Markdown / DOCX 自动解析、分块
"""
import os
import re

from memory_manager import MemoryManager


def parse_file(file_path: str) -> str:
    """
    解析文档文件，返回纯文本内容
    支持: .txt, .md, .pdf, .docx
    """
    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".txt", ".md", ".markdown"):
        return _parse_text(file_path)
    elif ext == ".pdf":
        return _parse_pdf(file_path)
    elif ext in (".docx", ".doc"):
        return _parse_docx(file_path)
    else:
        raise ValueError(f"不支持的文件格式: {ext}（支持 .txt/.md/.pdf/.docx）")


def _parse_text(file_path: str) -> str:
    """解析纯文本 / Markdown 文件"""
    import chardet

    with open(file_path, "rb") as f:
        raw = f.read()

    # 自动检测编码
    detected = chardet.detect(raw)
    encoding = detected.get("encoding", "utf-8") or "utf-8"

    try:
        return raw.decode(encoding)
    except (UnicodeDecodeError, LookupError):
        return raw.decode("utf-8", errors="replace")


def _parse_pdf(file_path: str) -> str:
    """解析 PDF 文件"""
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        raise ImportError(
            "PDF 解析需要 PyPDF2 库，请运行: pip install PyPDF2"
        )

    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        if text and text.strip():
            pages.append(text.strip())

    if not pages:
        raise ValueError(f"PDF 文件无文本内容: {file_path}")

    return "\n\n".join(pages)


def _parse_docx(file_path: str) -> str:
    """解析 DOCX 文件"""
    try:
        from docx import Document
    except ImportError:
        raise ImportError(
            "DOCX 解析需要 python-docx 库，请运行: pip install python-docx"
        )

    doc = Document(file_path)
    paragraphs = []
    for para in doc.paragraphs:
        text = para.text.strip()
        if text:
            paragraphs.append(text)

    # 提取表格内容
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if cells:
                paragraphs.append(" | ".join(cells))

    if not paragraphs:
        raise ValueError(f"DOCX 文件无文本内容: {file_path}")

    return "\n\n".join(paragraphs)


def import_file_to_kb(file_path: str, kb_name: str, tags: list = None,
                       memory_manager: MemoryManager = None) -> dict:
    """
    导入文档到知识库
    file_path: 文件路径
    kb_name: 目标知识库名
    tags: 额外标签
    memory_manager: MemoryManager 实例
    """
    if not os.path.exists(file_path):
        return {"error": f"文件不存在: {file_path}"}

    # 解析文件
    try:
        text = parse_file(file_path)
    except Exception as e:
        return {"error": f"解析失败: {e}"}

    if not text.strip():
        return {"error": "文件内容为空"}

    # 添加到知识库
    if memory_manager is None:
        memory_manager = MemoryManager()

    filename = os.path.basename(file_path)
    all_tags = list(tags or [])
    all_tags.append(f"file:{filename}")

    result = memory_manager.add_to_kb(
        kb_name=kb_name,
        text=text,
        source_file=filename,
        tags=all_tags,
    )

    return {
        "status": "imported",
        "file": filename,
        "text_length": len(text),
        "result": result,
    }


def import_directory_to_kb(dir_path: str, kb_name: str, tags: list = None,
                            memory_manager: MemoryManager = None) -> dict:
    """
    批量导入目录下的文档到知识库
    支持: .txt, .md, .pdf, .docx
    """
    if not os.path.isdir(dir_path):
        return {"error": f"目录不存在: {dir_path}"}

    supported_ext = {".txt", ".md", ".markdown", ".pdf", ".docx", ".doc"}
    files = []
    for fname in os.listdir(dir_path):
        ext = os.path.splitext(fname)[1].lower()
        if ext in supported_ext:
            files.append(os.path.join(dir_path, fname))

    if not files:
        return {"error": "目录中没有支持的文件格式"}

    if memory_manager is None:
        memory_manager = MemoryManager()

    results = []
    for fpath in files:
        r = import_file_to_kb(fpath, kb_name, tags, memory_manager)
        results.append(r)

    success = sum(1 for r in results if r.get("status") == "imported")
    failed = sum(1 for r in results if "error" in r)

    return {
        "status": "batch_imported",
        "total_files": len(files),
        "success": success,
        "failed": failed,
        "details": results,
    }
