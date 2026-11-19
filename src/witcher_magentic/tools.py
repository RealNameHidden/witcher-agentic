import json
from dataclasses import asdict
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from agent_framework import tool

from witcher_magentic.domain import BestiaryEntry, InventoryItem


_WITCHER_WIKI_API = "https://witcher.fandom.com/api.php"
_CURSE_PAGES = (
    "Curse",
    "Curses and the Cursed",
    "Words of Wisdom on Beastly Curses",
    "The Natural Obscurity of Curses",
    "Cursed One",
)
_POTION_PAGES = (
    "The Witcher potions",
    "The Witcher 2 potions",
    "The Witcher 3 potions",
)
_OIL_PAGES = (
    "The Witcher oils",
    "The Witcher 2 oils",
    "The Witcher 3 oils",
)


class _WikiHtmlTextExtractor(HTMLParser):
    _BLOCK_TAGS = {"br", "dd", "div", "dt", "h1", "h2", "h3", "li", "p", "tr"}

    def __init__(self) -> None:
        super().__init__()
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in self._BLOCK_TAGS:
            self._parts.append("\n")
        elif tag in {"td", "th"}:
            self._parts.append("\t")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def text(self) -> str:
        lines = (" ".join(line.split()) for line in "".join(self._parts).splitlines())
        return "\n".join(line for line in lines if line)


_BESTIARY = {
    "katakan": BestiaryEntry(
        name="Katakan",
        category="Higher Vampire",
        weaknesses=("Black Blood", "Vampire Oil", "Devil's Puffball"),
        description="A dangerous vampire that regenerates rapidly and hunts after dark.",
    ),
}

_INVENTORY = (
    InventoryItem(name="Black Blood", item_type="potion", quantity=5),
    InventoryItem(name="Swallow", item_type="potion", quantity=5),
    InventoryItem(name="Cat", item_type="potion", quantity=5),
    InventoryItem(name="Thunderbolt", item_type="potion", quantity=5),
    InventoryItem(name="Tawny Owl", item_type="potion", quantity=5),
    InventoryItem(name="White Raffard's Decoction", item_type="potion", quantity=5),
    InventoryItem(name="Golden Oriole", item_type="potion", quantity=5),
    InventoryItem(name="White Honey", item_type="potion", quantity=5),
    InventoryItem(name="Blizzard", item_type="potion", quantity=5),
    InventoryItem(name="Full Moon", item_type="potion", quantity=5),
    InventoryItem(name="Maribor Forest", item_type="potion", quantity=5),
    InventoryItem(name="Petri's Philter", item_type="potion", quantity=5),
    InventoryItem(name="Killer Whale", item_type="potion", quantity=5),
    InventoryItem(name="Vampire Oil", item_type="oil", quantity=5),
    InventoryItem(name="Beast Oil", item_type="oil", quantity=5),
    InventoryItem(name="Cursed Oil", item_type="oil", quantity=5),
    InventoryItem(name="Draconid Oil", item_type="oil", quantity=5),
    InventoryItem(name="Elementa Oil", item_type="oil", quantity=5),
    InventoryItem(name="Hanged Man's Venom", item_type="oil", quantity=5),
    InventoryItem(name="Hybrid Oil", item_type="oil", quantity=5),
    InventoryItem(name="Insectoid Oil", item_type="oil", quantity=5),
    InventoryItem(name="Necrophage Oil", item_type="oil", quantity=5),
    InventoryItem(name="Ogroid Oil", item_type="oil", quantity=5),
    InventoryItem(name="Relict Oil", item_type="oil", quantity=5),
    InventoryItem(name="Specter Oil", item_type="oil", quantity=5),
)


def get_bestiary_entry(monster_name: str) -> BestiaryEntry | None:
    return _BESTIARY.get(monster_name.strip().casefold())


def get_inventory() -> tuple[InventoryItem, ...]:
    return _INVENTORY


@tool(approval_mode="never_require")
def inspect_bestiary(monster_name: str) -> dict[str, object] | None:
    """Look up a monster and return its category, weaknesses, and description."""
    entry = get_bestiary_entry(monster_name)
    return asdict(entry) if entry is not None else None


@tool(approval_mode="never_require")
def inspect_inventory() -> list[dict[str, object]]:
    """Return every currently available potion and blade oil."""
    return [asdict(item) for item in get_inventory()]


def _read_wiki_api(params: dict[str, str]) -> dict[str, object]:
    url = f"{_WITCHER_WIKI_API}?{urlencode(params)}"
    request = Request(url, headers={"User-Agent": "witcher-magentic/0.1"})
    try:
        with urlopen(request, timeout=15) as response:
            return json.load(response)
    except (OSError, URLError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Could not read Witcher Wiki: {error}") from error


def _read_wiki_pages(
    titles: list[str] | tuple[str, ...], coverage_note: str
) -> dict[str, object]:
    article_result = _read_wiki_api(
        {
            "action": "query",
            "prop": "revisions",
            "rvprop": "content",
            "rvslots": "main",
            "titles": "|".join(titles),
            "format": "json",
            "formatversion": "2",
        }
    )

    articles = []
    for page in article_result["query"]["pages"]:
        if "revisions" not in page:
            continue
        title = page["title"]
        articles.append(
            {
                "title": title,
                "url": f"https://witcher.fandom.com/wiki/{quote(title.replace(' ', '_'))}",
                "content": page["revisions"][0]["slots"]["main"]["content"],
            }
        )

    return {
        "source": "Witcher Wiki (Fandom)",
        "coverage_note": coverage_note,
        "articles": articles,
    }


def _read_rendered_wiki_pages(
    titles: tuple[str, ...], coverage_note: str
) -> dict[str, object]:
    articles = []
    for title in titles:
        result = _read_wiki_api(
            {
                "action": "parse",
                "page": title,
                "prop": "text",
                "format": "json",
                "formatversion": "2",
            }
        )
        parser = _WikiHtmlTextExtractor()
        parser.feed(result["parse"]["text"])
        articles.append(
            {
                "title": result["parse"]["title"],
                "url": f"https://witcher.fandom.com/wiki/{quote(title.replace(' ', '_'))}",
                "content": parser.text(),
            }
        )

    return {
        "source": "Witcher Wiki (Fandom)",
        "coverage_note": coverage_note,
        "articles": articles,
    }


@tool(approval_mode="never_require")
def read_witcher_potion_lore() -> dict[str, object]:
    """Read Witcher Wiki potion lists, effects, ingredients, and toxicity data."""
    return _read_rendered_wiki_pages(
        _POTION_PAGES,
        "Includes the comprehensive potion list pages for The Witcher games 1–3.",
    )


@tool(approval_mode="never_require")
def read_witcher_oil_lore() -> dict[str, object]:
    """Read Witcher Wiki blade-oil lists, effects, ingredients, and targets."""
    return _read_rendered_wiki_pages(
        _OIL_PAGES,
        "Includes the comprehensive blade-oil list pages for The Witcher games 1–3.",
    )


@tool(approval_mode="never_require")
def read_witcher_ritual_and_curse_lore() -> dict[str, object]:
    """Read Witcher Wiki articles about known rituals, curses, and cursed beings."""
    category_result = _read_wiki_api(
        {
            "action": "query",
            "list": "categorymembers",
            "cmtitle": "Category:Rituals",
            "cmnamespace": "0",
            "cmlimit": "max",
            "format": "json",
            "formatversion": "2",
        }
    )
    ritual_pages = [
        member["title"]
        for member in category_result["query"]["categorymembers"]
    ]
    titles = ["Ritual", "Ritual effects", *ritual_pages, *_CURSE_PAGES]

    return _read_wiki_pages(
        titles,
        (
            "Ritual articles come from the wiki's Rituals category. The wiki has no "
            "populated Curses category, so curse coverage uses selected reference pages."
        ),
    )
