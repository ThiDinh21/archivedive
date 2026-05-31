# ArchiveDive

A terminal card browser for [Grand Archive TCG](https://www.gatcg.com/), inspired by [Scryfall](https://scryfall.com).

![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue)

![ArchiveDive UI](https://raw.githubusercontent.com/ThiDinh21/archivedive/master/assets/img1.png)

![Search syntax help](https://raw.githubusercontent.com/ThiDinh21/archivedive/master/assets/img2.png)

## Install

Recommended — run instantly with [uv](https://docs.astral.sh/uv/getting-started/installation/) (no install needed):

```
uvx archivedive
```

or with pip:

```
pip install archivedive
```

## Usage

```
archivedive
```

### Key bindings

| Key      | Action                      |
| -------- | --------------------------- |
| `s`      | Focus search bar            |
| `F1`     | Search syntax help          |
| `c`      | Copy card text to clipboard |
| `o`      | Open card image in browser  |
| `ctrl+o` | Select art edition          |
| `r`      | Show related cards          |
| `ctrl+<` | Previous page               |
| `ctrl+>` | Next page                   |
| `ctrl+c` | Copy search bar text        |
| `ctrl+q` | Quit                        |

Clipboard copy requires `wl-clipboard` (Wayland), `xclip`, or `xsel` on Linux.

## Search syntax

Filters use `key:value` format and combine with `and`. Element filters use `or`.

```
silvie                          search by name
t:ally e:fire cost:2            fire ally costing 2
class:mage o:banish -r:common   mage with banish, not common
e:fire or e:water               fire or water element
t:champion legal:standard       standard-legal champions
sort:rarity order:desc          sort by rarity descending
```

See [SEARCH_SYNTAX.md](https://github.com/ThiDinh21/archivedive/blob/master/SEARCH_SYNTAX.md) for the full reference.
