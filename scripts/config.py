#!/usr/bin/env python3
"""
Semantic Memory — 用户配置管理
支持 JSON 配置文件，可自定义分块大小、衰减参数、模型选择等
"""
import os
import json

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
_QCLAW_BASE = os.path.normpath(os.path.join(SKILL_DIR, "..", "..", ".."))
DATA_DIR = os.path.join(
    os.environ.get("QCLAW_DATA", os.path.join(_QCLAW_BASE, "data")),
    "semantic-memory",
)
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

# ─── 默认配置 ──────────────────────────────────────────────
DEFAULTS = {
    # Embedding 模型
    "model_id": "all-MiniLM-L6-v2",     # 或 "bge-small-zh-v1.5"

    # 文本分块
    "chunk_max_chars": 512,               # 每块最大字符数
    "chunk_overlap": 64,                  # 块间重叠字符数

    # 搜索
    "search_top_k": 5,                    # 默认返回条数
    "search_min_score": 0.2,              # 最低相似度阈值

    # 时间衰减
    "half_life_days": 30,                 # 半衰期（天）
    "min_importance": 0.1,                # 低于此值可被自动遗忘

    # 对话 Hook
    "conversation_importance": 0.3,       # 对话记忆默认重要性
    "recall_importance_boost": 0.02,      # 每次被检索后重要性微增量
    "auto_recall_max_chars": 3000,        # 召回上下文字符预算

    # 去重
    "dedup_enabled": True,                # 是否启用去重
    "dedup_threshold": 0.95,              # 相似度超过此值视为重复

    # 敏感信息
    "sensitive_filter_enabled": True,     # 是否启用敏感过滤
    "sensitive_max_redact_ratio": 0.6,    # 超过此脱敏率拒绝存储

    # 性能监控
    "metrics_enabled": True,              # 是否启用性能监控
}


def load_config() -> dict:
    """
    加载用户配置（与默认值合并）
    用户配置优先，缺失字段回退到默认值
    """
    config = dict(DEFAULTS)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            if isinstance(user_config, dict):
                config.update(user_config)
        except (json.JSONDecodeError, OSError):
            pass  # 配置损坏时静默回退到默认值
    return config


def save_config(config: dict) -> dict:
    """
    保存用户配置（只保存非默认值）
    返回: 保存后的完整配置
    """
    # 只保存与默认值不同的项
    diff = {}
    for key, value in config.items():
        if key in DEFAULTS and value != DEFAULTS[key]:
            diff[key] = value
        elif key not in DEFAULTS:
            diff[key] = value  # 自定义字段全部保留

    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(diff, f, ensure_ascii=False, indent=2)

    return load_config()


def get_config(key: str, default=None):
    """获取单个配置项"""
    config = load_config()
    return config.get(key, default)


def set_config(key: str, value) -> dict:
    """
    设置单个配置项
    返回: 更新后的完整配置
    """
    config = load_config()
    config[key] = value
    return save_config(config)


def reset_config() -> dict:
    """重置为默认配置"""
    if os.path.exists(CONFIG_PATH):
        os.remove(CONFIG_PATH)
    return dict(DEFAULTS)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print(json.dumps(load_config(), ensure_ascii=False, indent=2))
    elif sys.argv[1] == "get" and len(sys.argv) >= 3:
        val = get_config(sys.argv[2])
        print(json.dumps({"key": sys.argv[2], "value": val}, ensure_ascii=False, indent=2))
    elif sys.argv[1] == "set" and len(sys.argv) >= 4:
        key, val_str = sys.argv[2], sys.argv[3]
        # 自动类型转换
        try:
            val = json.loads(val_str)
        except (json.JSONDecodeError, ValueError):
            val = val_str
        result = set_config(key, val)
        print(json.dumps({"status": "updated", "key": key, "value": result[key]}, ensure_ascii=False, indent=2))
    elif sys.argv[1] == "reset":
        result = reset_config()
        print(json.dumps({"status": "reset", "config": result}, ensure_ascii=False, indent=2))
    else:
        print(f"Usage: config.py [get <key> | set <key> <value> | reset]")
