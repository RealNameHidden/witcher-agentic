import unittest
from unittest.mock import patch

from witcher_magentic.tools import (
    get_bestiary_entry,
    get_inventory,
    inspect_bestiary,
    inspect_inventory,
    read_witcher_oil_lore,
    read_witcher_potion_lore,
    read_witcher_ritual_and_curse_lore,
)


class BestiaryToolTests(unittest.TestCase):
    def test_finds_monster_without_case_sensitivity(self) -> None:
        entry = get_bestiary_entry("  KATAKAN ")

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual("Katakan", entry.name)
        self.assertIn("Black Blood", entry.weaknesses)

    def test_returns_none_for_unknown_monster(self) -> None:
        self.assertIsNone(get_bestiary_entry("Unknown Beast"))


class InventoryToolTests(unittest.TestCase):
    def test_returns_available_items(self) -> None:
        inventory = get_inventory()

        self.assertTrue(any(item.name == "Black Blood" for item in inventory))
        self.assertTrue(all(item.quantity > 0 for item in inventory))


class AgentFrameworkToolTests(unittest.TestCase):
    def test_exposes_information_functions_as_framework_tools(self) -> None:
        self.assertEqual("inspect_bestiary", inspect_bestiary.name)
        self.assertEqual("inspect_inventory", inspect_inventory.name)
        self.assertEqual("read_witcher_potion_lore", read_witcher_potion_lore.name)
        self.assertEqual("read_witcher_oil_lore", read_witcher_oil_lore.name)
        self.assertEqual(
            "read_witcher_ritual_and_curse_lore",
            read_witcher_ritual_and_curse_lore.name,
        )

    @patch("witcher_magentic.tools._read_wiki_api")
    def test_lore_tool_returns_wiki_content_and_source_urls(self, read_api) -> None:
        read_api.side_effect = [
            {
                "query": {
                    "categorymembers": [{"title": "Divination"}],
                }
            },
            {
                "query": {
                    "pages": [
                        {
                            "title": "Divination",
                            "revisions": [
                                {"slots": {"main": {"content": "Sees the future."}}}
                            ],
                        }
                    ]
                }
            },
        ]

        result = read_witcher_ritual_and_curse_lore.func()

        self.assertEqual("Witcher Wiki (Fandom)", result["source"])
        self.assertEqual("Divination", result["articles"][0]["title"])
        self.assertEqual("Sees the future.", result["articles"][0]["content"])
        self.assertEqual(
            "https://witcher.fandom.com/wiki/Divination",
            result["articles"][0]["url"],
        )

    @patch("witcher_magentic.tools._read_rendered_wiki_pages")
    def test_potion_and_oil_tools_request_their_game_indexes(self, read_pages) -> None:
        read_pages.return_value = {"articles": []}

        read_witcher_potion_lore.func()
        potion_titles = read_pages.call_args.args[0]
        read_witcher_oil_lore.func()
        oil_titles = read_pages.call_args.args[0]

        self.assertEqual(
            ("The Witcher potions", "The Witcher 2 potions", "The Witcher 3 potions"),
            potion_titles,
        )
        self.assertEqual(
            ("The Witcher oils", "The Witcher 2 oils", "The Witcher 3 oils"),
            oil_titles,
        )


if __name__ == "__main__":
    unittest.main()
