#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Semantic Memory — 敏感信息过滤器
自动识别并脱敏 API 密钥、密码、身份证号、银行卡号等敏感数据
"""
from __future__ import annotations

import re

# ─── 敏感信息正则模式 ──────────────────────────────────────
SENSITIVE_PATTERNS = [
    # OpenAI API Key
    (re.compile(r'\bsk-[a-zA-Z0-9]{20,}\b'), '[REDACTED_API_KEY]'),
    # Generic API key patterns
    (re.compile(r'(?:api[_-]?key[=:\s]+)([a-zA-Z0-9_\-]{20,})', re.IGNORECASE), '[REDACTED_API_KEY]'),
    # Password patterns (English + Chinese)
    (re.compile(r'(?:password|密码|口令)[=:\s是：为]+(\S+)', re.IGNORECASE), '[REDACTED_PASSWORD]'),
    (re.compile(r'(?:passwd|pwd)[=:\s是：为]+(\S+)', re.IGNORECASE), '[REDACTED_PASSWORD]'),
    # Chinese ID card (18 digits)
    (re.compile(r'\b\d{6}(?:19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]\b'), '[REDACTED_ID_CARD]'),
    # Bank card number (16-19 consecutive digits)
    (re.compile(r'\b\d{16,19}\b'), '[REDACTED_BANK_CARD]'),
    # Phone numbers (Chinese mobile: 1xx-xxxx-xxxx)
    (re.compile(r'\b1[3-9]\d{9}\b'), '[REDACTED_PHONE]'),
    # Email addresses
    (re.compile(r'\b[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}\b'), '[REDACTED_EMAIL]'),
    # JWT tokens
    (re.compile(r'\beyJ[a-zA-Z0-9_\-]*\.eyJ[a-zA-Z0-9_\-]*\.[a-zA-Z0-9_\-]*\b'), '[REDACTED_JWT]'),
    # AWS Access Key
    (re.compile(r'\bAKIA[A-Z0-9]{16}\b'), '[REDACTED_AWS_KEY]'),
    # AWS Secret Key
    (re.compile(r'(?:aws[_-]?secret[_-]?key[=:\s]+)([a-zA-Z0-9/+=]{40})', re.IGNORECASE), '[REDACTED_AWS_SECRET]'),
    # Private key markers
    (re.compile(r'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----'), '[REDACTED_PRIVATE_KEY]'),
]

# 不应脱敏的排除模式（避免误杀）
EXCLUDE_PATTERNS = [
    # 年月日 (如 20260504)
    re.compile(r'\b\d{8}\b'),
    # 纯时间戳
    re.compile(r'\b\d{10,13}\b'),
]


def sanitize(text: str) -> str:
    """
    过滤文本中的敏感信息，返回脱敏后的文本
    """
    if not text:
        return text

    result = text
    for pattern, replacement in SENSITIVE_PATTERNS:
        result = pattern.sub(replacement, result)

    return result


def has_sensitive_info(text: str) -> bool:
    """
    检测文本中是否包含敏感信息（不修改原文）
    """
    if not text:
        return False

    for pattern, _ in SENSITIVE_PATTERNS:
        if pattern.search(text):
            return True
    return False


def should_store(text: str) -> tuple[bool, str]:
    """
    判断文本是否应该被存储
    返回: (should_store, reason)
    - 纯 API Key 不存储
    - 纯密码不存储
    - 包含敏感信息但主要是正常内容的：脱敏后存储
    """
    if not text or len(text.strip()) < 5:
        return False, "text_too_short"

    # 检测是否是纯敏感信息（只有 API Key/密码，没有其他内容）
    stripped = text.strip()
    # 如果整个文本几乎就是一个敏感模式匹配，直接拒绝
    for pattern, _ in SENSITIVE_PATTERNS:
        match = pattern.search(stripped)
        if match:
            # 检查匹配是否覆盖了大部分文本
            matched_len = match.end() - match.start()
            if matched_len / len(stripped) > 0.7:
                return False, "mostly_sensitive"

    # 检测是否几乎全是敏感信息（如纯密钥）
    sanitized = sanitize(text)
    original_len = len(text)
    sanitized_len = len(sanitized)
    redacted_ratio = 1.0 - (sanitized_len / max(original_len, 1))

    # 如果超过 60% 的内容被脱敏，可能不应该存储
    if redacted_ratio > 0.6:
        return False, "mostly_sensitive"

    return True, "ok" if redacted_ratio < 0.01 else "sanitized"


if __name__ == "__main__":
    # 测试
    test_cases = [
        "今天和张三讨论了AI项目进展",
        "我的API密钥是sk-abc123def456ghi789jkl012mno345pqr678",
        "密码是 MyP@ssw0rd! 请记住",
        "身份证号 110101199001011234 银行卡 6222021234567890123",
        "手机号 13800138000 邮箱 test@example.com",
        "用户密码password=abc123，请登录后修改",
    ]

    for text in test_cases:
        should, reason = should_store(text)
        sanitized = sanitize(text)
        print(f"原文: {text[:50]}")
        print(f"  存储: {should} ({reason})")
        print(f"  脱敏: {sanitized[:50]}")
        print()
