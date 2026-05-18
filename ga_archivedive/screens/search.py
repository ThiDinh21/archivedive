from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, Input, Label

from ..models import SearchResponse
from ..api import BASE_URL
from ..widgets.card_panel import CardPanel
from ..widgets.card_table import CardTable


class SearchScreen(Screen):

    BINDINGS = [
        Binding("ctrl+left", "prev_page", "Prev page", key_display="ctrl+<"),
        Binding("ctrl+right", "next_page", "Next page", key_display="ctrl+>"),
        Binding("s", "focus_search", "Search"),
        Binding("c", "copy_card", "Copy card"),
        Binding("o", "open_image", "Open image"),
        Binding("ctrl+o", "select_art", "Select art", key_display="ctrl+o"),
    ]

    DEFAULT_CSS = """
    SearchScreen {
        layout: vertical;
    }
    #search-input {
        margin: 1 2;
    }
    #main-content {
        height: 1fr;
    }
    CardTable {
        width: 1fr;
        margin: 0 0 0 2;
    }
    CardTable:focus {
        background: $surface-lighten-1;
    }
    #status {
        margin: 0 2 1 2;
        height: 1;
        color: $text-muted;
    }
    """

    def __init__(self) -> None:
        super().__init__()
        self._search_timer: Timer | None = None
        self._page = 1
        self._total_pages = 1
        self._total_cards = 0
        self._last_query = ""

    def compose(self) -> ComposeResult:
        yield Header()
        yield Input(placeholder="Search cards… (name, effect, type)", id="search-input")
        with Horizontal(id="main-content"):
            yield CardTable(id="card-table")
            yield CardPanel(id="card-panel")
        yield Label("Loading…", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_initial()

    @work(exclusive=True)
    async def _load_initial(self) -> None:
        table = self.query_one(CardTable)
        table.loading = True
        try:
            client = self.app.client  # type: ignore[attr-defined]
            cards = await client.random(count=50)
            table.populate(cards)
            self._set_status(len(cards), 1, 1)
        finally:
            table.loading = False

    @on(Input.Changed, "#search-input")
    def on_search_changed(self, event: Input.Changed) -> None:
        if self._search_timer:
            self._search_timer.stop()
        self._last_query = event.value
        self._page = 1
        self._search_timer = self.set_timer(0.4, self._do_search)

    @on(Input.Submitted, "#search-input")
    def on_search_submitted(self, event: Input.Submitted) -> None:
        self.query_one(CardTable).focus()

    @on(CardTable.CardHighlighted)
    def on_card_highlighted(self, event: CardTable.CardHighlighted) -> None:
        self.query_one(CardPanel).show(event.card)

    def on_key(self, event: object) -> None:
        from textual.events import Key
        if not isinstance(event, Key):
            return
        focused = self.focused
        if isinstance(focused, Input) and event.key in ("down", "escape"):
            self.query_one(CardTable).focus()
            event.stop()
        elif isinstance(focused, CardTable) and event.key == "escape":
            self.query_one(Input).focus()
            event.stop()
        elif isinstance(focused, CardTable) and event.key == "up" and focused.cursor_row == 0:
            self.query_one(Input).focus()
            event.stop()
        elif isinstance(focused, CardTable) and event.key == "right":
            self.query_one(CardPanel).focus()
            event.stop()
        elif isinstance(focused, CardPanel) and event.key == "left":
            self.query_one(CardTable).focus()
            event.stop()
        elif event.key.isdigit() and not isinstance(focused, Input):
            self.query_one(CardPanel).on_key(event)

    @work(exclusive=True)
    async def _do_search(self) -> None:
        table = self.query_one(CardTable)
        table.loading = True
        try:
            query = self._last_query.strip()
            client = self.app.client  # type: ignore[attr-defined]

            if not query:
                cards = await client.random(count=50)
                table.populate(cards)
                self._set_status(len(cards), 1, 1)
                return

            result: SearchResponse = await client.search_query(query, page=self._page)
            table.populate(result.data)
            self._total_pages = result.total_pages
            self._total_cards = result.total_cards
            self._set_status(result.total_cards, self._page, result.total_pages)
        finally:
            table.loading = False

    def action_focus_search(self) -> None:
        self.query_one(Input).focus()

    def action_copy_card(self) -> None:
        self.query_one(CardPanel).action_copy_card()

    def action_open_image(self) -> None:
        self.query_one(CardPanel).action_open_image()

    def action_select_art(self) -> None:
        from .art_select import ArtSelectScreen
        panel = self.query_one(CardPanel)
        card = panel._current_card
        if card is None:
            return
        editions = card.result_editions or card.editions
        options: list[tuple[str, str]] = []
        for ed in editions:
            if not ed.image:
                continue
            label_parts: list[str] = []
            if ed.rarity:
                label_parts.append(ed.rarity.capitalize())
            if ed.set and ed.set.name:
                label_parts.append(ed.set.name)
            if ed.illustrator:
                label_parts.append(f"by {ed.illustrator}")
            label = "  •  ".join(label_parts) if label_parts else "Edition"
            options.append((label, f"{BASE_URL}{ed.image}"))
        if not options:
            return
        self.app.push_screen(ArtSelectScreen(options))

    def action_prev_page(self) -> None:
        if self._page > 1:
            self._page -= 1
            self._do_search()

    def action_next_page(self) -> None:
        if self._page < self._total_pages:
            self._page += 1
            self._do_search()

    def _set_status(self, total: int, page: int, total_pages: int) -> None:
        page_info = f"  |  page {page}/{total_pages}" if total_pages > 1 else ""
        nav_hint = "  |  ctrl+←/→ to paginate" if total_pages > 1 else ""
        self.query_one("#status", Label).update(
            f"{total} cards{page_info}{nav_hint}"
        )
