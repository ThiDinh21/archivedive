from __future__ import annotations

from textual import on, work
from textual.app import ComposeResult
from textual.binding import Binding
from textual.screen import Screen
from textual.timer import Timer
from textual.widgets import Footer, Header, Input, Label

from ..models import SearchResponse
from ..widgets.card_table import CardTable


class SearchScreen(Screen):

    BINDINGS = [
        Binding("ctrl+left", "prev_page", "Prev page"),
        Binding("ctrl+right", "next_page", "Next page"),
    ]

    DEFAULT_CSS = """
    SearchScreen {
        layout: vertical;
    }
    #search-input {
        margin: 1 2;
    }
    CardTable {
        height: 1fr;
        margin: 0 2;
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
        yield CardTable(id="card-table")
        yield Label("Loading…", id="status")
        yield Footer()

    def on_mount(self) -> None:
        self._load_initial()

    @work(exclusive=True)
    async def _load_initial(self) -> None:
        client = self.app.client  # type: ignore[attr-defined]
        cards = await client.random(count=50)
        self.query_one(CardTable).populate(cards)
        self._set_status(len(cards), 1, 1)

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

    def on_key(self, event: object) -> None:
        from textual.events import Key
        if not isinstance(event, Key):
            return
        focused = self.focused
        if isinstance(focused, Input) and event.key == "down":
            self.query_one(CardTable).focus()
            event.stop()
        elif isinstance(focused, CardTable) and event.key in ("escape", "s"):
            self.query_one(Input).focus()
            event.stop()
        elif isinstance(focused, CardTable) and event.key == "up" and focused.cursor_row == 0:
            self.query_one(Input).focus()
            event.stop()

    @work(exclusive=True)
    async def _do_search(self) -> None:
        query = self._last_query.strip()
        client = self.app.client  # type: ignore[attr-defined]

        if not query:
            cards = await client.random(count=50)
            self.query_one(CardTable).populate(cards)
            self._set_status(len(cards), 1, 1)
            return

        result: SearchResponse = await client.search(name=query, page=self._page)
        self.query_one(CardTable).populate(result.data)
        self._total_pages = result.total_pages
        self._total_cards = result.total_cards
        self._set_status(result.total_cards, self._page, result.total_pages)

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
        nav_hint = "  |  [ / ] to paginate" if total_pages > 1 else ""
        self.query_one("#status", Label).update(
            f"{total} cards{page_info}{nav_hint}  |  enter to view card"
        )
