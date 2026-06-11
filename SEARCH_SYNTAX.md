# ArchiveDive Search Syntax

## Basic search

Plain text searches by card name (fuzzy match).

    silvie
    dungeon guide

---

## Keyword filters

Filters use the format `key:value`. Multiple filters are combined with `and`.

| Key       | Aliases                   | Description                     | Example            |
| --------- | ------------------------- | ------------------------------- | ------------------ |
| `name:`   | (plain text)              | Card name                       | `silvie`           |
| `o:`      | `effect:`                 | Effect text (any edition)       | `o:banish`         |
| `oc:`     | `oracle:`                 | Effect text (canonical only)    | `oc:banish`        |
| `kw:`     | `keyword:`                | Keyword ability (exact match)   | `kw:stealth`       |
| `rule:`   |                           | Rule text (title or body)       | `rule:graveyard`   |
| `flavor:` |                           | Flavor text                     | `flavor:silvie`    |
| `ill:`    | `illustrator:`            | Illustrator name (fuzzy)        | `ill:dragonart`    |
| `t:`      | `type:` `sub:` `subtype:` | Type or subtype (searches both) | `t:ally` `t:human` |
| `class:`  | `cl:`                     | Class                           | `class:mage`       |
| `e:`      | `element:`                | Element (see below)             | `e:fire`           |
| `r:`      | `rarity:`                 | Rarity (see below)              | `r:rare`           |
| `set:`    | `s:`                      | Set prefix code                 | `set:DOA`          |
| `cost:`   | `c:`                      | Memory or reserve cost (either) | `cost:3`           |
| `m:`      | `memory:`                 | Memory cost only                | `m:3`              |
| `res:`    | `reserve:`                | Reserve cost only               | `res:2`            |
| `legal:`  |                           | Legal in format                 | `legal:standard`   |
| `banned:` |                           | Banned in format                | `banned:standard`  |
| `speed:`  |                           | Speed: fast or slow             | `speed:fast`       |
| `is:`     |                           | Flags (see below)               | `is:material`      |
| `pow:`    | `power:`                  | Power                           | `pow:3`            |
| `life:`   |                           | Life                            | `life:4`           |
| `dur:`    | `durability:`             | Durability                      | `dur:2`            |
| `lvl:`    | `level:`                  | Level                           | `lvl:2`            |

---

## Flags (is:)

| Flag           | Description                  | Expands to                                                                                                   |
| -------------- | ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| `is:material`  | Material deck cards          | `t:champion or t:regalia`                                                                                    |
| `is:permanent` | Cards that stay on the field | `t:ally or t:champion or t:item or t:weapon or t:token or t:status or t:regalia or t:phantasia or t:mastery` |

---

## Sorting

Use `sort:` and `order:` to control result ordering.

| Key      | Default | Values                                                       |
| -------- | ------- | ------------------------------------------------------------ |
| `sort:`  | `name`  | `name` `cost` `rarity` `power` `life` `level` `dur` `number` |
| `order:` | `asc`   | `asc` `a` `desc` `d`                                         |

Examples:

    sort:rarity order:desc          highest rarity first
    sort:cost                       cheapest cards first
    e:fire sort:power order:desc    fire cards by power descending
    t:champion sort:level           champions sorted by level

---

## Quoting phrases

Wrap multi-word values in double quotes to search for an exact phrase.
Without quotes, spaces end the value and the rest is parsed as new tokens.

    o:"on enter"              effect contains the phrase "on enter"
    o:"banish from memory"    exact phrase in effect text
    name:"silvie"             works but unnecessary for single words
    ill:dragonart             illustrator name

---

## Operators (numeric and rarity fields)

Supported: `=` (default), `>`, `<`, `>=`, `<=`

    m>=3        memory cost 3 or more
    pow<4       power less than 4
    life=5      exactly 5 life
    lvl<=2      level 2 or lower
    r>c         rarity higher than common
    r>=sr       super rare or higher

---

## Negation

Prefix a filter with `-` to exclude it. Handled client-side — pagination
counts may differ slightly as results are filtered after fetching.

    -e:fire       not fire element
    -t:champion   not a champion
    -r:common     not common rarity

---

## OR logic

Use `or` or `OR` between filters. Handled client-side via two API calls
merged and deduplicated.

    e:fire or e:water           fire or water
    e:fire or e:water           same thing
    t:ally or t:champion        ally or champion
    o:banish or o:memory        effect mentions banish or memory

`or` binds more loosely than adjacent filters:

    t:ally e:fire or t:champion     (ally AND fire) or (champion)

Use parentheses to make explicit grouping:

    (t:ally e:fire) or (t:champion e:water)   explicit grouping
    (t:ally or t:champion) e:fire             fire ally or fire champion

---

## Combining filters

    t:ally e:fire cost:2            fire ally costing 2 (memory or reserve)
    t:human class:mage o:banish     human mage with banish in effect
    t:champion -e:norm              champion with any element
    e:fire or e:water -r:common     fire or water, excluding commons
    set:DOA legal:standard          Dawn of Ashes cards legal in standard

---

## Elements

    fire    water   wind    crux    norm
    arcane  astra   tera    umbra   luxem
    neos    exia    exalted

Aliases: fi=fire wa=water wi=wind cr=crux no=norm

---

## Rarities

    common (c)       uncommon (u)      rare (r)
    superrare (sr)   ultrarare (ur)    promo (pr)
    collectorsuper (csr)   collectorultra (cur)   collectorpromo (cpr)

---

## Legality formats

Used with `legal:` and `banned:`:

    standard (s)    pantheon (p)    draft (d)

    legal:standard      legal:s
    banned:pantheon     banned:p

---

## Keywords (kw:)

Common keywords (59 total — see rules.gatcg.com/glossary/keywords-and-abilities):

    stealth       taunt         steadfast     unblockable   true sight
    intercept     cleave        agility       ambush        on enter
    on death      on hit        on attack     on kill       floating memory
    vigor         ranged        empower       bulwark       immortality

`kw:` matches only cards that have the keyword — not cards that merely mention
it in their text. Handled client-side: fetches by effect text, then filters
to cards where the keyword appears as a standalone ability.

---

## Examples

    silvie
    t:ally e:fire cost:2
    class:mage o:banish -r:common
    t:champion legal:p lvl<=3
    pow>=3 life>=3 t:human
    o:memory speed:fast
    set:DOA t:champion
    banned:standard
    legal:pantheon t:champion
    is:material e:fire
    is:permanent -t:champion
    e:fire or e:water -r:common -r:uncommon
    o:"on enter" t:ally class:mage
    oc:"banish from memory"
    kw:stealth t:ally
    kw:taunt or kw:intercept
    rule:graveyard
    flavor:"courage"
    ill:dragonart r:csr
    is:material legal:s -r:common
