import json
import pytest
import httpx
from ga_archivedive.api import GAClient, BASE_URL, _Cache


def _card_payload(**overrides) -> dict:
    return {
        "name": "Test Card",
        "slug": "test-card",
        "classes": ["WARRIOR"],
        "types": ["ALLY"],
        "subtypes": [],
        "elements": ["FIRE"],
        "cost": {"type": "memory", "value": "2"},
        "speed": None,
        "rule": [],
        "editions": [{"slug": "test-card-en1", "rarity": 1, "image": "/cards/images/abc.jpg"}],
        "result_editions": [],
        "references": [],
        "referenced_by": [],
        **overrides,
    }


def _search_payload(cards: list[dict], total: int = None) -> dict:
    return {
        "data": cards,
        "total_cards": total or len(cards),
        "total_pages": 1,
        "has_more": False,
        "paginated_cards_count": len(cards),
        "page": 1,
        "page_size": 50,
    }


def _make_client(responses: dict[str, object], tmp_path, monkeypatch) -> GAClient:
    """Build a GAClient with mocked HTTP and an isolated cache."""
    monkeypatch.setattr("ga_archivedive.api._cache_path", lambda: tmp_path / "test.db")

    def handler(request: httpx.Request) -> httpx.Response:
        path = request.url.path
        for pattern, payload in responses.items():
            if request.url.path.startswith(pattern):
                return httpx.Response(200, json=payload)
        return httpx.Response(404, json={"error": "not found"})

    client = GAClient.__new__(GAClient)
    client._http = httpx.AsyncClient(
        transport=httpx.MockTransport(handler),
        base_url=BASE_URL,
        timeout=10.0,
    )
    client._cache = _Cache()
    return client


# ── image_url ─────────────────────────────────────────────────────────────────

class TestImageUrl:
    def test_constructs_full_url(self, tmp_path, monkeypatch):
        client = _make_client({}, tmp_path, monkeypatch)
        assert client.image_url("abc.jpg") == f"{BASE_URL}/cards/images/abc.jpg"


# ── search ────────────────────────────────────────────────────────────────────

class TestSearch:
    async def test_returns_cards(self, tmp_path, monkeypatch):
        payload = _search_payload([_card_payload()])
        client = _make_client({"/cards/search": payload}, tmp_path, monkeypatch)
        result = await client.search(name="Test")
        assert len(result.data) == 1
        assert result.data[0].name == "Test Card"

    async def test_result_is_cached(self, tmp_path, monkeypatch):
        call_count = 0
        payload = _search_payload([_card_payload()])

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=payload)

        client = GAClient.__new__(GAClient)
        monkeypatch.setattr("ga_archivedive.api._cache_path", lambda: tmp_path / "test.db")
        client._http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=BASE_URL,
        )
        client._cache = _Cache()

        await client.search(name="Test")
        await client.search(name="Test")
        assert call_count == 1

    async def test_empty_result(self, tmp_path, monkeypatch):
        payload = _search_payload([])
        client = _make_client({"/cards/search": payload}, tmp_path, monkeypatch)
        result = await client.search(name="zzznomatch")
        assert result.data == []
        assert result.total_cards == 0


# ── get_card ──────────────────────────────────────────────────────────────────

class TestGetCard:
    async def test_returns_card(self, tmp_path, monkeypatch):
        client = _make_client({"/cards/test-card": _card_payload()}, tmp_path, monkeypatch)
        card = await client.get_card("test-card")
        assert card.name == "Test Card"
        assert card.slug == "test-card"

    async def test_result_is_cached(self, tmp_path, monkeypatch):
        call_count = 0

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal call_count
            call_count += 1
            return httpx.Response(200, json=_card_payload())

        client = GAClient.__new__(GAClient)
        monkeypatch.setattr("ga_archivedive.api._cache_path", lambda: tmp_path / "test.db")
        client._http = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url=BASE_URL,
        )
        client._cache = _Cache()

        await client.get_card("test-card")
        await client.get_card("test-card")
        assert call_count == 1

    async def test_not_found_raises(self, tmp_path, monkeypatch):
        client = _make_client({}, tmp_path, monkeypatch)
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_card("nonexistent")


# ── random ────────────────────────────────────────────────────────────────────

class TestRandom:
    async def test_returns_cards(self, tmp_path, monkeypatch):
        payload = {"data": [_card_payload(), _card_payload(name="Second Card", slug="second-card")]}
        client = _make_client({"/cards/random": payload}, tmp_path, monkeypatch)
        cards = await client.random(count=2)
        assert len(cards) == 2

    async def test_handles_flat_list_response(self, tmp_path, monkeypatch):
        payload = [_card_payload()]
        client = _make_client({"/cards/random": payload}, tmp_path, monkeypatch)
        cards = await client.random(count=1)
        assert len(cards) == 1
