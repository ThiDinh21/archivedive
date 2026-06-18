from typing import Any
from pydantic import BaseModel, Field, field_validator


class CardCost(BaseModel):
    type: str  # "memory", "reserve", "none"
    value: str | None = None  # can be "2", "X", etc.

    @field_validator("value", mode="before")
    @classmethod
    def coerce_value(cls, v: Any) -> str | None:
        if v is None:
            return None
        return str(v)


class SetInfo(BaseModel):
    name: str | None = None
    prefix: str | None = None
    language: str | None = None


_RARITY_NAMES: dict[str, str] = {
    "1": "Common",
    "2": "Uncommon",
    "3": "Rare",
    "4": "Super Rare",
    "5": "Ultra Rare",
    "6": "Promo",
    "7": "Collector Super Rare",
    "8": "Collector Ultra Rare",
    "9": "Collector Promo Rare",
}

_RARITY_SHORT: dict[str, str] = {
    "1": "C", "2": "U", "3": "R", "4": "SR", "5": "UR",
    "6": "PR", "7": "CSR", "8": "CUR", "9": "CPR",
}


class CardEdition(BaseModel):
    slug: str | None = None
    uuid: str | None = None
    collector_number: str | None = None
    rarity: str | None = None

    @field_validator("rarity", mode="before")
    @classmethod
    def coerce_rarity(cls, v: Any) -> str | None:
        if v is None:
            return None
        return str(v)

    @property
    def rarity_name(self) -> str | None:
        if self.rarity is None:
            return None
        return _RARITY_NAMES.get(self.rarity, self.rarity)

    @property
    def rarity_short(self) -> str | None:
        if self.rarity is None:
            return None
        return _RARITY_SHORT.get(self.rarity, self.rarity)
    illustrator: str | None = None
    image: str | None = None
    effect: str | None = None
    flavor: str | None = None
    set: SetInfo | None = None
    legality: dict[str, Any] | None = None


class CardReference(BaseModel):
    kind: str | None = None
    name: str
    slug: str
    uuid: str | None = None
    direction: str | None = None


class Card(BaseModel):
    name: str
    slug: str
    uuid: str | None = None
    classes: list[str] = Field(default_factory=list)
    types: list[str] = Field(default_factory=list)
    subtypes: list[str] = Field(default_factory=list)
    elements: list[str] = Field(default_factory=list)
    power: int | None = None
    life: int | None = None
    level: int | None = None
    durability: int | None = None
    speed: str | None = None
    cost: CardCost | None = None
    effect: str | None = None
    flavor: str | None = None
    rule: str | None = None
    legality: dict[str, dict[str, Any]] | None = None

    @field_validator("speed", mode="before")
    @classmethod
    def coerce_speed(cls, v: Any) -> str | None:
        if v is None or isinstance(v, bool):
            return None
        return str(v)

    @field_validator("rule", mode="before")
    @classmethod
    def coerce_rule(cls, v: Any) -> str | None:
        if not v:
            return None
        if isinstance(v, list):
            parts = []
            for item in v:
                if isinstance(item, str):
                    parts.append(item)
                elif isinstance(item, dict):
                    parts.append(item.get("description", ""))
            return "\n\n".join(p for p in parts if p) or None
        return v
    editions: list[CardEdition] = Field(default_factory=list)
    result_editions: list[CardEdition] = Field(default_factory=list)
    references: list[CardReference] = Field(default_factory=list)
    referenced_by: list[CardReference] = Field(default_factory=list)
    last_update: str | None = None

    @property
    def display_cost(self) -> str:
        if self.cost is None or self.cost.type == "none":
            return "-"
        symbol = "M" if self.cost.type == "memory" else "R"
        return f"{symbol}{self.cost.value}" if self.cost.value else symbol

    @property
    def display_types(self) -> str:
        parts = self.classes + self.types
        if self.subtypes:
            parts += ["—"] + self.subtypes
        return " ".join(parts)

    @property
    def display_elements(self) -> str:
        return " / ".join(self.elements) if self.elements else "-"



class SearchResponse(BaseModel):
    data: list[Card] = Field(default_factory=list)
    total_cards: int = 0
    total_pages: int = 0
    has_more: bool = False
    paginated_cards_count: int = 0
    page: int = 1
    page_size: int = 50
