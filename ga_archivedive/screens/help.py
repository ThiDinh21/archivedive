from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Static

_CONTENT = """\
[bold yellow]Search Syntax Reference[/bold yellow]

[dim]Filters use the format [/dim][bold]key:value[/bold][dim]. Multiple filters are AND-combined.[/dim]

[bold]── Text ──────────────────────────────[/bold]
[cyan]silvie[/cyan]                   name search (fuzzy)
[cyan]o:banish[/cyan]                 effect text (any edition)
[cyan]oc:banish[/cyan]                effect text (canonical only)
[cyan]kw:stealth[/cyan]               keyword ability (exact)
[cyan]rule:graveyard[/cyan]           rule text
[cyan]flavor:courage[/cyan]           flavor text
[cyan]ill:akira[/cyan]                illustrator

[bold]── Card attributes ──────────────────[/bold]
[cyan]t:ally[/cyan]  [cyan]t:human[/cyan]           type or subtype
[cyan]class:mage[/cyan]               class
[cyan]e:fire[/cyan]  [cyan]e:wa[/cyan]               element (aliases: fi wa wi cr no)
[cyan]r:rare[/cyan]  [cyan]r:csr[/cyan]              rarity
[cyan]set:DOA[/cyan]                  set prefix
[cyan]speed:fast[/cyan]               speed

[bold]── Costs ────────────────────────────[/bold]
[cyan]cost:3[/cyan]                   memory or reserve cost
[cyan]m:3[/cyan]                      memory cost only
[cyan]res:2[/cyan]                    reserve cost only

[bold]── Stats (operators: = > < >= <=) ──[/bold]
[cyan]pow:3[/cyan]  [cyan]pow>=3[/cyan]            power
[cyan]life:4[/cyan]  [cyan]life<=5[/cyan]           life
[cyan]dur:2[/cyan]                    durability
[cyan]lvl:2[/cyan]  [cyan]lvl<=3[/cyan]             level

[bold]── Legality ─────────────────────────[/bold]
[cyan]legal:standard[/cyan]  [cyan]legal:s[/cyan]    legal in format
[cyan]banned:pantheon[/cyan]  [cyan]banned:p[/cyan]  banned in format

[bold]── Flags ────────────────────────────[/bold]
[cyan]is:material[/cyan]              champions and regalia
[cyan]is:permanent[/cyan]             cards that stay on the field

[bold]── Logic ────────────────────────────[/bold]
[cyan]e:fire OR e:water[/cyan]        OR between filters
[cyan]-r:common[/cyan]                negation (exclude)
[cyan]o:"on enter"[/cyan]             exact phrase (double quotes)

[bold]── Examples ─────────────────────────[/bold]
[dim]t:ally e:fire cost:2
class:mage o:banish -r:common
is:material legal:standard
kw:stealth OR kw:taunt
o:"on enter" t:ally
pow>=3 life>=3 t:human[/dim]

[bold]── Rarities ─────────────────────────[/bold]
[dim]c  u  r  sr  ur  pr  csr  cur  cpr[/dim]

[bold]── Formats ──────────────────────────[/bold]
[dim]standard (s)   pantheon (p)   draft (d)[/dim]
"""


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
