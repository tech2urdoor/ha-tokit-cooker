"""tools/setup_wifi.py against a pretend cooker whose Wi-Fi has been reset.

    python tests/test_setup_wifi.py
"""
from __future__ import annotations

import argparse
import importlib.util
import stat
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from fake_cooker import MAC, TOKEN, FakeCooker  # noqa: E402


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


tool = _load("setup_wifi", HERE.parent / "tools" / "setup_wifi.py")
const = _load("tokit_const", HERE.parent / "custom_components" / "tokit_cooker" / "const.py")

PASSWORD = "correct horse battery"


class SetupWifiTest(unittest.TestCase):
    def start(self, **kwargs) -> FakeCooker:
        cooker = FakeCooker(**kwargs)
        cooker.__enter__()
        self.addCleanup(cooker.__exit__)
        miio = tool._load_miio()
        miio.PORT = cooker.port
        # run() loads the protocol code itself, so hand it the copy pointed at the pretend cooker.
        self.addCleanup(setattr, tool, "_load_miio", tool._load_miio)
        tool._load_miio = lambda: miio
        self.addCleanup(setattr, tool, "SEARCH", tool.SEARCH)
        tool.SEARCH = ("127.0.0.1",)
        return cooker

    def run_tool(self, *, password: str = PASSWORD, **options) -> tuple[int, str]:
        args = argparse.Namespace(**{"host": None, "ssid": "home", "token_file": None, "check": False, **options})
        said: list[str] = []
        code = tool.run(args, ask=lambda _: "typed-name", ask_secret=lambda _: password, say=said.append)
        return code, "\n".join(said)

    def test_it_supports_the_models_the_integration_does(self) -> None:
        self.assertEqual(tool.MODELS, const.SUPPORTED_MODELS)

    def test_it_reads_the_token_and_sends_the_network(self) -> None:
        cooker = self.start(provisioned=False)
        code, said = self.run_tool()
        self.assertEqual(code, 0)
        self.assertEqual(cooker.router, {"ssid": "home", "passwd": PASSWORD, "uid": 0})
        self.assertIn(TOKEN, said)
        self.assertIn(MAC, said)
        self.assertNotIn(PASSWORD, said)

    def test_the_token_is_shown_before_the_network_is_sent(self) -> None:
        cooker = self.start(provisioned=False)
        seen_at_prompt: list[bool] = []
        args = argparse.Namespace(host=None, ssid=None, token_file=None, check=False)
        said: list[str] = []

        def secret(_: str) -> str:
            seen_at_prompt.append(any(TOKEN in line for line in said) and cooker.router is None)
            return PASSWORD

        tool.run(args, ask=lambda _: " typed-name ", ask_secret=secret, say=said.append)
        self.assertEqual(seen_at_prompt, [True])
        self.assertEqual(cooker.router["ssid"], "typed-name")

    def test_check_reads_the_token_and_changes_nothing(self) -> None:
        cooker = self.start(provisioned=False)
        code, said = self.run_tool(check=True)
        self.assertEqual(code, 0)
        self.assertIn(TOKEN, said)
        self.assertIsNone(cooker.router)
        self.assertFalse(cooker.provisioned)

    def test_the_token_can_go_to_a_file_only_its_owner_can_read(self) -> None:
        self.start(provisioned=False)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "token"
            code, said = self.run_tool(token_file=path)
            self.assertEqual(code, 0)
            self.assertNotIn(TOKEN, said)
            self.assertEqual(path.read_text().strip(), TOKEN)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_a_cooker_already_on_wifi_is_left_alone(self) -> None:
        cooker = self.start(provisioned=True)
        with self.assertRaises(tool.SetupError) as caught:
            self.run_tool()
        self.assertIn("Reset the cooker's Wi-Fi first", str(caught.exception))
        self.assertEqual(cooker.requests, [])

    def test_another_model_is_left_alone(self) -> None:
        cooker = self.start(provisioned=False, model="chunmi.ihcooker.v2")
        with self.assertRaises(tool.SetupError) as caught:
            self.run_tool()
        self.assertIn("chunmi.ihcooker.v2", str(caught.exception))
        self.assertIsNone(cooker.router)

    def test_a_password_too_short_to_be_one_is_not_sent(self) -> None:
        cooker = self.start(provisioned=False)
        with self.assertRaises(tool.SetupError):
            self.run_tool(password="short")
        self.assertIsNone(cooker.router)

    def test_an_open_network_has_no_password(self) -> None:
        cooker = self.start(provisioned=False)
        self.run_tool(password="")
        self.assertEqual(cooker.router, {"ssid": "home", "passwd": "", "uid": 0})

    def test_nothing_answering_says_what_to_check(self) -> None:
        cooker = self.start(provisioned=False)
        cooker.silent = True
        original = tool.find
        self.addCleanup(setattr, tool, "find", original)
        tool.find = lambda miio, addresses: original(miio, addresses, wait=0.2, tries=1)
        with self.assertRaises(tool.SetupError) as caught:
            self.run_tool()
        self.assertIn("Nothing answered", str(caught.exception))

    def test_host_narrows_the_search_to_one_address(self) -> None:
        cooker = self.start(provisioned=False)
        tool.SEARCH = ("192.0.2.1",)  # a documentation address: nothing is there
        code, _ = self.run_tool(host="127.0.0.1")
        self.assertEqual(code, 0)
        self.assertIsNotNone(cooker.router)


if __name__ == "__main__":
    unittest.main()
