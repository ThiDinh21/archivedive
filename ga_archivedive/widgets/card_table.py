from __future__ import annotations

from textual.message import Message
from textual.widgets import DataTable

from ..models import Card


class CardTable(DataTable[str]):

    class CardHighlighted(Message):
        def __init__(self, card: Card) -> None:
            self.card = card
            super().__init__()

    class CardSelected(Message):
        def __init__(self, card: Card) -> None:
            self.card = card
            super().__init__()

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._cards: list[Card] = []

    def on_mount(self) -> None:
        self.cursor_type = "row"
        self.add_column("Name", width=32)
        self.add_column("Type", width=22)
        self.add_column("Element", width=12)
        self.add_column("Cost", width=6)
        self.add_column("Rarity", width=10)

    def populate(self, cards: list[Card]) -> None:
        self._cards = cards
        self.clear()
        for card in cards:
            editions = card.result_editions or card.editions
            rarity = editions[0].rarity.capitalize() if editions and editions[0].rarity else "-"
            self.add_row(
                card.name,
                card.display_types,
                card.display_elements,
                card.display_cost,
                rarity,
                key=card.slug,
            )
        if cards:
            self.move_cursor(row=0)

    def on_data_table_row_highlighted(self, event: DataTable.RowHighlighted) -> None:
        card = self._card_for_key(event.row_key.value if event.row_key else None)
        if card:
            self.post_message(self.CardHighlighted(card))

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        card = self._card_for_key(event.row_key.value if event.row_key else None)
        if card:
            self.post_message(self.CardSelected(card))

    def _card_for_key(self, key: str | None) -> Card | None:
        if key is None:
            return None
        return next((c for c in self._cards if c.slug == key), None)
