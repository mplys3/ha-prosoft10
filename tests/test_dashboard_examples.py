"""Check example nesting and templates; these are not live frontend tests."""

import unittest
from pathlib import Path

import jinja2
import yaml

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def load(name):
    return yaml.safe_load((EXAMPLES / name).read_text())


class DashboardExampleTests(unittest.TestCase):
    def test_native_card_dashboard_and_list_item_agree(self):
        card = load("prosoft-logs-card.yaml")
        self.assertEqual(card["type"], "vertical-stack")
        self.assertEqual([part["type"] for part in card["cards"]], ["entities", "markdown", "markdown"])
        dashboard = load("prosoft-logs-dashboard.yaml")
        self.assertIsInstance(dashboard["views"], list)
        self.assertEqual(dashboard["views"][0]["cards"], [card])
        self.assertEqual(load("prosoft-logs-card-list-item.yaml"), [card])

    def test_ultra_modules_embed_the_same_native_cards(self):
        card = load("prosoft-logs-card.yaml")
        ultra = load("prosoft-logs-ultra-card.yaml")
        self.assertEqual(ultra["type"], "custom:ultra-card")
        modules = ultra["layout"]["rows"][0]["columns"][0]["modules"]
        self.assertEqual([m["card_config"] for m in modules], card["cards"])
        self.assertEqual(len({m["id"] for m in modules}), 3)
        for module in modules:
            self.assertEqual(module["type"], "native_card")
            self.assertEqual(module["card_type"], f"hui-{module['card_config']['type']}-card")
        dashboard = load("prosoft-logs-ultra-dashboard.yaml")
        self.assertEqual(dashboard["views"][0]["cards"], [ultra])

    def test_templates_handle_unknown_state_and_escape_records(self):
        env = jinja2.Environment(undefined=jinja2.StrictUndefined)
        env.filters["timestamp_custom"] = lambda value, fmt: "27/10/2026 12:00"
        cards = load("prosoft-logs-card.yaml")["cards"][1:]
        for card in cards:
            template = env.from_string(card["content"])
            for state in ("unknown", "unavailable", "2026-10-27T11:00:00+00:00"):
                for status in ("not_requested", "fetching", "failed", "received"):
                    for populated in (False, True):
                        with self.subTest(title=card["title"], state=state, status=status, populated=populated):
                            rows = [{"date": "2026-10-06", "time": "13:41", "content": "<test> | Hardhed =33 dH"}] if populated else []
                            attrs = {"entries": rows, "status": status, "completion": "idle"}
                            rendered = template.render(
                                state_attr=lambda entity, key, attrs=attrs: attrs.get(key),
                                states=lambda entity, state=state: state,
                                as_timestamp=lambda value, default=None: default if value in ("unknown", "unavailable") else 0,
                            )
                            if populated:
                                self.assertIn("| :--- | :--- | :--- |\n| 2026-10-06 | 13:41 |", rendered)
                                self.assertIn("&lt;test&gt; &#124; Hardhed =33 dH", rendered)
                            if state in ("unknown", "unavailable"):
                                self.assertNotIn("Senest hentet:", rendered)


if __name__ == "__main__":
    unittest.main()
