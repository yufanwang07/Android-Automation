from pathlib import Path
import unittest

from android_automation.ui import Bounds, UiHierarchy


FIXTURE = Path(__file__).parent / "fixtures" / "window_dump.xml"


def hierarchy() -> UiHierarchy:
    return UiHierarchy.parse(FIXTURE.read_text())


class UiHierarchyTests(unittest.TestCase):
    def test_bounds_parse_and_center(self) -> None:
        bounds = Bounds.parse("[100,1800][980,1950]")
        self.assertIsNotNone(bounds)
        self.assertEqual(bounds.center, (540, 1875))

    def test_find_matches_text_resource_id_and_description(self) -> None:
        ui = hierarchy()
        self.assertEqual([node.label for node in ui.find("continue")], ["Continue"])
        self.assertEqual([node.label for node in ui.find("title")], ["Welcome"])
        self.assertEqual([node.label for node in ui.find("settings")], ["Settings"])

    def test_clickables_exclude_disabled_nodes(self) -> None:
        self.assertEqual(
            [node.label for node in hierarchy().clickables()], ["Continue"]
        )

    def test_visible_nodes_have_useful_labels(self) -> None:
        self.assertEqual(
            [node.label for node in hierarchy().visible()],
            ["Welcome", "Continue", "Settings"],
        )


if __name__ == "__main__":
    unittest.main()
