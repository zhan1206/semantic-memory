"""sensitive_filter 单元测试"""
import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from sensitive_filter import sanitize, has_sensitive_info, should_store


class TestSanitize:
    def test_openai_key(self):
        text = "我的 API Key 是 sk-abc123def456ghi789jkl012mno345pqr678"
        result = sanitize(text)
        assert "sk-abc" not in result
        assert "[REDACTED_API_KEY]" in result

    def test_password_chinese(self):
        text = "密码是 MyP@ssw0rd! 请记住"
        result = sanitize(text)
        assert "MyP@ssw0rd" not in result

    def test_password_english(self):
        text = "password=secret123"
        result = sanitize(text)
        assert "secret123" not in result

    def test_id_card(self):
        text = "身份证号 110101199001011234 请查一下"
        result = sanitize(text)
        assert "110101199001011234" not in result

    def test_bank_card(self):
        text = "银行卡号 6222021234567890123"
        result = sanitize(text)
        assert "6222021234567890123" not in result

    def test_phone(self):
        text = "手机号 13800138000 请联系我"
        result = sanitize(text)
        assert "13800138000" not in result

    def test_email(self):
        text = "邮箱是 test@example.com"
        result = sanitize(text)
        assert "test@example.com" not in result

    def test_jwt(self):
        text = "token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.dozjgNryP4J3jVmNHl0w5N_XgL0n3I9PlFUP0THsR8U"
        result = sanitize(text)
        assert "eyJhbGciOiJIUzI1NiJ9" not in result

    def test_aws_key(self):
        text = "AKIAIOSFODNN7EXAMPLE key here"
        result = sanitize(text)
        assert "AKIAIOSFODNN7" not in result

    def test_private_key_marker(self):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQE...\n-----END RSA PRIVATE KEY-----"
        result = sanitize(text)
        assert "PRIVATE KEY" not in result

    def test_normal_text_unchanged(self):
        text = "今天讨论了项目计划，明天继续开会沟通。"
        result = sanitize(text)
        assert result == text

    def test_empty_string(self):
        assert sanitize("") == ""
        assert sanitize(None) is None

    def test_combined(self):
        text = "密码password=123，邮箱test@test.com，手机13800138000，API sk-abc123def456"
        result = sanitize(text)
        assert "123" not in result or "password" not in result


class TestHasSensitiveInfo:
    def test_has_api_key(self):
        assert has_sensitive_info("sk-abc123def456ghi789jkl012mno345") is True

    def test_has_phone(self):
        assert has_sensitive_info("13800138000") is True

    def test_clean_text(self):
        assert has_sensitive_info("今天天气不错，我们讨论了项目进展") is False


class TestShouldStore:
    def test_short_text_rejected(self):
        should, reason = should_store("hi")
        assert should is False
        assert reason == "text_too_short"

    def test_mostly_sensitive_rejected(self):
        # 纯密码/纯密钥不应存储
        should, reason = should_store("sk-abc123def456ghi789jkl012mno345pqr678")
        assert should is False
        assert reason == "mostly_sensitive"

    def test_normal_text_accepted(self):
        should, reason = should_store("今天讨论了项目进展，明天继续开会")
        assert should is True
        assert reason == "ok"

    def test_partially_sanitized(self):
        text = "项目代号是 sk-abc123def456ghi789，任务分配如下..."
        should, reason = should_store(text)
        assert should is True
        assert reason in ("ok", "sanitized")

    def test_empty_rejected(self):
        should, reason = should_store("")
        assert should is False