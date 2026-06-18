from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Label, OptionList

from ..models import CardReference


class RelatedCardsScreen(ModalScreen[str | None]):

    BINDINGS = [Binding("escape", "dismiss", "Close")]

    DEFAULT_CSS = """
    RelatedCardsScreen {
        align: center middle;
    }
    #dialog {
        width: 60;
        max-height: 30;
        border: tall $primary;
        background: $surface;
        padding: 1 2;
    }
    #title {
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def __init__(self, references: list[CardReference], referenced_by: list[CardReference]) -> None:
        super().__init__()
        self._options: list[tuple[str, str]] = []
        for ref in references:
            kind = f"[{ref.kind}]" if ref.kind else ""
            self._options.append((f"→ {ref.name}  {kind}", ref.slug))
        for ref in referenced_by:
            kind = f"[{ref.kind}]" if ref.kind else ""
            self._options.append((f"← {ref.name}  {kind}", ref.slug))

    def compose(self) -> ComposeResult:
        with Vertical(id="dialog"):
            yield Label("Related cards  (→ references  ← referenced by)", id="title")
            yield OptionList(*[label for label, _ in self._options])

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        _, slug = self._options[event.option_index]
        self.dismiss(slug)
