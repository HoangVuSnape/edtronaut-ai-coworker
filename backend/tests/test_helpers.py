"""Unit tests for coworker_api.utils.helpers."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from coworker_api.utils.helpers import generate_id, utc_now, truncate_text


class TestGenerateId:
    def test_returns_valid_uuid4(self):
        result = generate_id()
        parsed = uuid.UUID(result, version=4)
        assert str(parsed) == result

    def test_returns_unique_values(self):
        ids = {generate_id() for _ in range(10)}
        assert len(ids) == 10


class TestUtcNow:
    def test_returns_timezone_aware_datetime(self):
        now = utc_now()
        assert isinstance(now, datetime)
        assert now.tzinfo is not None

    def test_is_utc(self):
        now = utc_now()
        assert now.tzinfo == timezone.utc


class TestTruncateText:
    def test_short_text_unchanged(self):
        assert truncate_text("hello", max_length=100) == "hello"

    def test_exact_length_unchanged(self):
        text = "a" * 100
        assert truncate_text(text, max_length=100) == text

    def test_long_text_truncated_with_suffix(self):
        text = "a" * 200
        result = truncate_text(text, max_length=100)
        assert len(result) == 100
        assert result.endswith("...")

    def test_custom_suffix(self):
        text = "a" * 200
        result = truncate_text(text, max_length=50, suffix="…")
        assert result.endswith("…")
        assert len(result) == 50

    def test_empty_string(self):
        assert truncate_text("", max_length=10) == ""
