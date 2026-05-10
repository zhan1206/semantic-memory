#!/usr/bin/env python3
"""
Semantic Memory — 交互式 CLI 模式
提供交互式菜单界面，适合不想记命令的用户
"""
from __future__ import annotations
import os
import sys

SKILL_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(SKILL_DIR, "scripts"))

from memory_manager import MemoryManager
from config import load_config, get_config, set_config
from app_logging import CLIOutput as out


def _banner():
    out.header("Semantic Memory — 交互模式")


def _wait():
    input(f"\n{out.gray('按 Enter 继续...')}")


class InteractiveMemory:
    """记忆管理交互界面"""

    def __init__(self):
        self.mgr = MemoryManager()

    def run(self):
        while True:
            print()
            out.header("📚 记忆管理")
            print("  1. 添加记忆")
            print("  2. 语义搜索")
            print("  3. 语义召回（构建上下文）")
            print("  4. 查看最近记忆")
            print("  5. 查看统计")
            print("  6. 自动遗忘管理")
            print("  7. 返回主菜单")

            choice = input("\n请选择 [1-7]: ").strip()
            if choice == "1":
                self._add()
            elif choice == "2":
                self._search()
            elif choice == "3":
                self._recall()
            elif choice == "4":
                self._list()
            elif choice == "5":
                self._stats()
            elif choice == "6":
                self._forget()
            elif choice == "7":
                break

    def _add(self):
        print()
        text = input("记忆内容: ").strip()
        if not text:
            out.error("内容不能为空")
            return

        tags_raw = input("标签（逗号分隔，可跳过）: ").strip()
        tags = [t.strip() for t in tags_raw.split(",") if t.strip()]

        imp_raw = input("重要性 0.0-1.0（默认 0.5）: ").strip()
        importance = float(imp_raw) if imp_raw else 0.5

        result = self.mgr.add(text, tags=tags, importance=importance)
        if result.startswith("filtered:"):
            out.error("记忆被敏感信息过滤器拦截")
        elif result.startswith("dedup:"):
            out.warn(f"重复记忆，已更新原记忆: {result.split(':', 1)[1]}")
        else:
            out.ok(f"已添加记忆: {result}")

    def _search(self):
        print()
        query = input("查询内容: ").strip()
        if not query:
            out.error("查询内容不能为空")
            return

        top_k_raw = input("返回数量（默认 5）: ").strip()
        top_k = int(top_k_raw) if top_k_raw else 5

        results = self.mgr.search(query, top_k=top_k)
        print(f"\n找到 {len(results)} 条相关记忆:\n")

        for i, r in enumerate(results, 1):
            score = r.get("score", 0)
            text = r["text"]
            tags = r.get("tags", [])
            imp = r.get("importance", 0)
            print(f"  [{i}] (相似度 {score:.2f} | 重要 {imp:.1f} | 标签 {tags})")
            print(f"      {text[:100]}{'...' if len(text) > 100 else ''}")
            print()

        if not results:
            out.info("未找到相关记忆")

    def _recall(self):
        print()
        query = input("查询内容: ").strip()
        if not query:
            out.error("查询内容不能为空")
            return

        max_chars_raw = input("最大字符数（默认 2000）: ").strip()
        max_chars = int(max_chars_raw) if max_chars_raw else 2000

        results = self.mgr.search(query, top_k=20)

        context_parts = []
        total = 0
        for r in results:
            text = r["text"]
            if total + len(text) + 3 > max_chars:
                break
            context_parts.append(f"[{r['id']}] {text}")
            total += len(text) + 3

        context = "\n".join(context_parts)
        print(f"\n{'═' * 50}")
        print(context)
        print(f"{'═' * 50}")
        print(f"\n共 {len(context_parts)} 条记忆，{total} 字符")

    def _list(self):
        print()
        limit_raw = input("查看数量（默认 10）: ").strip()
        limit = int(limit_raw) if limit_raw else 10

        items = self.mgr.list_memories(limit=limit)
        print(f"\n最近 {len(items)} 条记忆:\n")
        out.table(["ID", "重要性", "标签", "内容预览"], [
            [r["id"][:12], f"{r.get('importance', 0):.1f}",
             ",".join(r.get("tags", [])), r["text"][:40] + ("..." if len(r["text"]) > 40 else "")]
            for r in items
        ])

    def _stats(self):
        print()
        stats = self.mgr.stats()
        print("📊 统计信息:")
        print(f"  总记忆数: {stats['total_memories']}")
        print(f"  知识库数: {stats['total_kbs']}")
        if stats.get("by_tag"):
            print("  标签分布:")
            for tag, count in sorted(stats["by_tag"].items(), key=lambda x: -x[1]):
                print(f"    {tag}: {count}")

    def _forget(self):
        print()
        results = self.mgr.auto_forget(dry_run=True)
        print(f"将遗忘 {len(results)} 条低价值记忆:")
        for r in results[:10]:
            print(f"  - {r['text'][:60]}...")
        if len(results) > 10:
            print(f"  ... 还有 {len(results) - 10} 条")

        confirm = input("\n确认遗忘？（输入 'yes' 确认）: ").strip()
        if confirm.lower() == "yes":
            applied = self.mgr.auto_forget(dry_run=False)
            out.ok(f"已遗忘 {len(applied)} 条记忆")
        else:
            out.info("已取消")


class InteractiveKB:
    """知识库交互界面"""

    def __init__(self):
        self.mgr = MemoryManager()

    def run(self):
        while True:
            print()
            out.header("📖 知识库管理")
            kbs = self.mgr.list_kbs()
            print(f"  当前知识库数量: {len(kbs)}")
            for kb in kbs:
                print(f"  - {kb['name']}: {kb.get('doc_count', 0)} 文档")
            print()
            print("  1. 创建知识库")
            print("  2. 删除知识库")
            print("  3. 添加文档")
            print("  4. 查询知识库")
            print("  5. 返回主菜单")

            choice = input("\n请选择 [1-5]: ").strip()
            if choice == "1":
                self._create()
            elif choice == "2":
                self._delete()
            elif choice == "3":
                self._add()
            elif choice == "4":
                self._query()
            elif choice == "5":
                break

    def _create(self):
        name = input("知识库名称: ").strip()
        desc = input("描述（可选）: ").strip()
        if not name:
            out.error("名称不能为空")
            return
        result = self.mgr.create_kb(name, description=desc)
        if "error" in result:
            out.error(result["error"])
        else:
            out.ok(f"知识库 '{name}' 创建成功")

    def _delete(self):
        kbs = self.mgr.list_kbs()
        if not kbs:
            out.info("暂无可删除的知识库")
            return
        name = input("知识库名称: ").strip()
        confirm = input(f"确认删除 '{name}'？（输入 'yes' 确认）: ").strip()
        if confirm.lower() == "yes":
            result = self.mgr.delete_kb(name)
            if "error" in result:
                out.error(result["error"])
            else:
                out.ok(f"已删除知识库: {name}")

    def _add(self):
        kb_name = input("知识库名称: ").strip()
        text = input("文档内容: ").strip()
        if not kb_name or not text:
            out.error("名称和内容都不能为空")
            return
        result = self.mgr.add_to_kb(kb_name, text)
        if "error" in result:
            out.error(result["error"])
        else:
            out.ok(f"已添加 {result.get('chunks', 0)} 个文本块")

    def _query(self):
        kb_name = input("知识库名称: ").strip()
        question = input("查询问题: ").strip()
        if not kb_name or not question:
            out.error("知识库名称和问题都不能为空")
            return
        results = self.mgr.query_kb(kb_name, question, top_k=5)
        print(f"\n找到 {len(results)} 条结果:\n")
        for r in results:
            print(f"  - {r['text'][:100]}{'...' if len(r['text']) > 100 else ''}")


class InteractiveConfig:
    """配置交互界面"""

    def run(self):
        while True:
            print()
            out.header("⚙️  配置管理")
            cfg = load_config()
            print("  1. 查看当前配置")
            print("  2. 修改搜索结果数")
            print("  3. 修改模型")
            print("  4. 修改半衰期")
            print("  5. 切换敏感过滤")
            print("  6. 重置配置")
            print("  7. 返回主菜单")

            choice = input("\n请选择 [1-7]: ").strip()
            if choice == "1":
                print(f"\n当前配置:\n")
                for k, v in sorted(cfg.items()):
                    print(f"  {k}: {v}")
            elif choice == "2":
                val = input(f"search_top_k（当前 {cfg['search_top_k']}）: ").strip()
                if val:
                    set_config("search_top_k", int(val))
                    out.ok(f"search_top_k = {val}")
            elif choice == "3":
                print(f"当前模型: {cfg['model_id']}")
                print("推荐: all-MiniLM-L6-v2（英文）/ bge-small-zh-v1.5（中文）")
                val = input("新模型 ID: ").strip()
                if val:
                    set_config("model_id", val)
                    out.ok(f"model_id = {val}")
                    out.warn("请重启服务使更改生效")
            elif choice == "4":
                val = input(f"half_life_days（当前 {cfg['half_life_days']}）: ").strip()
                if val:
                    set_config("half_life_days", int(val))
                    out.ok(f"half_life_days = {val}")
            elif choice == "5":
                current = cfg["sensitive_filter_enabled"]
                new = not current
                set_config("sensitive_filter_enabled", new)
                out.ok(f"sensitive_filter_enabled = {new}")
            elif choice == "6":
                from config import reset_config
                reset_config()
                out.ok("配置已重置为默认值")
            elif choice == "7":
                break


def main():
    _banner()

    while True:
        print()
        print("=" * 50)
        print("  Semantic Memory — 主菜单")
        print("=" * 50)
        print("  1. 📚 记忆管理")
        print("  2. 📖 知识库管理")
        print("  3. ⚙️  配置管理")
        print("  4. 📊 系统统计")
        print("  0. 🚪 退出")
        print()

        choice = input("请选择 [0-4]: ").strip()
        if choice == "1":
            InteractiveMemory().run()
        elif choice == "2":
            InteractiveKB().run()
        elif choice == "3":
            InteractiveConfig().run()
        elif choice == "4":
            mgr = MemoryManager()
            stats = mgr.stats()
            print(f"\n总记忆数: {stats['total_memories']}")
            print(f"总知识库: {stats['total_kbs']}")
            if stats.get("by_tag"):
                print("标签分布:")
                for tag, count in sorted(stats["by_tag"].items(), key=lambda x: -x[1]):
                    print(f"  {tag}: {count}")
        elif choice == "0":
            print("\n再见！👋")
            break


if __name__ == "__main__":
    main()
