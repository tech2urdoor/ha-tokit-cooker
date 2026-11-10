"""The miIO client against the pretend cooker. Needs only `cryptography`, not Home Assistant.

    python tests/test_miio.py
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from fake_cooker import MAC, MODEL, TOKEN, FakeCooker  # noqa: E402

# Loaded by path, so the package's __init__ (which needs Home Assistant) isn't imported.
_spec = importlib.util.spec_from_file_location(
    "tokit_miio", HERE.parent / "custom_components" / "tokit_cooker" / "miio.py"
)
miio = importlib.util.module_from_spec(_spec)
sys.modules["tokit_miio"] = miio
_spec.loader.exec_module(miio)


class MiioTest(unittest.TestCase):
    def setUp(self) -> None:
        self.cooker = FakeCooker()
        self.cooker.__enter__()
        self.addCleanup(self.cooker.__exit__)
        port = miio.PORT
        miio.PORT = self.cooker.port
        self.addCleanup(setattr, miio, "PORT", port)
        self.device = miio.MiioDevice("127.0.0.1", TOKEN, timeout=0.5, retries=2)

    def test_info(self) -> None:
        info = self.device.info()
        self.assertEqual(info["model"], MODEL)
        self.assertEqual(info["mac"], MAC)

    def test_reads_properties(self) -> None:
        values = self.device.get_properties([(2, 1), (3, 7), (3, 9)])
        self.assertEqual(values, {(2, 1): 5, (3, 7): 22, (3, 9): 0})

    def test_a_property_the_cooker_does_not_have_is_left_out(self) -> None:
        values = self.device.get_properties([(2, 1), (9, 9)])
        self.assertEqual(values, {(2, 1): 5})

    def test_more_than_twelve_properties_go_in_several_requests(self) -> None:
        self.device.get_properties([(2, 1)] * 13)
        sizes = [len(r["params"]) for r in self.cooker.requests if r["method"] == "get_properties"]
        self.assertEqual(sizes, [12, 1])

    def test_action_inputs_are_sent_as_piid_value_objects(self) -> None:
        self.device.action(2, 1, [(8, 3)])
        self.assertEqual(self.cooker.actions, [(2, 1, [{"piid": 8, "value": 3}])])

    def test_selecting_a_mode_does_not_heat(self) -> None:
        self.device.action(2, 1, [(8, 1)])
        self.assertEqual(self.cooker.status, 0)
        self.assertEqual(self.cooker.props[(3, 9)], 0)

    def test_an_action_the_cooker_does_not_accept_is_an_error(self) -> None:
        # Power can't be set while it's off: the cooker answers code 1.
        with self.assertRaises(miio.MiioError):
            self.device.action(3, 13, [(9, 30), (20, ""), (19, "")])
        self.assertEqual(self.cooker.props[(3, 9)], 0)

    def test_power_changes_once_it_is_cooking(self) -> None:
        self.cooker.press_start()
        self.device.action(3, 13, [(9, 30), (20, ""), (19, "")])
        self.assertEqual(self.cooker.props[(3, 9)], 30)

    def test_plain_values_get_a_reply_that_is_not_json(self) -> None:
        with self.assertRaises(miio.MiioError) as caught:
            self.device.send("action", {"did": "x", "siid": 2, "aiid": 1, "in": [1]})
        self.assertIn("could not be decoded", str(caught.exception))
        self.assertEqual(self.cooker.actions, [])

    def test_an_unknown_method_is_an_error(self) -> None:
        with self.assertRaises(miio.MiioError):
            self.device.send("no_such_method", [])

    def test_the_wrong_token_gets_silence(self) -> None:
        wrong = miio.MiioDevice("127.0.0.1", "ff" * 16, timeout=0.2, retries=2)
        with self.assertRaises(miio.MiioError) as caught:
            wrong.info()
        self.assertIn("no reply", str(caught.exception))

    def test_a_cooker_that_is_not_there(self) -> None:
        self.cooker.silent = True
        with self.assertRaises(miio.MiioError):
            miio.MiioDevice("127.0.0.1", TOKEN, timeout=0.2, retries=2).info()

    def test_it_handshakes_again_after_a_silence(self) -> None:
        self.device.info()
        self.cooker.silent = True
        with self.assertRaises(miio.MiioError):
            self.device.info()
        self.cooker.silent = False
        self.assertEqual(self.device.info()["model"], MODEL)


if __name__ == "__main__":
    unittest.main()
