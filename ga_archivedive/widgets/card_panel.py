from __future__ import annotations

import re
import webbrowser

_RE_BOLD = re.compile(r'\*\*(.+?)\*\*')
_RE_ITALIC = re.compile(r'\*(.+?)\*')

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..models import Card
from ..api import BASE_URL
from .. import copy_to_clipboard

_PLACEHOLDER = "[dim]Select a card to see details[/dim]"

_SYMBOLS_RICH = {
    "POWER": "[red]⚔[/red]",
    "LIFE":  "[green]♥[/green]",
    "REST":  "[bright_white]↷[/bright_white]",
}
_SYMBOLS_PLAIN = {"POWER": "⚔", "LIFE": "♥", "REST": "↷"}


def _short_name(card_name: str) -> str:
    return card_name.split(",")[0].strip()


def _sub_symbols(text: str, card_name: str, symbol_map: dict[str, str]) -> str:
    text = text.replace("CARDNAME", _short_name(card_name))
    for token, replacement in symbol_map.items():
        text = text.replace(f"[{token}]", replacement)
    return text


def _to_rich(text: str, card_name: str = "") -> str:
    """Convert GA API markdown and symbol placeholders to Rich markup."""
    text = _sub_symbols(text, card_name, _SYMBOLS_RICH)
    text = _RE_BOLD.sub(r'[bold]\1[/bold]', text)
    text = _RE_ITALIC.sub(r'[italic]\1[/italic]', text)
    return text


def _to_plain(text: str, card_name: str = "") -> str:
    """Strip GA API markdown and replace symbol placeholders for plain text."""
    text = _sub_symbols(text, card_name, _SYMBOLS_PLAIN)
    text = _RE_BOLD.sub(r'\1', text)
    text = _RE_ITALIC.sub(r'\1', text)
    return text


def _stat(label: str, value: object) -> str:
    return f"[dim]{label}[/dim] [bold]{value if value is not None else '—'}[/bold]"


def _section(title: str) -> str:
    return f"\n[dim]─── {title} {'─' * max(0, 24 - len(title))}[/dim]\n"


def _render(card: Card) -> str:
    parts: list[str] = []

    editions_with_images = [
        ed for ed in (card.result_editions or card.editions) if ed.image
    ]

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
        parts.append(_to_rich(effect, card.name))

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
            ed_parts.append(ed.rarity_name or ed.rarity)
        if ed.set and ed.set.name:
            ed_parts.append(ed.set.name)
        if ed.illustrator:
            ed_parts.append(f"[dim]by {ed.illustrator}[/dim]")
        parts.append("  •  ".join(ed_parts))

    parts.append(_section("Legality"))
    legality = card.legality or {}
    for fmt in ("STANDARD", "PANTHEON", "DRAFT"):
        info = legality.get(fmt)
        if info is None:
            status = "[green]Legal[/green]"
        else:
            limit = info.get("limit", 0)
            status = "[red]Banned[/red]" if limit == 0 else f"[yellow]Restricted ({limit})[/yellow]"
        parts.append(f"[dim]{fmt.capitalize():<10}[/dim] {status}")

    all_refs = card.references + card.referenced_by
    if all_refs:
        parts.append(_section("Related"))
        for ref in card.references:
            kind = f"[dim][{ref.kind}][/dim]" if ref.kind else ""
            parts.append(f"[dim]→[/dim] {ref.name}  {kind}")
        for ref in card.referenced_by:
            kind = f"[dim][{ref.kind}][/dim]" if ref.kind else ""
            parts.append(f"[dim]←[/dim] {ref.name}  {kind}")
        parts.append(f"[dim]r → open related card[/dim]")

    if card.rule:
        parts.append(_section("Rule"))
        parts.append(f"[dim]{_to_rich(card.rule, card.name)}[/dim]")

    if editions_with_images:
        parts.append(_section("Images"))
        numbered = editions_with_images[:9]
        overflow = editions_with_images[9:]
        if len(editions_with_images) > 1:
            keys = " ".join(f"[bold cyan]{i}[/bold cyan]" for i in range(1, len(numbered) + 1))
            hint = f"[dim]Press {keys} to open · o opens latest[/dim]"
            if overflow:
                hint += f"[dim] · +{len(overflow)} more (copy URL)[/dim]"
            parts.append(hint)
        for i, ed in enumerate(numbered, 1):
            label_parts: list[str] = []
            if ed.rarity:
                label_parts.append(ed.rarity_name or ed.rarity)
            if ed.set and ed.set.name:
                label_parts.append(ed.set.name)
            label = "  •  ".join(label_parts) if label_parts else "Edition"
            parts.append(f"[bold cyan]\\[{i}][/bold cyan] [dim]{label}[/dim]")
            parts.append(f"[dim]{BASE_URL}{ed.image}[/dim]")
        for ed in overflow:
            label_parts = []
            if ed.rarity:
                label_parts.append(ed.rarity_name or ed.rarity)
            if ed.set and ed.set.name:
                label_parts.append(ed.set.name)
            label = "  •  ".join(label_parts) if label_parts else "Edition"
            parts.append(f"[dim]    {label}[/dim]")
            parts.append(f"[dim]{BASE_URL}{ed.image}[/dim]")
        if len(editions_with_images) == 1:
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
        lines.append(f"\n{_to_plain(effect, card.name)}")
    return "\n".join(lines)


class CardPanel(VerticalScroll):

    can_focus = True

    BINDINGS = [
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
        try:
            copy_to_clipboard(_plain_text(self._current_card))
            self.app.notify(f"Copied: {self._current_card.name}", timeout=2)
        except RuntimeError as e:
            self.app.notify(str(e), severity="error", timeout=4)

    def action_open_image(self) -> None:
        urls = self._image_urls()
        if not urls:
            return
        webbrowser.open(urls[-1])
        self.app.notify("Opening latest printing in browser…", timeout=2)

    def on_key(self, event: object) -> None:
        from textual.events import Key
        if not isinstance(event, Key):
            return
        if event.key.isdigit():
            idx = int(event.key) - 1
            urls = self._image_urls()
            if 0 <= idx < len(urls):
                webbrowser.open(urls[idx])
                self.app.notify(f"Opening image {idx + 1} in browser…", timeout=2)
                event.stop()

    def _image_urls(self) -> list[str]:
        if self._current_card is None:
            return []
        editions = self._current_card.result_editions or self._current_card.editions
        return [f"{BASE_URL}{ed.image}" for ed in editions if ed.image]
