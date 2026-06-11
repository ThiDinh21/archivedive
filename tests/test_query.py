"""Tests for the search query parser, API param builder, and client-side filter."""
import pytest
from ga_archivedive.query import (
    Filter, ParsedQuery, parse, to_api_params, apply_client_filters,
    _tokenize, _check,
)
from ga_archivedive.models import Card, CardCost, CardEdition


# ── Helpers ────────────────────────────────────────────────────────────────────

def _card(**kwargs) -> Card:
    defaults = dict(
        name="Test Card", slug="test-card",
        classes=[], types=["ALLY"], subtypes=[],
        elements=["FIRE"],
        cost=CardCost(type="memory", value="2"),
        speed=None, editions=[], result_editions=[],
        references=[], referenced_by=[],
    )
    defaults.update(kwargs)
    return Card(**defaults)


def _kv(q: ParsedQuery) -> list[list[tuple]]:
    """(key, value) pairs per group — ignores negated/op for quick structural checks."""
    return [[(f.key, f.value) for f in g] for g in q.groups]


def _full(q: ParsedQuery) -> list[list[tuple]]:
    """(key, value, op, negated) per group."""
    return [[(f.key, f.value, f.op, f.negated) for f in g] for g in q.groups]


# ── Tokenizer ──────────────────────────────────────────────────────────────────

class TestTokenize:
    def test_empty(self):
        assert _tokenize("") == []

    def test_plain_word(self):
        assert _tokenize("silvie") == ["silvie"]

    def test_simple_filter(self):
        assert _tokenize("t:ally") == ["t:ally"]

    def test_multiple_filters(self):
        assert _tokenize("t:ally e:fire") == ["t:ally", "e:fire"]

    def test_parens_separate_tokens(self):
        assert _tokenize("(t:ally)") == ["(", "t:ally", ")"]

    def test_or_inside_parens(self):
        assert _tokenize("(t:ally or t:champion)") == [
            "(", "t:ally", "or", "t:champion", ")"
        ]

    def test_quoted_value(self):
        assert _tokenize('o:"on enter"') == ['o:"on enter"']

    def test_numeric_operator(self):
        assert _tokenize("pow>=3") == ["pow>=3"]

    def test_negated_filter(self):
        assert _tokenize("-e:fire") == ["-e:fire"]

    def test_paren_no_spaces(self):
        # parens without spaces still tokenized correctly
        assert _tokenize("(t:ally)e:fire") == ["(", "t:ally", ")", "e:fire"]

    def test_value_cannot_contain_paren(self):
        # the paren inside a value is a separate token, not part of the filter
        tokens = _tokenize("t:ally(bad")
        assert "(" in tokens


# ── Parse → DNF groups ─────────────────────────────────────────────────────────

class TestParse:

    # Basics
    def test_empty_string(self):
        assert parse("").groups == [[]]

    def test_whitespace_only(self):
        assert parse("   ").groups == [[]]

    def test_plain_name(self):
        assert _kv(parse("silvie")) == [[("name", "silvie")]]

    def test_multi_word_name(self):
        assert _kv(parse("dungeon guide")) == [[("name", "dungeon guide")]]

    def test_simple_filter(self):
        assert _kv(parse("t:ally")) == [[("type", "ally")]]

    def test_implicit_and(self):
        assert _kv(parse("t:ally e:fire")) == [[("type", "ally"), ("element", "fire")]]

    # OR
    def test_simple_or(self):
        assert _kv(parse("t:ally or t:champion")) == [
            [("type", "ally")], [("type", "champion")]
        ]

    def test_or_uppercase(self):
        assert _kv(parse("t:ally OR t:champion")) == [
            [("type", "ally")], [("type", "champion")]
        ]

    # OR precedence: adjacent filters AND-bind tighter than OR
    def test_or_precedence_left(self):
        # (ally AND fire) OR champion
        q = parse("t:ally e:fire OR t:champion")
        assert _kv(q) == [
            [("type", "ally"), ("element", "fire")],
            [("type", "champion")],
        ]

    def test_or_precedence_right(self):
        # ally OR (fire AND champion)
        q = parse("t:ally OR e:fire t:champion")
        assert _kv(q) == [
            [("type", "ally")],
            [("element", "fire"), ("type", "champion")],
        ]

    # Parentheses
    def test_paren_wrapping_single_filter(self):
        assert _kv(parse("(t:ally)")) == [[("type", "ally")]]

    def test_paren_distributes_outer_filter(self):
        # (t:ally or t:champion) e:fire  →  2 groups, each with element:fire
        q = parse("(t:ally or t:champion) e:fire")
        assert _kv(q) == [
            [("type", "ally"), ("element", "fire")],
            [("type", "champion"), ("element", "fire")],
        ]

    def test_paren_filter_before_group(self):
        # commutativity: e:fire (t:ally or t:champion)
        q = parse("e:fire (t:ally or t:champion)")
        assert _kv(q) == [
            [("element", "fire"), ("type", "ally")],
            [("element", "fire"), ("type", "champion")],
        ]

    def test_paren_explicit_or_grouping(self):
        q = parse("(t:ally e:fire) or (t:champion e:water)")
        assert _kv(q) == [
            [("type", "ally"), ("element", "fire")],
            [("type", "champion"), ("element", "water")],
        ]

    def test_paren_cartesian_product(self):
        # (t:ally or t:champion) (e:fire or e:water)  →  4 groups
        q = parse("(t:ally or t:champion) (e:fire or e:water)")
        keys = _kv(q)
        assert len(keys) == 4
        assert [("type", "ally"),     ("element", "fire")]  in keys
        assert [("type", "ally"),     ("element", "water")] in keys
        assert [("type", "champion"), ("element", "fire")]  in keys
        assert [("type", "champion"), ("element", "water")] in keys

    def test_paren_cartesian_outer_filter_on_all_groups(self):
        # (t:ally or t:champion) (e:fire or e:water) r:rare  →  each group has rarity
        q = parse("(t:ally or t:champion) (e:fire or e:water) r:rare")
        assert len(q.groups) == 4
        for group in q.groups:
            assert any(f.key == "rarity" for f in group)

    def test_paren_nested(self):
        # ((t:ally) e:fire)  →  single group
        assert _kv(parse("((t:ally) e:fire)")) == [[("type", "ally"), ("element", "fire")]]

    def test_paren_nested_with_inner_or(self):
        # ((t:ally or t:champion) e:fire)  →  2 groups
        q = parse("((t:ally or t:champion) e:fire)")
        assert _kv(q) == [
            [("type", "ally"), ("element", "fire")],
            [("type", "champion"), ("element", "fire")],
        ]

    def test_paren_three_groups_cartesian(self):
        # (a or b) (c or d) (e or f)  →  8 groups
        q = parse("(e:fire or e:water) (t:ally or t:champion) (r:rare or r:sr)")
        assert len(q.groups) == 8

    # Negation scoping with OR
    def test_negation_scoped_to_branch(self):
        # e:fire OR e:water -r:common  →  fire | (water AND not-common)
        q = parse("e:fire OR e:water -r:common")
        assert len(q.groups) == 2
        assert _kv(q)[0] == [("element", "fire")]
        branch2 = {(f.key, f.negated) for f in q.groups[1]}
        assert ("element", False) in branch2
        assert ("rarity", True) in branch2

    def test_paren_negation_applies_to_all_branches(self):
        # (e:fire or e:water) -r:common  →  both branches get -r:common
        q = parse("(e:fire or e:water) -r:common")
        assert len(q.groups) == 2
        for group in q.groups:
            assert any(f.key == "rarity" and f.negated for f in group)

    # OR edge cases
    def test_or_at_start_pruned(self):
        # leading OR — empty first group dropped
        assert _kv(parse("OR t:ally")) == [[("type", "ally")]]

    def test_or_at_end_pruned(self):
        assert _kv(parse("t:ally OR")) == [[("type", "ally")]]

    def test_unmatched_close_paren_skipped(self):
        assert _kv(parse("t:ally)")) == [[("type", "ally")]]

    # Operators
    def test_operator_gt(self):
        f = parse("pow>3").groups[0][0]
        assert f == Filter(key="power", value="3", op=">")

    def test_operator_gte(self):
        f = parse("pow>=3").groups[0][0]
        assert f == Filter(key="power", value="3", op=">=")

    def test_operator_lt(self):
        f = parse("m<2").groups[0][0]
        assert f == Filter(key="cost_memory", value="2", op="<")

    def test_operator_lte(self):
        f = parse("lvl<=3").groups[0][0]
        assert f == Filter(key="level", value="3", op="<=")

    def test_operator_exact(self):
        f = parse("life=5").groups[0][0]
        assert f == Filter(key="life", value="5", op="=")

    # Negation
    def test_negated_filter(self):
        f = parse("-e:fire").groups[0][0]
        assert f == Filter(key="element", value="fire", negated=True)

    def test_negated_and_positive_combined(self):
        groups = _full(parse("t:ally -r:common"))
        assert ("type",    "ally",   "=", False) in groups[0]
        assert ("rarity",  "common", "=", True)  in groups[0]

    # Sort / order
    def test_sort_extracted(self):
        q = parse("t:ally sort:rarity")
        assert q.sort == "rarity"
        assert _kv(q) == [[("type", "ally")]]

    def test_sort_and_order(self):
        q = parse("sort:rarity order:desc t:ally")
        assert q.sort == "rarity"
        assert q.order == "DESC"

    def test_sort_alias_cost(self):
        assert parse("sort:cost").sort == "cost_memory"

    def test_sort_alias_number(self):
        assert parse("sort:number").sort == "collector_number"

    def test_order_alias_d(self):
        assert parse("order:d").order == "DESC"

    def test_default_sort_order(self):
        q = parse("t:ally")
        assert q.sort == "name"
        assert q.order == "ASC"

    # Key aliases
    def test_aliases(self):
        cases = [
            ("e:fire",    "element"),
            ("r:rare",    "rarity"),
            ("c:3",       "cost"),
            ("m:2",       "cost_memory"),
            ("res:2",     "cost_reserve"),
            ("s:DOA",     "prefix"),
            ("o:banish",  "effect"),
            ("oc:banish", "oracle"),
            ("kw:taunt",  "keyword"),
            ("ill:akira", "illustrator"),
            ("t:ally",    "type"),
            ("sub:human", "subtype"),
            ("pow:3",     "power"),
            ("dur:2",     "durability"),
            ("lvl:3",     "level"),
        ]
        for query, expected_key in cases:
            assert parse(query).groups[0][0].key == expected_key, f"alias failed for {query!r}"

    # Quoted values
    def test_quoted_multi_word_effect(self):
        f = parse('o:"on enter"').groups[0][0]
        assert f == Filter(key="effect", value="on enter")

    def test_quoted_illustrator(self):
        f = parse('ill:"studio atma"').groups[0][0]
        assert f == Filter(key="illustrator", value="studio atma")

    # Complex real-world queries
    def test_complex_class_effect_rarity(self):
        q = parse("class:mage o:banish -r:common")
        keys = [f.key for f in q.groups[0]]
        assert "class" in keys
        assert "effect" in keys
        assert "rarity" in keys

    def test_complex_legal_champion_level(self):
        q = parse("t:champion legal:p lvl<=3")
        group = q.groups[0]
        assert any(f.key == "type" and f.value == "champion" for f in group)
        assert any(f.key == "legal" and f.value == "p" for f in group)
        assert any(f.key == "level" and f.op == "<=" for f in group)


# ── is_client_side property ────────────────────────────────────────────────────

class TestIsClientSide:
    def test_client_side_keys(self):
        for key in ("cost", "cost_memory", "cost_reserve", "type", "subtype", "class",
                    "power", "life", "durability", "level", "oracle", "keyword"):
            assert Filter(key, "x").is_client_side, f"{key} should be client-side"

    def test_server_side_keys(self):
        for key in ("name", "effect", "element", "prefix", "rule", "flavor", "illustrator"):
            assert not Filter(key, "x").is_client_side, f"{key} should be server-side"

    def test_negated_forces_client_side(self):
        assert Filter("element", "fire", negated=True).is_client_side

    def test_non_eq_op_forces_client_side(self):
        assert Filter("element", "fire", op=">").is_client_side

    def test_valid_rarity_server_side(self):
        for alias in ("r", "c", "u", "rare", "common", "sr", "ur", "csr"):
            assert not Filter("rarity", alias).is_client_side, f"rarity:{alias} should be server-side"

    def test_invalid_rarity_client_side(self):
        assert Filter("rarity", "fake").is_client_side
        assert Filter("rarity", "").is_client_side

    def test_valid_format_server_side(self):
        for alias in ("standard", "s", "pantheon", "p", "draft", "d"):
            assert not Filter("legal", alias).is_client_side
            assert not Filter("banned", alias).is_client_side

    def test_invalid_format_client_side(self):
        assert Filter("legal",  "fake").is_client_side
        assert Filter("banned", "fake").is_client_side

    def test_valid_speed_server_side(self):
        assert not Filter("speed", "fast").is_client_side
        assert not Filter("speed", "slow").is_client_side

    def test_invalid_speed_client_side(self):
        assert Filter("speed", "xyz").is_client_side
        assert Filter("speed", "medium").is_client_side


# ── API param builder ──────────────────────────────────────────────────────────

class TestToApiParams:
    def test_name(self):
        assert to_api_params([Filter("name", "silvie")]) == {"name": "silvie"}

    def test_effect(self):
        assert to_api_params([Filter("effect", "banish")]) == {"effect": "banish"}

    def test_element_single(self):
        assert to_api_params([Filter("element", "fire")]) == {"element": "FIRE"}

    def test_element_alias(self):
        assert to_api_params([Filter("element", "fi")]) == {"element": "FIRE"}

    def test_element_multiple_becomes_list(self):
        params = to_api_params([Filter("element", "fire"), Filter("element", "water")])
        assert params["element"] == ["FIRE", "WATER"]

    def test_rarity_valid_sends_numeric(self):
        assert to_api_params([Filter("rarity", "rare")]) == {"rarity": 3}
        assert to_api_params([Filter("rarity", "sr")]) == {"rarity": 4}

    def test_rarity_invalid_excluded(self):
        assert to_api_params([Filter("rarity", "fake")]) == {}

    def test_type_known_sends_type_hint(self):
        params = to_api_params([Filter("type", "ally")])
        assert "type" in params
        assert "subtype" not in params

    def test_type_unknown_sends_subtype_hint(self):
        # HUMAN is not in _KNOWN_TYPES → routes to subtype
        params = to_api_params([Filter("type", "human")])
        assert "subtype" in params
        assert "type" not in params

    def test_multiple_same_subtype_only_first_hint(self):
        # two subtype filters: only first sent to API
        params = to_api_params([Filter("type", "human"), Filter("type", "elf")])
        assert "subtype" in params
        # must be scalar (single value), not a list
        assert params["subtype"] == "HUMAN"

    def test_multiple_diff_hint_keys_each_sent_once(self):
        # one type (ALLY→type) and one subtype (HUMAN→subtype) → both hints
        params = to_api_params([Filter("type", "ally"), Filter("type", "human")])
        assert "type" in params
        assert "subtype" in params

    def test_negated_type_no_hint(self):
        params = to_api_params([Filter("type", "ally", negated=True)])
        assert "type" not in params and "subtype" not in params

    def test_kw_sends_effect_proxy(self):
        assert to_api_params([Filter("keyword", "stealth")]) == {"effect": "stealth"}

    def test_oc_sends_effect_proxy(self):
        assert to_api_params([Filter("oracle", "banish")]) == {"effect": "banish"}

    def test_kw_and_oc_first_wins(self):
        # kw: sets effect first; oc: sees it occupied and skips
        params = to_api_params([Filter("keyword", "stealth"), Filter("oracle", "banish")])
        assert params["effect"] == "stealth"

    def test_legal_standard(self):
        params = to_api_params([Filter("legal", "standard")])
        assert params == {"legality_format": "STANDARD", "legality_state": "LEGAL"}

    def test_banned_pantheon(self):
        params = to_api_params([Filter("banned", "pantheon")])
        assert params == {"legality_format": "PANTHEON", "legality_state": "RESTRICTED"}

    def test_legal_invalid_excluded(self):
        assert to_api_params([Filter("legal", "fake")]) == {}

    def test_speed_valid(self):
        assert to_api_params([Filter("speed", "fast")]) == {"speed": "fast"}

    def test_speed_invalid_excluded(self):
        assert to_api_params([Filter("speed", "xyz")]) == {}

    def test_client_side_cost_excluded(self):
        assert to_api_params([Filter("cost", "3")]) == {}

    def test_numeric_op_excluded(self):
        assert to_api_params([Filter("power", "3", op=">=")]) == {}

    def test_set_prefix(self):
        assert to_api_params([Filter("prefix", "DOA")]) == {"prefix": "DOA"}

    def test_rule(self):
        assert to_api_params([Filter("rule", "graveyard")]) == {"rule": "graveyard"}

    def test_negated_element_excluded(self):
        # negated element is client-side, not sent to API
        assert to_api_params([Filter("element", "fire", negated=True)]) == {}


# ── Client-side filter (_check / apply_client_filters) ────────────────────────

class TestClientFilter:

    # type routing
    def test_type_known_matches_types_list(self):
        card = _card(types=["ALLY"])
        assert apply_client_filters([card], [Filter("type", "ally")]) == [card]

    def test_type_known_no_match(self):
        card = _card(types=["CHAMPION"])
        assert apply_client_filters([card], [Filter("type", "ally")]) == []

    def test_type_unknown_routes_to_subtypes(self):
        card = _card(types=["ALLY"], subtypes=["HUMAN"])
        assert apply_client_filters([card], [Filter("type", "human")]) == [card]

    def test_type_unknown_no_match(self):
        card = _card(types=["ALLY"], subtypes=["ELF"])
        assert apply_client_filters([card], [Filter("type", "human")]) == []

    # multiple subtypes AND (the core correctness case)
    def test_two_subtypes_both_required(self):
        human_elf  = _card(slug="he", subtypes=["HUMAN", "ELF"])
        human_only = _card(slug="ho", subtypes=["HUMAN"])
        filters = [Filter("type", "human"), Filter("type", "elf")]
        assert apply_client_filters([human_elf, human_only], filters) == [human_elf]

    # subtype
    def test_subtype_explicit(self):
        card = _card(subtypes=["DRAGON"])
        assert apply_client_filters([card], [Filter("subtype", "dragon")]) == [card]

    # class
    def test_class_matches(self):
        card = _card(classes=["MAGE"])
        assert apply_client_filters([card], [Filter("class", "mage")]) == [card]

    def test_class_no_match(self):
        card = _card(classes=["WARRIOR"])
        assert apply_client_filters([card], [Filter("class", "mage")]) == []

    def test_multiple_classes_and(self):
        dual  = _card(slug="d", classes=["MAGE", "WARRIOR"])
        single = _card(slug="s", classes=["MAGE"])
        filters = [Filter("class", "mage"), Filter("class", "warrior")]
        assert apply_client_filters([dual, single], filters) == [dual]

    # element — server-side when non-negated, test _check directly
    def test_element_matches(self):
        assert _check(_card(elements=["FIRE"]), Filter("element", "fire"))

    def test_element_alias(self):
        assert _check(_card(elements=["WATER"]), Filter("element", "wa"))

    def test_element_no_match(self):
        assert not _check(_card(elements=["WIND"]), Filter("element", "fire"))

    # negation
    def test_negated_element(self):
        fire  = _card(slug="fi", elements=["FIRE"])
        water = _card(slug="wa", elements=["WATER"])
        result = apply_client_filters([fire, water], [Filter("element", "fire", negated=True)])
        assert result == [water]

    def test_negated_type(self):
        ally  = _card(slug="al", types=["ALLY"])
        champ = _card(slug="ch", types=["CHAMPION"])
        result = apply_client_filters([ally, champ], [Filter("type", "ally", negated=True)])
        assert result == [champ]

    def test_negated_rarity(self):
        common = _card(slug="cm", editions=[CardEdition(slug="e1", rarity="1")])
        rare   = _card(slug="ra", editions=[CardEdition(slug="e2", rarity="3")])
        result = apply_client_filters([common, rare], [Filter("rarity", "common", negated=True)])
        assert result == [rare]

    # rarity comparison operators
    def test_rarity_greater_than(self):
        common = _card(slug="cm", editions=[CardEdition(slug="e1", rarity="1")])
        rare   = _card(slug="ra", editions=[CardEdition(slug="e2", rarity="3")])
        result = apply_client_filters([common, rare], [Filter("rarity", "c", op=">")])
        assert result == [rare]

    def test_rarity_greater_equal(self):
        rare = _card(slug="ra", editions=[CardEdition(slug="e1", rarity="4")])
        sr   = _card(slug="sr", editions=[CardEdition(slug="e2", rarity="4")])
        common = _card(slug="cm", editions=[CardEdition(slug="e3", rarity="1")])
        result = apply_client_filters([rare, sr, common], [Filter("rarity", "sr", op=">=")])
        assert result == [rare, sr]

    def test_rarity_less_equal(self):
        common = _card(slug="cm", editions=[CardEdition(slug="e1", rarity="1")])
        ultra  = _card(slug="ur", editions=[CardEdition(slug="e2", rarity="5")])
        result = apply_client_filters([common, ultra], [Filter("rarity", "u", op="<=")])
        assert result == [common]

    # oracle
    def test_oracle_substring(self):
        card = _card(effect="banish from memory")
        assert apply_client_filters([card], [Filter("oracle", "banish")]) == [card]

    def test_oracle_case_insensitive(self):
        card = _card(effect="BANISH TARGET CARD")
        assert apply_client_filters([card], [Filter("oracle", "banish")]) == [card]

    def test_oracle_no_match(self):
        card = _card(effect="draw a card")
        assert apply_client_filters([card], [Filter("oracle", "banish")]) == []

    def test_oracle_none_effect(self):
        card = _card(effect=None)
        assert apply_client_filters([card], [Filter("oracle", "banish")]) == []

    # keyword (bolded ability)
    def test_keyword_bold_matches(self):
        card = _card(effect="**Stealth** — This unit cannot be blocked.")
        assert apply_client_filters([card], [Filter("keyword", "Stealth")]) == [card]

    def test_keyword_plain_text_no_match(self):
        # "stealth" appears in prose but is NOT bolded → not a keyword
        card = _card(effect="This card has no stealth ability.")
        assert apply_client_filters([card], [Filter("keyword", "Stealth")]) == []

    def test_keyword_case_insensitive(self):
        card = _card(effect="**stealth**")
        assert apply_client_filters([card], [Filter("keyword", "Stealth")]) == [card]

    def test_keyword_multiword(self):
        card = _card(effect="**On Enter**: gain 1 memory.")
        assert apply_client_filters([card], [Filter("keyword", "On Enter")]) == [card]

    def test_keyword_partial_matches_full_name(self):
        # "float" is shorthand for the "Floating Memory" keyword
        card = _card(effect="**Floating Memory** — return this to your hand.")
        assert apply_client_filters([card], [Filter("keyword", "float")]) == [card]

    def test_keyword_partial_plain_text_no_match(self):
        card = _card(effect="This card can float around.")
        assert apply_client_filters([card], [Filter("keyword", "float")]) == []

    # rarity — valid values are server-side; test _check directly
    def test_rarity_common(self):
        card = _card(editions=[CardEdition(slug="e", rarity="1")])
        assert _check(card, Filter("rarity", "c"))

    def test_rarity_no_match(self):
        card = _card(editions=[CardEdition(slug="e", rarity="1")])
        assert not _check(card, Filter("rarity", "rare"))

    def test_rarity_invalid_never_matches(self):
        card = _card(editions=[CardEdition(slug="e", rarity="3")])
        assert apply_client_filters([card], [Filter("rarity", "fake")]) == []

    def test_rarity_result_editions_take_priority(self):
        # result_editions used when present — test via _check directly
        card = _card(
            editions=[CardEdition(slug="e1", rarity="1")],
            result_editions=[CardEdition(slug="e2", rarity="3")],
        )
        assert _check(card, Filter("rarity", "rare"))
        assert not _check(card, Filter("rarity", "common"))

    # numeric: power
    def test_power_gte_above(self):
        assert apply_client_filters([_card(power=5)], [Filter("power", "3", op=">=")]) == [_card(power=5)]

    def test_power_gte_equal(self):
        assert apply_client_filters([_card(power=3)], [Filter("power", "3", op=">=")]) != []

    def test_power_gte_below_no_match(self):
        assert apply_client_filters([_card(power=2)], [Filter("power", "3", op=">=")]) == []

    def test_power_gt_equal_no_match(self):
        assert apply_client_filters([_card(power=3)], [Filter("power", "3", op=">")]) == []

    def test_power_lte(self):
        assert apply_client_filters([_card(power=2)], [Filter("power", "3", op="<=")]) != []

    def test_power_lt_equal_no_match(self):
        assert apply_client_filters([_card(power=3)], [Filter("power", "3", op="<")]) == []

    def test_power_eq(self):
        assert apply_client_filters([_card(power=3)], [Filter("power", "3")]) != []
        assert apply_client_filters([_card(power=4)], [Filter("power", "3")]) == []

    def test_power_none_no_match(self):
        assert apply_client_filters([_card(power=None)], [Filter("power", "3", op=">=")]) == []

    # life
    def test_life_gte(self):
        card = _card(life=5)
        assert apply_client_filters([card], [Filter("life", "4", op=">=")]) == [card]
        assert apply_client_filters([_card(life=3)], [Filter("life", "4", op=">=")]) == []

    # level
    def test_level_lte(self):
        card = _card(level=2)
        assert apply_client_filters([card], [Filter("level", "3", op="<=")]) == [card]

    # cost: memory vs reserve vs generic
    def test_cost_memory_matches(self):
        card = _card(cost=CardCost(type="memory", value="2"))
        assert apply_client_filters([card], [Filter("cost_memory", "2")]) == [card]

    def test_cost_memory_no_match_on_reserve(self):
        card = _card(cost=CardCost(type="reserve", value="2"))
        assert apply_client_filters([card], [Filter("cost_memory", "2")]) == []

    def test_cost_reserve_matches(self):
        card = _card(cost=CardCost(type="reserve", value="3"))
        assert apply_client_filters([card], [Filter("cost_reserve", "3")]) == [card]

    def test_cost_reserve_no_match_on_memory(self):
        card = _card(cost=CardCost(type="memory", value="3"))
        assert apply_client_filters([card], [Filter("cost_reserve", "3")]) == []

    def test_cost_generic_matches_memory(self):
        card = _card(cost=CardCost(type="memory", value="3"))
        assert apply_client_filters([card], [Filter("cost", "3")]) == [card]

    def test_cost_generic_matches_reserve(self):
        card = _card(cost=CardCost(type="reserve", value="3"))
        assert apply_client_filters([card], [Filter("cost", "3")]) == [card]

    def test_cost_none_type_no_match(self):
        card = _card(cost=CardCost(type="none"))
        assert apply_client_filters([card], [Filter("cost", "0")]) == []

    def test_cost_operator_gte(self):
        cheap = _card(slug="c1", cost=CardCost(type="memory", value="1"))
        expensive = _card(slug="c3", cost=CardCost(type="memory", value="3"))
        result = apply_client_filters([cheap, expensive], [Filter("cost_memory", "2", op=">=")])
        assert expensive in result
        assert cheap not in result

    # speed — valid values are server-side; test _check directly
    def test_speed_fast_matches(self):
        assert _check(_card(speed="fast"), Filter("speed", "fast"))

    def test_speed_slow_no_match_fast(self):
        assert not _check(_card(speed="slow"), Filter("speed", "fast"))

    def test_speed_none_no_match(self):
        assert not _check(_card(speed=None), Filter("speed", "fast"))

    # legal/banned are always False client-side (invalid values only reach here)
    def test_legal_invalid_always_false(self):
        assert apply_client_filters([_card()], [Filter("legal", "fake")]) == []

    # server-side filter not applied client-side
    def test_server_side_filter_passes_all(self):
        fire  = _card(slug="fi", elements=["FIRE"])
        water = _card(slug="wa", elements=["WATER"])
        f = Filter("element", "fire")
        assert not f.is_client_side
        # apply_client_filters skips server-side, so both pass
        assert apply_client_filters([fire, water], [f]) == [fire, water]

    # complex AND combinations
    def test_combined_type_class_filters(self):
        match   = _card(slug="m", types=["ALLY"], classes=["MAGE"], subtypes=["HUMAN"])
        no_cls  = _card(slug="n1", types=["ALLY"], classes=["WARRIOR"], subtypes=["HUMAN"])
        no_sub  = _card(slug="n2", types=["ALLY"], classes=["MAGE"],    subtypes=["ELF"])
        filters = [Filter("type", "human"), Filter("class", "mage")]
        assert apply_client_filters([match, no_cls, no_sub], filters) == [match]

    def test_negated_combined_with_positive(self):
        rare_fire   = _card(slug="rf", elements=["FIRE"],  editions=[CardEdition(slug="e1", rarity="3")])
        common_fire = _card(slug="cf", elements=["FIRE"],  editions=[CardEdition(slug="e2", rarity="1")])
        filters = [Filter("rarity", "common", negated=True)]
        result = apply_client_filters([rare_fire, common_fire], filters)
        assert rare_fire in result
        assert common_fire not in result


# ── Warnings ───────────────────────────────────────────────────────────────────

class TestWarnings:
    def test_no_warnings_for_valid_query(self):
        q = parse("t:ally e:fire")
        assert q.warnings == []

    def test_unknown_key_produces_warning(self):
        q = parse("wrongkey:creature")
        assert len(q.warnings) == 1
        assert "wrongkey:" in q.warnings[0]
        assert "unknown filter key" in q.warnings[0]

    def test_unknown_key_not_added_to_name(self):
        q = parse("wrongkey:creature")
        # should not produce a name filter
        keys = [f.key for g in q.groups for f in g]
        assert "name" not in keys

    def test_valid_filter_after_unknown_key_still_parsed(self):
        q = parse("wrongkey:creature e:fire")
        assert len(q.warnings) == 1
        keys = [f.key for g in q.groups for f in g]
        assert "element" in keys

    def test_numeric_op_on_non_numeric_key_warns(self):
        q = parse("e>fire")
        assert len(q.warnings) == 1
        assert "not valid" in q.warnings[0]
        assert "e:" in q.warnings[0]

    def test_numeric_op_on_numeric_key_no_warning(self):
        q = parse("pow>=3")
        assert q.warnings == []
        assert q.groups[0][0].key == "power"
        assert q.groups[0][0].op == ">="

    def test_multiple_unknown_keys_each_warn(self):
        q = parse("foo:a bar:b")
        assert len(q.warnings) == 2

    def test_all_invalid_groups_produce_empty_groups(self):
        # all tokens are unknown keys — groups should collapse to [[]]
        q = parse("foo:a bar:b")
        # The fallback is [[]] which contains one empty group
        assert all(len(g) == 0 for g in q.groups)

    def test_unknown_key_in_or_group(self):
        q = parse("t:ally OR wrongkey:foo")
        # ally group should be present; warnings for wrongkey
        assert any(any(f.key == "type" for f in g) for g in q.groups)
        assert len(q.warnings) == 1

    def test_plain_text_no_warning(self):
        q = parse("silvie dungeon")
        assert q.warnings == []
        keys = [f.key for g in q.groups for f in g]
        assert "name" in keys

    def test_negated_unknown_key_warns(self):
        q = parse("-wrongkey:foo")
        assert len(q.warnings) == 1
        assert "wrongkey:" in q.warnings[0]

    def test_valid_and_invalid_mixed_in_parens(self):
        q = parse("(t:ally OR wrongkey:foo) e:fire")
        assert len(q.warnings) == 1
        # fire element should be distributed into the valid group
        assert any(
            any(f.key == "element" for f in g)
            for g in q.groups
        )
