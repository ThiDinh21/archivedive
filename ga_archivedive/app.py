from textual.app import App

from .api import GAClient
from .screens.search import SearchScreen


class ArchiveDiveApp(App):
    TITLE = "ArchiveDive"
    SUB_TITLE = "Grand Archive card browser"

    def __init__(self) -> None:
        super().__init__()
        self.client = GAClient()

    def on_mount(self) -> None:
        self.push_screen(SearchScreen())

    async def on_unmount(self) -> None:
        await self.client.close()


def main() -> None:
    ArchiveDiveApp().run()
