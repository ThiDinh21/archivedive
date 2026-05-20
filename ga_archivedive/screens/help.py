from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

def _row(example: str, desc: str, width: int = 26) -> str:
    """Build a padded two-column row, accounting for visible chars only."""
    visible = example.replace("[cyan]", "").replace("[/cyan]", "")
    pad = " " * max(1, width - len(visible))
    return f"{example}{pad}{desc}"


_C = "[cyan]"
_E = "[/cyan]"

_CONTENT = (
    f"[bold yellow]Search Syntax Reference[/bold yellow]\n"
    f"\n"
    f"[dim]key:value filters combined with AND (element uses OR). F1 or esc to close.[/dim]\n"
    f"[dim]ctrl+c copies search bar text · ctrl+q to quit[/dim]\n"
    f"\n"
    f"[bold]── Text ─────────────────────────────────[/bold]\n"
    + "\n".join([
        _row(f"{_C}silvie{_E}",              "name search (fuzzy)"),
        _row(f"{_C}o:banish{_E}",            "effect text (any edition)"),
        _row(f"{_C}oc:banish{_E}",           "effect text (canonical only)"),
        _row(f"{_C}kw:stealth{_E}",          "keyword ability (exact)"),
        _row(f"{_C}rule:graveyard{_E}",      "rule text"),
        _row(f"{_C}flavor:courage{_E}",      "flavor text"),
        _row(f"{_C}ill:akira{_E}",           "illustrator"),
    ]) + "\n"
    f"\n"
    f"[bold]── Card attributes ──────────────────────[/bold]\n"
    + "\n".join([
        _row(f"{_C}t:ally{_E}  {_C}t:human{_E}",    "type or subtype"),
        _row(f"{_C}class:mage{_E}",                  "class"),
        _row(f"{_C}e:fire{_E}  {_C}e:wa{_E}",        "element  (aliases: fi wa wi cr no)"),
        _row(f"{_C}r:rare{_E}  {_C}r:csr{_E}",       "rarity"),
        _row(f"{_C}set:DOA{_E}",                      "set prefix code"),
        _row(f"{_C}speed:fast{_E}",                   "speed"),
    ]) + "\n"
    f"\n"
    f"[bold]── Costs ────────────────────────────────[/bold]\n"
    + "\n".join([
        _row(f"{_C}cost:3{_E}",   "memory or reserve (either)"),
        _row(f"{_C}m:3{_E}",      "memory cost only"),
        _row(f"{_C}res:2{_E}",    "reserve cost only"),
    ]) + "\n"
    f"\n"
    f"[bold]── Stats  (= > < >= <=) ─────────────────[/bold]\n"
    + "\n".join([
        _row(f"{_C}pow:3{_E}  {_C}pow>=3{_E}",     "power"),
        _row(f"{_C}life:4{_E}  {_C}life<=5{_E}",   "life"),
        _row(f"{_C}dur:2{_E}",                       "durability"),
        _row(f"{_C}lvl:2{_E}  {_C}lvl<=3{_E}",     "level"),
    ]) + "\n"
    f"\n"
    f"[bold]── Legality ─────────────────────────────[/bold]\n"
    + "\n".join([
        _row(f"{_C}legal:standard{_E}  {_C}legal:s{_E}",    "legal in format"),
        _row(f"{_C}banned:standard{_E}  {_C}banned:p{_E}",  "banned in format"),
    ]) + "\n"
    f"\n"
    f"[bold]── Sort ─────────────────────────────────[/bold]\n"
    + "\n".join([
        _row(f"{_C}sort:rarity{_E}",        "sort by rarity"),
        _row(f"{_C}sort:cost{_E}",           "sort by cost (memory)"),
        _row(f"{_C}sort:power{_E}",          "sort by power"),
        _row(f"{_C}sort:name{_E}",           "sort by name (default)"),
        _row(f"{_C}order:desc{_E}",          "descending  (default: asc)"),
    ]) + "\n"
    f"\n"
    f"[bold]── Flags ────────────────────────────────[/bold]\n"
    + "\n".join([
        _row(f"{_C}is:material{_E}",   "champions and regalia"),
        _row(f"{_C}is:permanent{_E}",  "cards that stay on the field"),
    ]) + "\n"
    f"\n"
    f"[bold]── Logic ────────────────────────────────[/bold]\n"
    + "\n".join([
        _row(f"{_C}e:fire OR e:water{_E}",  "OR between filters"),
        _row(f"{_C}-r:common{_E}",           "negation (exclude)"),
        _row(f'{_C}o:"on enter"{_E}',        "exact phrase (double quotes)"),
    ]) + "\n"
    f"\n"
    f"[bold]── Examples ─────────────────────────────[/bold]\n"
    f"[dim]t:ally e:fire cost:2\n"
    f"class:mage o:banish -r:common\n"
    f"is:material legal:standard\n"
    f"kw:stealth OR kw:taunt\n"
    f'o:"on enter" t:ally\n'
    f"pow>=3 life>=3 t:human[/dim]\n"
    f"\n"
    f"[bold]── Rarities ─────────────────────────────[/bold]\n"
    f"[dim]c  u  r  sr  ur  pr  csr  cur  cpr[/dim]\n"
    f"\n"
    f"[bold]── Formats ──────────────────────────────[/bold]\n"
    f"[dim]standard (s)   pantheon (p)   draft (d)[/dim]\n"
)


class HelpScreen(ModalScreen[None]):

    BINDINGS = [
        Binding("escape", "dismiss", "Close"),
        Binding("f1", "dismiss", "Close", show=False),
        Binding("?", "dismiss", "Close", show=False),
    ]

    DEFAULT_CSS = """
    HelpScreen {
        align: center middle;
    }
    #dialog {
        width: 60%;
        max-height: 80%;
        border: tall $primary;
        background: $surface;
        padding: 0 2;
    }
    """

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="dialog"):
            yield Static(_CONTENT, markup=True)
