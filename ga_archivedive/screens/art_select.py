import webbrowser

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList


class ArtSelectScreen(ModalScreen[None]):

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    ArtSelectScreen {
        align: center middle;
    }
    #dialog {
        width: 60;
        max-height: 24;
        border: tall $primary;
        background: $surface;
        padding: 1 2;
    }
    #title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, options: list[tuple[str, str]]) -> None:
        super().__init__()
        self._options = options  # [(label, url), ...]

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Open card art", id="title")
            yield OptionList(*[label for label, _ in self._options])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        _, url = self._options[event.option_index]
        webbrowser.open(url)
        self.dismiss()
