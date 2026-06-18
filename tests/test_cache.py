import time
import pytest
from unittest.mock import patch
from ga_archivedive.api import _Cache


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setattr("ga_archivedive.api._cache_path", lambda: tmp_path / "test.db")
    return _Cache()


class TestCache:
    def test_miss_returns_none(self, cache):
        assert cache.get("missing") is None

    def test_set_and_get(self, cache):
        cache.set("key", {"name": "test"})
        assert cache.get("key") == {"name": "test"}

    def test_stores_various_types(self, cache):
        cache.set("list", [1, 2, 3])
        cache.set("string", "hello")
        cache.set("number", 42)
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("string") == "hello"
        assert cache.get("number") == 42

    def test_overwrite_existing(self, cache):
        cache.set("key", "first")
        cache.set("key", "second")
        assert cache.get("key") == "second"

    def test_expired_entry_returns_none(self, cache):
        cache.set("key", "value", ttl=1)
        with patch("ga_archivedive.api.time") as mock_time:
            mock_time.time.return_value = time.time() + 10
            assert cache.get("key") is None

    def test_unexpired_entry_returns_value(self, cache):
        cache.set("key", "value", ttl=3600)
        assert cache.get("key") == "value"

