from textual import work
from textual.app import App
from textual.binding import Binding

from .api import GAClient
from .screens.search import SearchScreen


class ArchiveDiveApp(App):
    TITLE = "ArchiveDive"
    SUB_TITLE = "Grand Archive card browser"

    BINDINGS = [
        Binding("f1", "help", "Syntax help", priority=True, key_display="F1", show=False),
        Binding("?", "help", "Syntax help", priority=True, show=False),
    ]

    def __init__(self) -> None:
        super().__init__()
        self.client = GAClient()

    def on_mount(self) -> None:
        self.push_screen(SearchScreen())
        self._load_known_types()

    @work(thread=False)
    async def _load_known_types(self) -> None:
        from .query import set_known_types
        types = await self.client.fetch_known_types()
        set_known_types(types)

    def action_help(self) -> None:
        from .screens.help import HelpScreen
        if isinstance(self.screen, HelpScreen):
            self.pop_screen()
        else:
            self.push_screen(HelpScreen())

    async def on_unmount(self) -> None:
        await self.client.close()


def main() -> None:
    ArchiveDiveApp().run()
