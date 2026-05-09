#!/usr/bin/env python3
"""
Semantic Memory — 批量操作工具
用于大规模数据导入、批量编辑、批量删除等场景
"""
import os
import sys
import json
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Optional

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from memory_manager import MemoryManager
from logging import get_logger, progress_bar

logger = get_logger("batch")


def batch_add_from_file(filepath: str, tags: list[str], importance: float,
                         skip_filter: bool, dry_run: bool) -> dict:
    """从文件批量添加记忆（每行一条）"""
    if not os.path.exists(filepath):
        return {"error": f"文件不存在: {filepath}"}

    with open(filepath, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    if dry_run:
        return {"total": len(lines), "mode": "dry_run", "would_add": len(lines)}

    mgr = MemoryManager()
    success, failed, filtered, dedup = 0, 0, 0, 0

    for text in progress_bar(lines, total=len(lines), desc="批量添加"):
        result = mgr.add(text, tags=tags, importance=importance,
                        skip_filter=skip_filter)
        if result.startswith("filtered:"):
            filtered += 1
        elif result.startswith("dedup:"):
            dedup += 1
        elif "error" in result:
            failed += 1
        else:
            success += 1

    return {
        "total": len(lines),
        "success": success,
        "failed": failed,
        "filtered": filtered,
        "dedup": dedup,
    }


def batch_tag_by_id(ids: list[str], tags: list[str]) -> dict:
    """批量给指定 ID 添加标签"""
    mgr = MemoryManager()
    success, failed = 0, 0

    for mid in ids:
        if mgr.tag(mid, tags):
            success += 1
        else:
            failed += 1

    return {"success": success, "failed": failed, "total": len(ids)}


def batch_delete_by_tag(tag: str, dry_run: bool) -> dict:
    """按标签批量删除记忆"""
    mgr = MemoryManager()
    items = mgr.list_memories(tag=tag, limit=10000)

    if dry_run:
        return {"mode": "dry_run", "would_delete": len(items), "items": items[:10]}

    success, failed = 0, 0
    for item in items:
        if mgr.delete(item["id"]):
            success += 1
        else:
            failed += 1

    return {"success": success, "failed": failed, "total": len(items)}


def batch_import_directory(directory: str, kb_name: str, exts: Optional[list[str]]) -> dict:
    """批量导入目录中的文档"""
    from doc_parser import import_directory_to_kb

    if not os.path.isdir(directory):
        return {"error": f"目录不存在: {directory}"}

    if exts:
        files = []
        for root, _, filenames in os.walk(directory):
            for fname in filenames:
                if any(fname.lower().endswith(ext) for ext in exts):
                    files.append(os.path.join(root, fname))
    else:
        files = [
            os.path.join(root, f)
            for root, _, filenames in os.walk(directory)
            for f in filenames
        ]

    mgr = MemoryManager()
    mgr.create_kb(kb_name)

    success, failed = 0, 0
    errors = []

    for fpath in progress_bar(files, total=len(files), desc="导入文件"):
        try:
            from doc_parser import import_file_to_kb
            result = import_file_to_kb(fpath, kb_name)
            if "error" not in result:
                success += 1
            else:
                failed += 1
                errors.append({"file": fpath, "error": result["error"]})
        except Exception as e:
            failed += 1
            errors.append({"file": fpath, "error": str(e)})

    return {"success": success, "failed": failed, "total": len(files), "errors": errors[:20]}


def batch_export(ids: list[str], output_file: str) -> dict:
    """批量导出记忆到 JSON 文件"""
    mgr = MemoryManager()
    exported = []
    for mid in ids:
        item = mgr.get(mid)
        if item:
            exported.append(item)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(exported, f, ensure_ascii=False, indent=2)

    return {"exported": len(exported), "file": output_file}


def batch_edit(ids: list[str], text: str) -> dict:
    """批量编辑记忆内容（替换）"""
    mgr = MemoryManager()
    success, failed = 0, 0

    for mid in ids:
        if mgr.edit(mid, text):
            success += 1
        else:
            failed += 1

    return {"success": success, "failed": failed, "total": len(ids)}


# ─── CLI 入口 ───────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Semantic Memory 批量操作工具")
    sub = parser.add_subparsers(dest="command")

    # 批量添加
    add = sub.add_parser("add-file", help="从文本文件批量添加记忆")
    add.add_argument("file", help="文本文件路径（每行一条记忆）")
    add.add_argument("--tags", help="标签，逗号分隔")
    add.add_argument("--importance", type=float, default=0.5)
    add.add_argument("--skip-filter", action="store_true")
    add.add_argument("--dry-run", action="store_true")

    # 批量标签
    tag = sub.add_parser("tag", help="批量添加标签")
    tag.add_argument("ids", nargs="+", help="记忆 ID 列表")
    tag.add_argument("--tags", required=True, help="标签，逗号分隔")

    # 批量删除
    delete = sub.add_parser("delete-by-tag", help="按标签批量删除")
    delete.add_argument("tag", help="标签名")
    delete.add_argument("--dry-run", action="store_true", default=True)

    # 批量导入目录
    import_dir = sub.add_parser("import-dir", help="批量导入目录中的文档")
    import_dir.add_argument("directory", help="目录路径")
    import_dir.add_argument("kb_name", help="知识库名称")
    import_dir.add_argument("--exts", help="文件扩展名，逗号分隔，如 .txt,.md,.pdf")

    # 批量导出
    export = sub.add_parser("export", help="批量导出记忆")
    export.add_argument("ids", nargs="+", help="记忆 ID 列表")
    export.add_argument("--output", required=True, help="输出 JSON 文件路径")

    # 批量编辑
    edit = sub.add_parser("edit", help="批量编辑记忆内容")
    edit.add_argument("ids", nargs="+", help="记忆 ID 列表")
    edit.add_argument("text", help="新的记忆内容")

    args = parser.parse_args()

    if args.command == "add-file":
        tags = [t.strip() for t in (args.tags or "").split(",") if t.strip()]
        result = batch_add_from_file(args.file, tags, args.importance,
                                      args.skip_filter, args.dry_run)
        logger.info(f"结果: {result}")

    elif args.command == "tag":
        tags = [t.strip() for t in args.tags.split(",") if t.strip()]
        result = batch_tag_by_id(args.ids, tags)
        logger.info(f"标签添加结果: {result}")

    elif args.command == "delete-by-tag":
        result = batch_delete_by_tag(args.tag, args.dry_run)
        logger.info(f"删除结果: {result}")

    elif args.command == "import-dir":
        exts = [e.strip() for e in args.exts.split(",") if e.strip()] if args.exts else None
        result = batch_import_directory(args.directory, args.kb_name, exts)
        logger.info(f"导入结果: {result}")

    elif args.command == "export":
        result = batch_export(args.ids, args.output)
        logger.info(f"导出结果: {result}")

    elif args.command == "edit":
        result = batch_edit(args.ids, args.text)
        logger.info(f"编辑结果: {result}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
