from dataclasses import dataclass


@dataclass(frozen=True)
class BestiaryEntry:
    name: str
    category: str
    weaknesses: tuple[str, ...]
    description: str


@dataclass(frozen=True)
class InventoryItem:
    name: str
    item_type: str
    quantity: int
