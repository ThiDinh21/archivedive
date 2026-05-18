"""Search query parser and API translator for ArchiveDive."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ── Constants ──────────────────────────────────────────────────────────────────

ELEMENT_ALIASES: dict[str, str] = {
    "fi": "FIRE", "fire": "FIRE",
    "wa": "WATER", "water": "WATER",
    "wi": "WIND", "wind": "WIND",
    "cr": "CRUX", "crux": "CRUX",
    "no": "NORM", "norm": "NORM",
    "arcane": "ARCANE",
    "as": "ASTRA", "astra": "ASTRA",
    "te": "TERA", "tera": "TERA",
    "um": "UMBRA", "umbra": "UMBRA",
    "lu": "LUXEM", "luxem": "LUXEM",
    "ne": "NEOS", "neos": "NEOS",
    "xi": "EXIA", "exia": "EXIA",
    "xl": "EXALTED", "exalted": "EXALTED",
}

RARITY_MAP: dict[str, int] = {
    "c": 1, "common": 1,
    "u": 2, "uncommon": 2,
    "r": 3, "rare": 3,
    "sr": 4, "superrare": 4,
    "ur": 5, "ultrarare": 5,
    "pr": 6, "promo": 6,
    "csr": 7, "collectorsuper": 7,
    "cur": 8, "collectorultra": 8,
    "cpr": 9, "collectorpromo": 9,
}

FORMAT_MAP: dict[str, str] = {
    "s": "STANDARD", "standard": "STANDARD",
    "p": "PANTHEON", "pantheon": "PANTHEON",
    "d": "DRAFT", "draft": "DRAFT",
}

FLAGS: dict[str, str] = {
    "material": "t:champion OR t:regalia",
    "permanent": (
        "t:ally OR t:champion OR t:item OR t:weapon OR t:token "
        "OR t:status OR t:regalia OR t:phantasia OR t:mastery"
    ),
}

# Keys normalised to internal names
_KEY_MAP: dict[str, str] = {
    "name": "name",
    "o": "effect", "effect": "effect",
    "oc": "oracle", "oracle": "oracle",
    "kw": "keyword", "keyword": "keyword",
    "t": "type", "type": "type", "sub": "subtype", "subtype": "subtype",
    "class": "class",
    "e": "element", "element": "element",
    "r": "rarity", "rarity": "rarity",
    "set": "prefix", "s": "prefix",
    "cost": "cost", "c": "cost",
    "m": "cost_memory", "memory": "cost_memory",
    "res": "cost_reserve", "reserve": "cost_reserve",
    "legal": "legal",
    "banned": "banned",
    "speed": "speed",
    "pow": "power", "power": "power",
    "life": "life",
    "dur": "durability", "durability": "durability",
    "lvl": "level", "level": "level",
    "rule": "rule",
    "flavor": "flavor",
    "ill": "illustrator", "illustrator": "illustrator",
    "is": "flag",
}

# Known card types — used to route t: to type vs subtype param.
# Populated dynamically at startup via set_known_types(); this is the fallback.
_KNOWN_TYPES: set[str] = {
    "ALLY", "CHAMPION", "ACTION", "ATTACK", "GREATER BOON", "LESSER BOON",
    "ITEM", "MASTERY", "PHANTASIA", "REGALIA", "STATUS", "TOKEN", "UNIQUE", "WEAPON",
    "DOMAIN",
}


def set_known_types(types: set[str]) -> None:
    global _KNOWN_TYPES
    if types:
        _KNOWN_TYPES = _KNOWN_TYPES | types  # union: never drop known types

# Fields handled client-side (API params broken or unsupported)
_CLIENT_SIDE = {"oracle", "keyword", "power", "life", "durability", "level",
                "cost_memory", "cost_reserve", "cost"}

# ── Data structures ────────────────────────────────────────────────────────────

@dataclass
class Filter:
    key: str
    value: str
    op: str = "="       # =, >, <, >=, <=
    negated: bool = False

    @property
    def is_client_side(self) -> bool:
        return self.key in _CLIENT_SIDE or self.negated or self.op != "="


SORT_MAP: dict[str, str] = {
    "name": "name",
    "cost": "cost_memory", "c": "cost_memory",
    "m": "cost_memory", "memory": "cost_memory",
    "res": "cost_reserve", "reserve": "cost_reserve",
    "rarity": "rarity", "r": "rarity",
    "power": "power", "pow": "power",
    "life": "life",
    "level": "level", "lvl": "level",
    "durability": "durability", "dur": "durability",
    "number": "collector_number", "cn": "collector_number",
}

ORDER_MAP: dict[str, str] = {
    "asc": "ASC", "a": "ASC",
    "desc": "DESC", "d": "DESC",
}


@dataclass
class ParsedQuery:
    # OR-groups of AND-combined filters
    groups: list[list[Filter]] = field(default_factory=lambda: [[]])
    sort: str = "name"
    order: str = "ASC"


# ── Tokeniser ──────────────────────────────────────────────────────────────────

_TOKEN_RE = re.compile(
    r'-?[a-zA-Z]+(?:>=|<=|>|<|=|:)"[^"]*"'  # key:"quoted value"
    r'|-?[a-zA-Z]+(?:>=|<=|>|<|=|:)\S+'       # key:value
    r'|"[^"]*"'                                 # bare "quoted string"
    r'|\S+'                                     # plain word
)
_FILTER_RE = re.compile(
    r'^(-?)'
    r'([a-zA-Z]+)'
    r'(>=|<=|>|<|=|:)'
    r'("(?:[^"\\]|\\.)*"|.+)$'
)


def _tokenize(text: str) -> list[str]:
    return _TOKEN_RE.findall(text)


def _strip_quotes(s: str) -> str:
    if s.startswith('"') and s.endswith('"'):
        return s[1:-1]
    return s


# ── Parser ─────────────────────────────────────────────────────────────────────

def parse(text: str) -> ParsedQuery:
    tokens = _tokenize(text.strip())
    if not tokens:
        return ParsedQuery(groups=[[]])

    q = ParsedQuery(groups=[])

    # Extract sort/order modifiers first, leaving the rest for filter parsing
    remaining: list[str] = []
    for tok in tokens:
        m = _FILTER_RE.match(tok)
        if m and not m.group(1):  # no negation
            raw_key = m.group(2).lower()
            value = _strip_quotes(m.group(4))
            if raw_key == "sort":
                q.sort = SORT_MAP.get(value.lower(), value.lower())
                continue
            if raw_key in ("order", "dir"):
                q.order = ORDER_MAP.get(value.lower(), "ASC")
                continue
        remaining.append(tok)

    # Split remaining on OR
    groups_raw: list[list[str]] = [[]]
    for tok in remaining:
        if tok.upper() == "OR":
            groups_raw.append([])
        else:
            groups_raw[-1].append(tok)

    for raw_group in groups_raw:
        group, name_parts = _parse_group(raw_group)
        if name_parts:
            group.append(Filter(key="name", value=" ".join(name_parts)))
        if group:
            q.groups.append(group)

    if not q.groups:
        q.groups = [[]]
    return q


def _parse_group(tokens: list[str]) -> tuple[list[Filter], list[str]]:
    filters: list[Filter] = []
    name_parts: list[str] = []
    for tok in tokens:
        m = _FILTER_RE.match(tok)
        if m:
            negated = m.group(1) == "-"
            raw_key = m.group(2).lower()
            op = m.group(3).replace(":", "=")
            value = _strip_quotes(m.group(4))
            if raw_key in _KEY_MAP:
                key = _KEY_MAP[raw_key]
                if key == "flag":
                    expanded = FLAGS.get(value.lower())
                    if expanded:
                        sub = parse(expanded)
                        for sub_group in sub.groups:
                            filters.extend(sub_group)
                else:
                    filters.append(Filter(key=key, value=value, op=op, negated=negated))
            else:
                name_parts.append(_strip_quotes(tok))
        else:
            name_parts.append(_strip_quotes(tok))
    return filters, name_parts


# ── API param builder ──────────────────────────────────────────────────────────

def to_api_params(filters: list[Filter]) -> dict[str, Any]:
    """Translate a list of AND-combined filters into GA API params.

    Returns only server-side filters; client-side ones must be post-processed.
    kw: and oc: use effect as a proxy to narrow the API results.
    """
    params: dict[str, Any] = {}

    for f in filters:
        v = f.value

        # kw: and oc: use effect as a proxy before client-side exact filtering
        if f.key in ("keyword", "oracle") and not f.negated:
            if "effect" not in params:
                params["effect"] = v
            continue

        if f.is_client_side:
            continue

        if f.key == "name":
            params["name"] = v

        elif f.key == "effect":
            params["effect"] = v

        elif f.key == "type":
            upper = v.upper()
            api_key = "type" if upper in _KNOWN_TYPES else "subtype"
            _append(params, api_key, upper)

        elif f.key == "subtype":
            _append(params, "subtype", v.upper())

        elif f.key == "class":
            _append(params, "class", v.upper())

        elif f.key == "element":
            elem = ELEMENT_ALIASES.get(v.lower(), v.upper())
            _append(params, "element", elem)

        elif f.key == "rarity":
            rarity_num = RARITY_MAP.get(v.lower().replace(" ", ""))
            if rarity_num:
                params["rarity"] = rarity_num

        elif f.key == "prefix":
            _append(params, "prefix", v)

        elif f.key == "speed":
            _append(params, "speed", v.lower())

        elif f.key == "rule":
            params["rule"] = v

        elif f.key == "flavor":
            params["flavor"] = v

        elif f.key == "illustrator":
            params["illustrator"] = v

        elif f.key == "legal":
            fmt = FORMAT_MAP.get(v.lower(), v.upper())
            params["legality_format"] = fmt
            params["legality_state"] = "LEGAL"

        elif f.key == "banned":
            fmt = FORMAT_MAP.get(v.lower(), v.upper())
            params["legality_format"] = fmt
            params["legality_state"] = "RESTRICTED"

    return params


def _append(params: dict[str, Any], key: str, value: str) -> None:
    """Accumulate multi-value params as lists."""
    if key not in params:
        params[key] = value
    elif isinstance(params[key], list):
        params[key].append(value)
    else:
        params[key] = [params[key], value]


# ── Client-side filter ─────────────────────────────────────────────────────────

def apply_client_filters(cards: list[Any], filters: list[Filter]) -> list[Any]:
    """Apply filters that the API can't handle."""
    import re as _re
    result = cards
    for f in filters:
        if not f.is_client_side:
            continue
        result = [c for c in result if _matches(c, f)]
    return result


def _matches(card: Any, f: Filter) -> bool:
    from .models import Card
    if not isinstance(card, Card):
        return True

    matched = _check(card, f)
    return (not matched) if f.negated else matched


def _check(card: Any, f: Filter) -> bool:
    from .models import Card
    import re as _re

    c: Card = card
    key, val, op = f.key, f.value.lower(), f.op

    if key == "oracle":
        return val in (c.effect or "").lower()

    if key == "keyword":
        pattern = _re.compile(r'\*\*' + _re.escape(f.value) + r'\*\*', _re.IGNORECASE)
        return bool(pattern.search(c.effect or ""))

    if key == "name":
        return val in c.name.lower()

    if key == "type":
        upper = val.upper()
        if upper in _KNOWN_TYPES:
            return any(val == t.lower() for t in c.types)
        return any(val == s.lower() for s in c.subtypes)

    if key == "subtype":
        return any(val == s.lower() for s in c.subtypes)

    if key == "class":
        return any(val == cl.lower() for cl in c.classes)

    if key == "element":
        elem = ELEMENT_ALIASES.get(val, val.upper())
        return any(elem == e for e in c.elements)

    if key == "rarity":
        rarity_num = RARITY_MAP.get(val.replace(" ", ""))
        if rarity_num is None:
            return True
        eds = c.result_editions or c.editions
        return any(str(ed.rarity) == str(rarity_num) for ed in eds)

    if key == "speed":
        return (c.speed or "").lower() == val

    if key == "prefix":
        eds = c.result_editions or c.editions
        return any(val.lower() in (ed.set.prefix or "").lower()
                   for ed in eds if ed.set)

    if key in ("power", "life", "durability", "level"):
        attr = getattr(c, key, None)
        if attr is None:
            return False
        try:
            return _compare(int(attr), op, int(val))
        except (ValueError, TypeError):
            return False

    if key == "cost_memory":
        if c.cost is None or c.cost.type != "memory":
            return False
        try:
            return _compare(int(c.cost.value or 0), op, int(val))
        except (ValueError, TypeError):
            return False

    if key == "cost_reserve":
        if c.cost is None or c.cost.type != "reserve":
            return False
        try:
            return _compare(int(c.cost.value or 0), op, int(val))
        except (ValueError, TypeError):
            return False

    if key == "cost":
        if c.cost is None or c.cost.type == "none":
            return False
        try:
            return _compare(int(c.cost.value or 0), op, int(val))
        except (ValueError, TypeError):
            return False

    return True


def _compare(actual: int, op: str, expected: int) -> bool:
    return {
        "=": actual == expected,
        ">": actual > expected,
        "<": actual < expected,
        ">=": actual >= expected,
        "<=": actual <= expected,
    }.get(op, False)
