from __future__ import annotations

from textual.app import ComposeResult
from textual.widget import Widget
from textual.widgets import Static
from textual.scroll_view import ScrollView
from textual.containers import VerticalScroll

from ..models import Card

_PLACEHOLDER = "[dim]Select a card to see details[/dim]"


def _stat(label: str, value: object) -> str:
    return f"[dim]{label}[/dim] [bold]{value if value is not None else '—'}[/bold]"


def _section(title: str) -> str:
    return f"\n[dim]─── {title} {'─' * max(0, 24 - len(title))}[/dim]\n"


def _render(card: Card) -> str:
    parts: list[str] = []

    # Name
    parts.append(f"[bold yellow]{card.name}[/bold yellow]")

    # Type line
    if card.display_types:
        parts.append(f"[cyan]{card.display_types}[/cyan]")

    # Element + cost
    meta: list[str] = []
    if card.elements:
        meta.append(f"[green]{card.display_elements}[/green]")
    if card.cost and card.cost.type != "none":
        meta.append(f"Cost [magenta]{card.display_cost}[/magenta]")
    if meta:
        parts.append("  ".join(meta))

    # Effect
    effect = card.effect or (card.editions[0].effect if card.editions else None)
    if effect:
        parts.append(_section("Effect"))
        parts.append(effect)

    # Stats
    has_stats = any(
        v is not None for v in [card.power, card.life, card.level, card.durability]
    )
    if has_stats or card.speed:
        parts.append(_section("Stats"))
        row1 = "  ".join([
            _stat("ATK", card.power),
            _stat("HP", card.life),
            _stat("DUR", card.durability),
        ])
        row2 = "  ".join([
            _stat("LVL", card.level),
            _stat("SPD", card.speed or "—"),
        ])
        parts.append(row1)
        parts.append(row2)

    # Edition info
    editions = card.result_editions or card.editions
    if editions:
        ed = editions[0]
        parts.append(_section("Edition"))
        ed_parts: list[str] = []
        if ed.rarity:
            ed_parts.append(ed.rarity.capitalize())
        if ed.set and ed.set.name:
            ed_parts.append(ed.set.name)
        if ed.illustrator:
            ed_parts.append(f"[dim]by {ed.illustrator}[/dim]")
        parts.append("  •  ".join(ed_parts))

    # Rule
    if card.rule:
        parts.append(_section("Rule"))
        parts.append(f"[dim]{card.rule}[/dim]")

    # Flavor
    flavor = card.flavor or (editions[0].flavor if editions else None)
    if flavor:
        parts.append(_section("Flavor"))
        parts.append(f"[italic dim]\"{flavor}\"[/italic dim]")

    return "\n".join(parts)


class CardPanel(Widget):

    DEFAULT_CSS = """
    CardPanel {
        width: 42;
        border-left: tall $primary-darken-2;
        padding: 1 2;
        background: $surface;
    }
    CardPanel VerticalScroll {
        width: 1fr;
        height: 1fr;
        scrollbar-size: 1 1;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Static(_PLACEHOLDER, id="panel-content", markup=True)

    def show(self, card: Card) -> None:
        self.query_one("#panel-content", Static).update(_render(card))

    def clear(self) -> None:
        self.query_one("#panel-content", Static).update(_PLACEHOLDER)
