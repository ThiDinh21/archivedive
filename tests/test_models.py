import pytest
from ga_archivedive.models import Card, CardCost, CardEdition, SearchResponse


# ── CardCost ──────────────────────────────────────────────────────────────────

class TestCardCost:
    def test_value_string_kept(self):
        cost = CardCost(type="memory", value="2")
        assert cost.value == "2"

    def test_value_int_coerced_to_string(self):
        cost = CardCost.model_validate({"type": "memory", "value": 2})
        assert cost.value == "2"

    def test_value_x_kept(self):
        cost = CardCost.model_validate({"type": "memory", "value": "X"})
        assert cost.value == "X"

    def test_value_none(self):
        cost = CardCost(type="none", value=None)
        assert cost.value is None


# ── CardEdition ───────────────────────────────────────────────────────────────

class TestCardEdition:
    def test_rarity_int_coerced(self):
        ed = CardEdition.model_validate({"rarity": 2})
        assert ed.rarity == "2"

    def test_rarity_string_kept(self):
        ed = CardEdition.model_validate({"rarity": "rare"})
        assert ed.rarity == "rare"

    def test_rarity_none(self):
        ed = CardEdition.model_validate({"rarity": None})
        assert ed.rarity is None


# ── Card validators ───────────────────────────────────────────────────────────

def _base_card(**overrides) -> dict:
    return {
        "name": "Test Card",
        "slug": "test-card",
        "classes": ["WARRIOR"],
        "types": ["ALLY"],
        "subtypes": [],
        "elements": ["FIRE"],
        "cost": {"type": "memory", "value": "2"},
        **overrides,
    }


class TestCardRule:
    def test_empty_list_becomes_none(self):
        card = Card.model_validate(_base_card(rule=[]))
        assert card.rule is None

    def test_none_stays_none(self):
        card = Card.model_validate(_base_card(rule=None))
        assert card.rule is None

    def test_string_kept(self):
        card = Card.model_validate(_base_card(rule="some rule"))
        assert card.rule == "some rule"

    def test_list_of_dicts_joined(self):
        card = Card.model_validate(_base_card(rule=[
            {"title": "", "date_added": "2025-01-01", "description": "First rule."},
            {"title": "", "date_added": "2025-01-02", "description": "Second rule."},
        ]))
        assert card.rule == "First rule.\n\nSecond rule."

    def test_list_of_dicts_empty_descriptions_skipped(self):
        card = Card.model_validate(_base_card(rule=[
            {"title": "", "date_added": "2025-01-01", "description": ""},
        ]))
        assert card.rule is None


class TestCardSpeed:
    def test_bool_true_becomes_none(self):
        card = Card.model_validate(_base_card(speed=True))
        assert card.speed is None

    def test_bool_false_becomes_none(self):
        card = Card.model_validate(_base_card(speed=False))
        assert card.speed is None

    def test_none_stays_none(self):
        card = Card.model_validate(_base_card(speed=None))
        assert card.speed is None

    def test_string_kept(self):
        card = Card.model_validate(_base_card(speed="fast"))
        assert card.speed == "fast"


# ── Card display properties ───────────────────────────────────────────────────

class TestDisplayCost:
    def test_memory_cost(self):
        card = Card.model_validate(_base_card(cost={"type": "memory", "value": "3"}))
        assert card.display_cost == "M3"

    def test_reserve_cost(self):
        card = Card.model_validate(_base_card(cost={"type": "reserve", "value": "2"}))
        assert card.display_cost == "R2"

    def test_x_cost(self):
        card = Card.model_validate(_base_card(cost={"type": "memory", "value": "X"}))
        assert card.display_cost == "MX"

    def test_no_cost(self):
        card = Card.model_validate(_base_card(cost={"type": "none", "value": None}))
        assert card.display_cost == "-"

    def test_null_cost(self):
        card = Card.model_validate(_base_card(cost=None))
        assert card.display_cost == "-"


class TestDisplayTypes:
    def test_class_and_type(self):
        card = Card.model_validate(_base_card(classes=["CHAMPION"], types=["WARRIOR"], subtypes=[]))
        assert card.display_types == "CHAMPION WARRIOR"

    def test_with_subtypes(self):
        card = Card.model_validate(_base_card(classes=["ALLY"], types=["HUMAN"], subtypes=["KNIGHT"]))
        assert card.display_types == "ALLY HUMAN — KNIGHT"

    def test_empty(self):
        card = Card.model_validate(_base_card(classes=[], types=[], subtypes=[]))
        assert card.display_types == ""


class TestDisplayElements:
    def test_single(self):
        card = Card.model_validate(_base_card(elements=["FIRE"]))
        assert card.display_elements == "FIRE"

    def test_multiple(self):
        card = Card.model_validate(_base_card(elements=["FIRE", "WIND"]))
        assert card.display_elements == "FIRE / WIND"

    def test_empty(self):
        card = Card.model_validate(_base_card(elements=[]))
        assert card.display_elements == "-"


# ── SearchResponse ────────────────────────────────────────────────────────────

class TestSearchResponse:
    def test_empty_defaults(self):
        resp = SearchResponse.model_validate({})
        assert resp.data == []
        assert resp.total_cards == 0
        assert resp.has_more is False

    def test_parses_cards(self):
        resp = SearchResponse.model_validate({
            "data": [_base_card()],
            "total_cards": 1,
            "total_pages": 1,
            "has_more": False,
            "paginated_cards_count": 1,
            "page": 1,
            "page_size": 50,
        })
        assert len(resp.data) == 1
        assert resp.data[0].name == "Test Card"
