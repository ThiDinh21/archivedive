from __future__ import annotations

import io

from PIL import Image as PILImage
from textual import work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Static

from ..models import Card

_PLACEHOLDER = "[dim]Select a card to see details[/dim]"
_IMAGE_WIDTH = 40


def _image_to_blocks(image_bytes: bytes, width: int = _IMAGE_WIDTH) -> str:
    img = PILImage.open(io.BytesIO(image_bytes)).convert("RGB")
    aspect = img.height / img.width
    char_height = max(1, int(width * aspect / 2))
    img = img.resize((width, char_height * 2), PILImage.LANCZOS)
    pixels = list(img.getdata())
    lines: list[str] = []
    for row in range(char_height):
        line = ""
        for col in range(width):
            tr, tg, tb = pixels[row * 2 * width + col]
            br, bg, bb = pixels[(row * 2 + 1) * width + col]
            top_lum = tr * 0.299 + tg * 0.587 + tb * 0.114
            bot_lum = br * 0.299 + bg * 0.587 + bb * 0.114
            char = "▄" if top_lum > bot_lum else "▀"
            line += f"[rgb({tr},{tg},{tb}) on rgb({br},{bg},{bb})]{char}[/]"
        lines.append(line)
    return "\n".join(lines)


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
    #card-image {
        width: 1fr;
        margin-bottom: 1;
    }
    #card-image.hidden {
        display: none;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._current_card: Card | None = None

    def compose(self) -> ComposeResult:
        yield Static("", id="card-image", classes="hidden", markup=True)
        yield Static(_PLACEHOLDER, id="panel-content", markup=True)

    def show(self, card: Card) -> None:
        self._current_card = card
        self.scroll_home(animate=False)
        self.query_one("#panel-content", Static).update(_render(card))
        if card.image_filename:
            self.query_one("#card-image", Static).add_class("hidden")
            self._load_image(card.image_filename)
        else:
            self.query_one("#card-image", Static).add_class("hidden")

    def clear(self) -> None:
        self._current_card = None
        self.query_one("#card-image", Static).add_class("hidden")
        self.query_one("#panel-content", Static).update(_PLACEHOLDER)

    def action_copy_card(self) -> None:
        if self._current_card is None:
            return
        _copy_to_clipboard(_plain_text(self._current_card))
        self.app.notify(f"Copied: {self._current_card.name}", timeout=2)

    @work(exclusive=True)
    async def _load_image(self, filename: str) -> None:
        import asyncio
        import traceback
        image_widget = self.query_one("#card-image", Static)
        try:
            client = self.app.client  # type: ignore[attr-defined]
            image_data = await client.fetch_image(filename)
            loop = asyncio.get_event_loop()
            markup = await loop.run_in_executor(None, lambda: _image_to_blocks(image_data))
            image_widget.update(markup)
            image_widget.remove_class("hidden")
        except Exception:
            image_widget.update(f"[red]{traceback.format_exc()}[/red]")
            image_widget.remove_class("hidden")
