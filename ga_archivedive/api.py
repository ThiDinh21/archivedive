from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

import httpx
from platformdirs import user_cache_dir

from .models import Card, SearchResponse

BASE_URL = "https://api.gatcg.com"
CACHE_TTL = 3600  # 1 hour


def _cache_path() -> Path:
    path = Path(user_cache_dir("ga-archivedive")) / "cache.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


class _Cache:
    def __init__(self) -> None:
        self._db = sqlite3.connect(_cache_path())
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS cache "
            "(key TEXT PRIMARY KEY, value TEXT, expires_at REAL)"
        )
        self._db.commit()

    def get(self, key: str) -> Any | None:
        row = self._db.execute(
            "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return None
        value, expires_at = row
        if time.time() > expires_at:
            self._db.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._db.commit()
            return None
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            self._db.execute("DELETE FROM cache WHERE key = ?", (key,))
            self._db.commit()
            return None

    def clear(self) -> None:
        self._db.execute("DELETE FROM cache")
        self._db.commit()

    def set(self, key: str, value: Any, ttl: int = CACHE_TTL) -> None:
        self._db.execute(
            "INSERT OR REPLACE INTO cache (key, value, expires_at) VALUES (?, ?, ?)",
            (key, json.dumps(value), time.time() + ttl),
        )
        self._db.commit()



def _or_sort_key(card: Card, sort: str) -> tuple:
    name = (card.name or "").lower()
    if sort == "name":
        return (name,)
    if sort == "power":
        return (card.power or 0, name)
    if sort == "life":
        return (card.life or 0, name)
    if sort == "level":
        return (card.level or 0, name)
    if sort == "durability":
        return (card.durability or 0, name)
    if sort in ("cost_memory", "cost_reserve"):
        try:
            v = int((card.cost and card.cost.value) or 0)
        except (ValueError, TypeError):
            v = 0
        return (v, name)
    if sort == "rarity":
        eds = card.result_editions or card.editions
        try:
            r = int(eds[0].rarity) if eds and eds[0].rarity else 0
        except (ValueError, TypeError):
            r = 0
        return (r, name)
    return (name,)


class GAClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(
            base_url=BASE_URL,
            timeout=10.0,
            headers={"Accept": "application/json"},
        )
        self._cache = _Cache()

    async def close(self) -> None:
        await self._http.aclose()

    async def search(
        self,
        *,
        name: str | None = None,
        element: list[str] | None = None,
        type: list[str] | None = None,
        subtype: list[str] | None = None,
        cls: list[str] | None = None,
        rarity: list[str] | None = None,
        cost_memory: int | None = None,
        cost_reserve: int | None = None,
        effect: str | None = None,
        legality_format: str | None = None,
        sort: str = "name",
        order: str = "ASC",
        page: int = 1,
        page_size: int = 50,
    ) -> SearchResponse:
        params: dict[str, Any] = {
            "sort": sort,
            "order": order,
            "page": page,
            "page_size": page_size,
        }
        if name:
            params["name"] = name
        if element:
            params["element[]"] = element
        if type:
            params["type[]"] = type
        if subtype:
            params["subtype[]"] = subtype
        if cls:
            params["class[]"] = cls
        if rarity:
            params["rarity[]"] = rarity
        if cost_memory is not None:
            params["cost_memory"] = cost_memory
        if cost_reserve is not None:
            params["cost_reserve"] = cost_reserve
        if effect:
            params["effect"] = effect
        if legality_format:
            params["legality_format"] = legality_format

        cache_key = f"search:{json.dumps(params, sort_keys=True)}"
        if cached := self._cache.get(cache_key):
            return SearchResponse.model_validate(cached)

        response = await self._http.get("/cards/search", params=params)
        response.raise_for_status()
        data = response.json()
        self._cache.set(cache_key, data)
        return SearchResponse.model_validate(data)

    async def get_card(self, slug: str) -> Card:
        cache_key = f"card:{slug}"
        if cached := self._cache.get(cache_key):
            return Card.model_validate(cached)

        response = await self._http.get(f"/cards/{slug}")
        response.raise_for_status()
        data = response.json()
        self._cache.set(cache_key, data)
        return Card.model_validate(data)

    async def autocomplete_names(self, name: str) -> list[str]:
        cache_key = f"autocomplete:{name.lower()}"
        if cached := self._cache.get(cache_key):
            return cached
        response = await self._http.get("/cards/autocomplete", params={"name": name})
        response.raise_for_status()
        data = response.json()
        results = data.get("data", data) if isinstance(data, dict) else data
        names = [c["name"] for c in results if "name" in c]
        self._cache.set(cache_key, names, ttl=300)
        return names

    async def random(self, count: int = 8) -> list[Card]:
        response = await self._http.get("/cards/random", params={"count": count})
        response.raise_for_status()
        data = response.json()
        cards = data.get("data", data) if isinstance(data, dict) else data
        return [Card.model_validate(c) for c in cards]

    async def search_query(
        self,
        query: str,
        page: int = 1,
        page_size: int = 15,
    ) -> SearchResponse:
        from .query import parse, to_api_params, apply_client_filters

        parsed = parse(query)

        if not parsed.groups or all(not g for g in parsed.groups):
            if parsed.warnings:
                return SearchResponse(
                    data=[], total_cards=0, total_pages=1, has_more=False,
                    paginated_cards_count=0, page=page, page_size=page_size,
                )
            return await self.search(page=page, page_size=page_size)

        if len(parsed.groups) == 1:
            return await self._fetch_group(
                parsed.groups[0], page, page_size,
                sort=parsed.sort, order=parsed.order,
            )

        # OR: fetch all pages from each group in parallel, merge, then paginate locally
        sem = asyncio.Semaphore(10)

        async def _fetch_throttled(group: list, page: int) -> SearchResponse:
            async with sem:
                return await self._fetch_group(
                    group, page=page, page_size=50,
                    sort=parsed.sort, order=parsed.order,
                )

        async def _fetch_all_pages(group: list) -> list[Card]:
            first = await _fetch_throttled(group, 1)
            cards = list(first.data)
            if not first.has_more:
                return cards
            remaining = await asyncio.gather(*(
                _fetch_throttled(group, p)
                for p in range(2, first.total_pages + 1)
            ))
            for result in remaining:
                cards.extend(result.data)
            return cards

        group_results = await asyncio.gather(
            *(_fetch_all_pages(g) for g in parsed.groups)
        )

        seen: set[str] = set()
        merged: list[Card] = []
        for cards in group_results:
            for card in cards:
                if card.slug not in seen:
                    seen.add(card.slug)
                    merged.append(card)

        merged.sort(
            key=lambda c: _or_sort_key(c, parsed.sort),
            reverse=(parsed.order.upper() == "DESC"),
        )

        total = len(merged)
        total_pages = max(1, (total + page_size - 1) // page_size)
        start = (page - 1) * page_size
        page_data = merged[start:start + page_size]

        return SearchResponse(
            data=page_data,
            total_cards=total,
            total_pages=total_pages,
            has_more=page < total_pages,
            paginated_cards_count=len(page_data),
            page=page,
            page_size=page_size,
        )

    async def _fetch_group(
        self,
        filters: list,
        page: int,
        page_size: int,
        sort: str = "name",
        order: str = "ASC",
    ) -> SearchResponse:
        from .query import to_api_params, apply_client_filters

        params = to_api_params(filters)
        params["sort"] = sort
        params["order"] = order
        params["page"] = page
        params["page_size"] = page_size

        cache_key = f"query:{json.dumps(params, sort_keys=True, default=str)}"
        if cached := self._cache.get(cache_key):
            result = SearchResponse.model_validate(cached)
        else:
            # Build httpx-compatible param list (multi-value support)
            param_list: list[tuple[str, Any]] = []
            for k, v in params.items():
                if isinstance(v, list):
                    for item in v:
                        param_list.append((k, item))
                else:
                    param_list.append((k, v))

            response = await self._http.get("/cards/search", params=param_list)
            response.raise_for_status()
            data = response.json()
            self._cache.set(cache_key, data)
            result = SearchResponse.model_validate(data)

        result.data = apply_client_filters(result.data, filters)
        return result

    async def fetch_known_types(self) -> set[str]:
        """Fetch all valid card types from the API definitions endpoint."""
        cache_key = "definitions:types"
        if cached := self._cache.get(cache_key):
            return set(cached)
        try:
            response = await self._http.get("/option/search")
            response.raise_for_status()
            types = {entry["value"] for entry in response.json().get("type", [])}
            self._cache.set(cache_key, list(types), ttl=86400)  # cache 24h
            return types
        except Exception:
            return set()

