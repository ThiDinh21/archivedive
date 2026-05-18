from __future__ import annotations

import webbrowser

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..models import Card
from ..api import BASE_URL

_PLACEHOLDER = "[dim]Select a card to see details[/dim]"


def _stat(label: str, value: object) -> str:
    return f"[dim]{label}[/dim] [bold]{value if value is not None else '—'}[/bold]"


def _section(title: str) -> str:
    return f"\n[dim]─── {title} {'─' * max(0, 24 - len(title))}[/dim]\n"


def _render(card: Card) -> str:
    parts: list[str] = []

    parts.append(f"[bold yellow]{card.name}[/bold yellow]")
    if card.display_types:
        parts.append(f"[cyan]{card.display_types}[/cyan]")

    meta: list[str] = []
    if card.elements:
        meta.append(f"[green]{card.display_elements}[/green]")
    if card.cost and card.cost.type != "none":
        meta.append(f"Cost [magenta]{card.display_cost}[/magenta]")
    if meta:
        parts.append("  ".join(meta))

    effect = card.effect or (card.editions[0].effect if card.editions else None)
    if effect:
        parts.append(_section("Effect"))
        parts.append(effect)

    has_stats = any(v is not None for v in [card.power, card.life, card.level, card.durability])
    if has_stats or card.speed:
        parts.append(_section("Stats"))
        parts.append("  ".join([
            _stat("ATK", card.power),
            _stat("HP", card.life),
            _stat("DUR", card.durability),
        ]))
        parts.append("  ".join([_stat("LVL", card.level), _stat("SPD", card.speed or "—")]))

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

    if card.rule:
        parts.append(_section("Rule"))
        parts.append(f"[dim]{card.rule}[/dim]")

    if card.image_filename:
        parts.append(_section("Image"))
        parts.append(f"[dim]{BASE_URL}{card.image_filename}[/dim]")
        parts.append("[dim]o → open in browser[/dim]")

    flavor = card.flavor or (editions[0].flavor if editions else None)
    if flavor:
        parts.append(_section("Flavor"))
        parts.append(f'[italic dim]"{flavor}"[/italic dim]')

    return "\n".join(parts)


def _plain_text(card: Card) -> str:
    lines = [card.name, card.display_types]
    if card.elements:
        lines.append(card.display_elements)
    if card.cost and card.cost.type != "none":
        lines.append(f"Cost: {card.display_cost}")
    effect = card.effect or (card.editions[0].effect if card.editions else None)
    if effect:
        lines.append(f"\n{effect}")
    if card.rule:
        lines.append(f"\nRule: {card.rule}")
    return "\n".join(lines)


def _copy_to_clipboard(text: str) -> None:
    import subprocess
    for cmd in (["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        try:
            subprocess.run(cmd, input=text.encode(), check=True, capture_output=True)
            return
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    raise RuntimeError("No clipboard tool found (install xclip or xsel)")


class CardPanel(VerticalScroll):

    can_focus = True

    BINDINGS = [
        Binding("o", "open_image", "Open image", show=False),
        Binding("ctrl+shift+c", "copy_card", "Copy card text", show=False),
    ]

    DEFAULT_CSS = """
    CardPanel {
        width: 42;
        border-left: tall $primary-darken-2;
        padding: 1 2;
        background: $surface;
        scrollbar-size: 1 1;
    }
    CardPanel:focus {
        background: $surface-lighten-1;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._current_card: Card | None = None

    def compose(self) -> ComposeResult:
        yield Static(_PLACEHOLDER, id="panel-content", markup=True)

    def show(self, card: Card) -> None:
        self._current_card = card
        self.scroll_home(animate=False)
        self.query_one("#panel-content", Static).update(_render(card))

    def clear(self) -> None:
        self._current_card = None
        self.query_one("#panel-content", Static).update(_PLACEHOLDER)

    def action_copy_card(self) -> None:
        if self._current_card is None:
            return
        _copy_to_clipboard(_plain_text(self._current_card))
        self.app.notify(f"Copied: {self._current_card.name}", timeout=2)

    def action_open_image(self) -> None:
        if self._current_card is None or not self._current_card.image_filename:
            return
        webbrowser.open(f"{BASE_URL}{self._current_card.image_filename}")
        self.app.notify("Opening image in browser…", timeout=2)
