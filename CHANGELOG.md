# Changelog

## [0.1.1] — 2026-05-31

### Docs
- Add screenshots to README
- Add GitHub repository URLs
- Fix SEARCH_SYNTAX.md link to point to GitHub
- Prefer `uvx` as the recommended install method

## [0.1.0] — 2026-05-31

Initial release.

### Features
- Card browser with search bar, card table, and detail panel
- Search query parser with filters, operators, negation, OR logic, and parenthesis grouping
- Filter keys: name, type/subtype, class, element, rarity, set, speed, cost, power, life, durability, level, effect, keyword, rule, flavor, illustrator, legality, flags
- Shorthand aliases: `t:`, `e:`, `r:`, `c:`, `cl:`, `m:`, `res:`, `o:`, `oc:`, `kw:`, `ill:`
- Numeric comparison operators (`>`, `<`, `>=`, `<=`) for stat and cost filters
- Sort and order modifiers (`sort:`, `order:`)
- Syntax warnings for unknown filter keys and invalid operators
- Art edition selector via `ctrl+o` for cards with multiple printings
- Related cards panel and modal navigation via `r`
- Format legality display (Standard, Pantheon, Draft)
- Clipboard copy: card text via `c`, search bar text via `ctrl+c`
- Clipboard support for Wayland (`wl-clipboard`), X11 (`xclip`, `xsel`)
- Open card image in browser via `o` or number keys `1`–`9`
- Keyboard navigation: `s` focus search, arrow keys, `escape`, `ctrl+<`/`>` pagination
- F1 syntax help overlay
- Loading spinner during API requests
- Result count and pagination status bar
