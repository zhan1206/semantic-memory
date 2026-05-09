#!/usr/bin/env python3
"""
Semantic Memory — CLI 入口
用法:
  python run.py add <内容> [--tags 标签1,标签2] [--importance 0.8]
  python run.py search <查询> [--top-k 5] [--tag 标签] [--kb 知识库名]
  python run.py recall <查询> [--top-k 5] [--max-chars 3000]
  python run.py list [--tag 标签] [--limit 50] [--sort timestamp|importance]
  python run.py get <记忆ID>
  python run.py tag <记忆ID> <标签1,标签2>
  python run.py importance <记忆ID> <0.0-1.0>
  python run.py edit <记忆ID> <新内容>
  python run.py delete <记忆ID>
  python run.py stats
  python run.py forget [--apply]
  python run.py clear --confirm
  python run.py encrypt <密码>
  python run.py unlock <密码>
  python run.py kb create <名称> [--desc 描述]
  python run.py kb list
  python run.py kb add <知识库名> <文件路径> [--tags 标签]
  python run.py kb query <知识库名> <问题> [--top-k 5]
  python run.py kb delete <知识库名>
  python run.py import <文件路径> --kb <知识库名> [--tags 标签]
  python run.py import-dir <目录路径> --kb <知识库名> [--tags 标签]
  python run.py config get [key]
  python run.py config set <key> <value>
  python run.py config reset
  python run.py metrics
  python run.py --interactive        # 交互式菜单模式
"""
import sys
import os
import json
import argparse

# ─── 彩色输出（内联，无依赖） ───────────────────────────────
try:
    from logging import CLIOutput as _out
    _USE_LOGGING = True
except ImportError:
    _USE_LOGGING = False
    _NO_COLOR = os.environ.get("NO_COLOR", "") or os.environ.get("TERM", "") == "dumb"
    _C = {
        "reset": "\033[0m", "bold": "\033[1m",
        "red": "\033[91m", "green": "\033[92m",
        "yellow": "\033[93m", "blue": "\033[94m",
        "cyan": "\033[96m", "gray": "\033[90m",
    }
    def _c(code, text):
        return f"{_C.get(code,'')}{text}{_C['reset']}" if not _NO_COLOR else text
    class _out:
        @staticmethod
        def ok(msg): print(_c("green", f"✓ {msg}"))
        @staticmethod
        def info(msg): print(_c("blue", f"ℹ {msg}"))
        @staticmethod
        def warn(msg): print(_c("yellow", f"⚠ {msg}"))
        @staticmethod
        def error(msg): print(_c("red", f"✗ {msg}"), file=sys.stderr)
        @staticmethod
        def header(msg):
            sep = _c("bold", "━" * 50)
            print(f"\n{sep}\n  {_c('bold', msg)}\n{sep}")

# Force UTF-8 output on Windows (prevent GBK encoding issues)
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 确保 scripts/ 在 import 路径中
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)


def _json_output(data):
    """统一 JSON 输出"""
    print(json.dumps(data, ensure_ascii=False, indent=2))


def cmd_add(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    tags = args.tags.split(",") if args.tags else []
    mid = mgr.add(args.text, tags=tags, importance=args.importance)
    _json_output({"status": "added", "id": mid})


def cmd_search(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    results = mgr.search(args.query, top_k=args.top_k, tag=args.tag, kb_name=args.kb)
    _json_output({"results": results, "count": len(results)})


def cmd_recall(args):
    """
    语义召回 + 上下文格式化
    输出格式化的上下文文本，可直接注入到对话上下文中
    支持 --max-chars 控制注入文本总长度（上下文窗口适配）
    """
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    results = mgr.search(args.query, top_k=args.top_k, tag=args.tag, kb_name=args.kb)

    if not results:
        _json_output({"context": "", "count": 0, "total_chars": 0})
        return

    # 上下文窗口预算适配
    max_chars = args.max_chars or 3000
    context_lines = []
    total_chars = 0

    for i, m in enumerate(results):
        text = m.get("text", "")
        tags = ",".join(m.get("tags", []))
        imp = m.get("effective_importance", m.get("importance", 0))
        line = f"[{i+1}] (importance:{imp:.2f}, tags:{tags}) {text}"

        if total_chars + len(line) > max_chars:
            break

        context_lines.append(line)
        total_chars += len(line)

    context = "\n".join(context_lines)
    _json_output({
        "context": context,
        "count": len(context_lines),
        "total_chars": total_chars,
        "truncated": len(context_lines) < len(results),
    })


def cmd_list(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    items = mgr.list_memories(tag=args.tag, limit=args.limit, sort_by=args.sort)
    _json_output({"items": items, "count": len(items)})


def cmd_get(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    result = mgr.get(args.id)
    if result:
        _json_output(result)
    else:
        _json_output({"error": f"记忆 {args.id} 不存在"})


def cmd_tag(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    tags = args.tags.split(",")
    ok = mgr.tag(args.id, tags)
    _json_output({"status": "tagged" if ok else "not_found"})


def cmd_importance(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    ok = mgr.set_importance(args.id, args.value)
    _json_output({"status": "updated" if ok else "not_found"})


def cmd_edit(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    ok = mgr.edit(args.id, args.text)
    _json_output({"status": "edited" if ok else "not_found"})


def cmd_delete(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    ok = mgr.delete(args.id)
    _json_output({"status": "deleted" if ok else "not_found"})


def cmd_stats(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    _json_output(mgr.stats())


def cmd_forget(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    results = mgr.auto_forget(dry_run=not args.apply)
    _json_output({
        "mode": "apply" if args.apply else "dry_run",
        "forgotten_count": len(results),
        "items": results[:20],
    })


def cmd_clear(args):
    if not args.confirm:
        _json_output({"error": "需要 --confirm 确认清空"})
        return
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    ok = mgr.clear(confirm=True)
    _json_output({"status": "cleared" if ok else "failed"})


def cmd_encrypt(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    _json_output(mgr.encrypt(args.password))


def cmd_unlock(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    _json_output(mgr.unlock(args.password))


def cmd_kb_create(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    _json_output(mgr.create_kb(args.name, description=args.desc or ""))


def cmd_kb_list(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    _json_output(mgr.list_kbs())


def cmd_kb_add(args):
    from doc_parser import import_file_to_kb
    tags = args.tags.split(",") if args.tags else []
    _json_output(import_file_to_kb(args.file, args.name, tags=tags))


def cmd_kb_query(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    results = mgr.query_kb(args.name, args.question, top_k=args.top_k)
    _json_output({"results": results, "count": len(results)})


def cmd_kb_delete(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    _json_output(mgr.delete_kb(args.name))


def cmd_import(args):
    from doc_parser import import_file_to_kb
    tags = args.tags.split(",") if args.tags else []
    _json_output(import_file_to_kb(args.file, args.kb, tags=tags))


def cmd_import_dir(args):
    from doc_parser import import_directory_to_kb
    tags = args.tags.split(",") if args.tags else []
    _json_output(import_directory_to_kb(args.dir, args.kb, tags=tags))


def cmd_config_get(args):
    from config import get_config, load_config
    if args.key:
        val = get_config(args.key)
        _json_output({"key": args.key, "value": val})
    else:
        _json_output(load_config())


def cmd_config_set(args):
    from config import set_config
    import json as _json
    # 自动类型转换
    try:
        val = _json.loads(args.value)
    except (_json.JSONDecodeError, ValueError):
        val = args.value
    result = set_config(args.key, val)
    _json_output({"status": "updated", "key": args.key, "value": result.get(args.key)})


def cmd_config_reset(args):
    from config import reset_config
    result = reset_config()
    _json_output({"status": "reset", "config": result})


def cmd_metrics(args):
    from memory_manager import MemoryManager
    mgr = MemoryManager()
    stats = mgr.stats()
    metrics = stats.get("metrics", {})
    _json_output(metrics)


def main():
    parser = argparse.ArgumentParser(
        description="Semantic Memory — OpenClaw 本地记忆与语义检索"
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="启动交互式菜单模式"
    )
    parser.add_argument(
        "--color", choices=["auto", "always", "never"], default="auto",
        help="控制彩色输出（默认 auto）"
    )
    sub = parser.add_subparsers(dest="command")

    # ─── 记忆命令 ─────────────────────────────────────────
    p_add = sub.add_parser("add", help="添加记忆")
    p_add.add_argument("text", help="记忆内容")
    p_add.add_argument("--tags", help="标签，逗号分隔")
    p_add.add_argument("--importance", type=float, default=0.5, help="重要性 0.0-1.0")
    p_add.set_defaults(func=cmd_add)

    p_search = sub.add_parser("search", help="语义搜索记忆")
    p_search.add_argument("query", help="查询文本")
    p_search.add_argument("--top-k", type=int, default=5)
    p_search.add_argument("--tag", help="按标签过滤")
    p_search.add_argument("--kb", help="在指定知识库中搜索")
    p_search.set_defaults(func=cmd_search)

    p_recall = sub.add_parser("recall", help="语义召回并格式化为上下文文本")
    p_recall.add_argument("query", help="查询文本")
    p_recall.add_argument("--top-k", type=int, default=5)
    p_recall.add_argument("--tag", help="按标签过滤")
    p_recall.add_argument("--kb", help="在指定知识库中搜索")
    p_recall.add_argument("--max-chars", type=int, default=3000, help="上下文窗口字符预算")
    p_recall.set_defaults(func=cmd_recall)

    p_list = sub.add_parser("list", help="列出记忆")
    p_list.add_argument("--tag", help="按标签过滤")
    p_list.add_argument("--limit", type=int, default=50)
    p_list.add_argument("--sort", default="timestamp", choices=["timestamp", "importance"])
    p_list.set_defaults(func=cmd_list)

    p_get = sub.add_parser("get", help="获取单条记忆")
    p_get.add_argument("id", help="记忆ID")
    p_get.set_defaults(func=cmd_get)

    p_tag = sub.add_parser("tag", help="添加标签")
    p_tag.add_argument("id", help="记忆ID")
    p_tag.add_argument("tags", help="标签，逗号分隔")
    p_tag.set_defaults(func=cmd_tag)

    p_imp = sub.add_parser("importance", help="设置重要性")
    p_imp.add_argument("id", help="记忆ID")
    p_imp.add_argument("value", type=float, help="重要性 0.0-1.0")
    p_imp.set_defaults(func=cmd_importance)

    p_edit = sub.add_parser("edit", help="编辑记忆")
    p_edit.add_argument("id", help="记忆ID")
    p_edit.add_argument("text", help="新内容")
    p_edit.set_defaults(func=cmd_edit)

    p_del = sub.add_parser("delete", help="删除记忆")
    p_del.add_argument("id", help="记忆ID")
    p_del.set_defaults(func=cmd_delete)

    p_stats = sub.add_parser("stats", help="记忆统计")
    p_stats.set_defaults(func=cmd_stats)

    p_forget = sub.add_parser("forget", help="自动遗忘低价值记忆")
    p_forget.add_argument("--apply", action="store_true", help="实际执行（默认 dry-run）")
    p_forget.set_defaults(func=cmd_forget)

    p_clear = sub.add_parser("clear", help="清空所有记忆")
    p_clear.add_argument("--confirm", action="store_true", help="确认清空")
    p_clear.set_defaults(func=cmd_clear)

    p_enc = sub.add_parser("encrypt", help="加密记忆库")
    p_enc.add_argument("password", help="加密密码")
    p_enc.set_defaults(func=cmd_encrypt)

    p_unlock = sub.add_parser("unlock", help="解密记忆库")
    p_unlock.add_argument("password", help="解密密码")
    p_unlock.set_defaults(func=cmd_unlock)

    # ─── 知识库命令 ───────────────────────────────────────
    p_kb = sub.add_parser("kb", help="知识库操作")
    kb_sub = p_kb.add_subparsers(dest="kb_command")

    kb_create = kb_sub.add_parser("create", help="创建知识库")
    kb_create.add_argument("name", help="知识库名称")
    kb_create.add_argument("--desc", help="描述")
    kb_create.set_defaults(func=cmd_kb_create)

    kb_list = kb_sub.add_parser("list", help="列出知识库")
    kb_list.set_defaults(func=cmd_kb_list)

    kb_add = kb_sub.add_parser("add", help="添加文档到知识库")
    kb_add.add_argument("name", help="知识库名称")
    kb_add.add_argument("file", help="文件路径")
    kb_add.add_argument("--tags", help="标签，逗号分隔")
    kb_add.set_defaults(func=cmd_kb_add)

    kb_query = kb_sub.add_parser("query", help="查询知识库")
    kb_query.add_argument("name", help="知识库名称")
    kb_query.add_argument("question", help="问题")
    kb_query.add_argument("--top-k", type=int, default=5)
    kb_query.set_defaults(func=cmd_kb_query)

    kb_del = kb_sub.add_parser("delete", help="删除知识库")
    kb_del.add_argument("name", help="知识库名称")
    kb_del.set_defaults(func=cmd_kb_delete)

    # ─── 导入命令 ─────────────────────────────────────────
    p_import = sub.add_parser("import", help="导入文件到知识库")
    p_import.add_argument("file", help="文件路径")
    p_import.add_argument("--kb", required=True, help="目标知识库名")
    p_import.add_argument("--tags", help="标签，逗号分隔")
    p_import.set_defaults(func=cmd_import)

    p_import_dir = sub.add_parser("import-dir", help="批量导入目录到知识库")
    p_import_dir.add_argument("dir", help="目录路径")
    p_import_dir.add_argument("--kb", required=True, help="目标知识库名")
    p_import_dir.add_argument("--tags", help="标签，逗号分隔")
    p_import_dir.set_defaults(func=cmd_import_dir)

    # ─── 配置命令 ────────────────────────────────────────────
    p_config = sub.add_parser("config", help="配置管理")
    config_sub = p_config.add_subparsers(dest="config_command")

    config_get = config_sub.add_parser("get", help="获取配置")
    config_get.add_argument("key", nargs="?", help="配置键名（空则显示全部）")
    config_get.set_defaults(func=cmd_config_get)

    config_set = config_sub.add_parser("set", help="设置配置")
    config_set.add_argument("key", help="配置键名")
    config_set.add_argument("value", help="配置值（自动识别类型）")
    config_set.set_defaults(func=cmd_config_set)

    config_reset = config_sub.add_parser("reset", help="重置为默认配置")
    config_reset.set_defaults(func=cmd_config_reset)

    # ─── 性能监控 ────────────────────────────────────────────
    p_metrics = sub.add_parser("metrics", help="查看性能指标")
    p_metrics.set_defaults(func=cmd_metrics)

    args = parser.parse_args()

    # 交互模式
    if getattr(args, "interactive", False):
        try:
            from interactive import main as interactive_main
            interactive_main()
        except ImportError:
            _out.error("交互模式不可用，请安装完整依赖: pip install -e .[all]")
            sys.exit(1)
        return

    if not args.command:
        parser.print_help()
        print("\n提示: 使用 --interactive 或 -i 启动交互式菜单")
        sys.exit(0)

    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
