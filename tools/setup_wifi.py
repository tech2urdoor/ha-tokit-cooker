#!/usr/bin/env python3
"""Put the cooker on your Wi-Fi without the TOKIT app, and read its token.

A cooker whose Wi-Fi has been reset opens an access point of its own. While this computer is
joined to that, the cooker hands over its token and takes the name and password of your network.
No account and no cloud are involved, and the token is the one Home Assistant asks for.

    pip install cryptography
    python tools/setup_wifi.py

docs/setup-without-the-app.md walks through it, including what has and hasn't been seen to work.
"""
from __future__ import annotations

import argparse
import getpass
import importlib.util
import os
import socket
import sys
import time
from pathlib import Path
from typing import Any, Callable, Sequence

ROOT = Path(__file__).resolve().parent.parent

# The models the integration supports. tests/test_setup_wifi.py checks this matches const.py.
MODELS = {"chunmi.ihcooker.cbhw"}

# Where to say hello. A device in this state is the router of its own network, and these are the
# addresses such devices are known to use. The last one is a broadcast, for any other address.
SEARCH = ("192.168.4.1", "192.168.13.1", "192.168.8.1", "255.255.255.255")

# A device already on a Wi-Fi network answers the hello with its token blanked out.
BLANK = (b"\xff" * 16, b"\x00" * 16)


class SetupError(Exception):
    """Something the person running this can act on. Shown without a traceback."""


def _load_miio() -> Any:
    """The integration's own protocol code, loaded by path so Home Assistant isn't needed."""
    path = ROOT / "custom_components" / "tokit_cooker" / "miio.py"
    spec = importlib.util.spec_from_file_location("tokit_miio", path)
    if spec is None or spec.loader is None:
        raise SetupError(f"Couldn't find {path}. Run this from a full copy of the repository.")
    module = importlib.util.module_from_spec(spec)
    sys.modules["tokit_miio"] = module
    try:
        spec.loader.exec_module(module)
    except ModuleNotFoundError as err:
        if err.name and err.name.startswith("cryptography"):
            raise SetupError("This needs one package first:  pip install cryptography") from err
        raise
    return module


def find(miio: Any, addresses: Sequence[str], wait: float = 1.5, tries: int = 3) -> dict[str, str | None]:
    """Say hello to each address and collect who answers.

    Returns {address: token}. The token is None for a device that kept it to itself, which is
    what one already on a Wi-Fi network does.
    """
    found: dict[str, str | None] = {}
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(0.2)
        for _ in range(tries):
            for address in addresses:
                try:
                    sock.sendto(miio.HELLO, (address, miio.PORT))
                except OSError:
                    continue  # no way to that address from this computer
            until = time.monotonic() + wait
            while time.monotonic() < until:
                try:
                    data, sender = sock.recvfrom(1024)
                except socket.timeout:
                    continue
                except OSError:
                    time.sleep(0.05)  # Windows reports an unreachable address here
                    continue
                if len(data) == 32 and data[:2] == b"\x21\x31":
                    field = data[16:32]
                    found[sender[0]] = None if field in BLANK else field.hex()
                    if found[sender[0]]:
                        # Found one. Listen a moment longer in case a second device answers too.
                        until = min(until, time.monotonic() + 0.3)
            if any(found.values()):
                break
    return found


def check_network(ssid: str, password: str) -> None:
    if not 1 <= len(ssid.encode()) <= 32:
        raise SetupError("A Wi-Fi network name is between 1 and 32 characters. Nothing was sent.")
    if password and not 8 <= len(password) <= 64:
        raise SetupError("A Wi-Fi password is between 8 and 63 characters. Nothing was sent.")


def write_token(path: Path, token: str) -> None:
    """Only the owner can read the file: the token is the key to the cooker."""
    handle = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(handle, "w") as out:
        out.write(token + "\n")
    os.chmod(path, 0o600)


def run(
    args: argparse.Namespace,
    ask: Callable[[str], str] = input,
    ask_secret: Callable[[str], str] = getpass.getpass,
    say: Callable[[str], None] = print,
) -> int:
    miio = _load_miio()
    addresses = [args.host] if args.host else list(SEARCH)

    say("Looking for the cooker...")
    found = find(miio, addresses)
    open_ones = {address: token for address, token in found.items() if token}
    if not found:
        raise SetupError(
            "Nothing answered. Check that this computer is joined to the cooker's own Wi-Fi network "
            "(its name starts with the model, like chunmi-ihcooker-cbhw_), then run this again. If it "
            "is joined, look up the router address your Wi-Fi settings show for that network and pass "
            "it with --host."
        )
    if not open_ones:
        raise SetupError(
            f"A device answered at {', '.join(found)} but kept its token to itself. That is what a "
            "cooker already on a Wi-Fi network does. Reset the cooker's Wi-Fi first, so it opens its "
            "own network, and join that."
        )
    if len(open_ones) > 1:
        raise SetupError(
            f"More than one device answered ({', '.join(open_ones)}). Say which with --host."
        )
    (host, token), = open_ones.items()

    device = miio.MiioDevice(host, token)
    try:
        info = device.info() or {}
    except miio.MiioError as err:
        raise SetupError(f"The device at {host} showed a token but then didn't answer: {err}") from err
    model = info.get("model")
    if model not in MODELS:
        raise SetupError(
            f"The device at {host} is a {model}, and this has only been made for "
            f"{', '.join(sorted(MODELS))}. Nothing was sent to it."
        )
    say(f"Found a {model} at {host} (MAC {info.get('mac')}, firmware {info.get('fw_ver')}).")

    # The token goes out before the Wi-Fi details do: once the cooker has those it drops its own
    # network, and whatever was still unsaid would be lost with it.
    if args.token_file:
        write_token(args.token_file, token)
        say(f"Its token is saved in {args.token_file}.")
    else:
        say(f"Its token is:  {token}")
        say("Keep that. Home Assistant asks for it, and it is the key to controlling the cooker.")

    if args.check:
        say("Stopped there, as asked. Nothing was changed on the cooker.")
        return 0

    ssid = args.ssid or ask("Wi-Fi network to put it on (2.4 GHz): ").strip()
    password = ask_secret("That network's password (it isn't shown as you type): ")
    check_network(ssid, password)

    try:
        answer = device.send("miIO.config_router", {"ssid": ssid, "passwd": password, "uid": 0})
    except miio.MiioError as err:
        say(
            f"The Wi-Fi details were sent, but the cooker didn't confirm them ({err}). It may have left "
            "its own network already. Give it a minute, then look for it on yours."
        )
        return 1
    say(f"The cooker took the details (it answered {answer}) and is leaving its own network for {ssid}.")
    say(
        "Next: join your own Wi-Fi again, find the cooker in your router's list of devices by the MAC "
        "above, give it a fixed address, and add the integration in Home Assistant with that address "
        "and the token."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Put a TOKIT induction cooker on your Wi-Fi without the app, and read its token.",
        epilog="Reset the cooker's Wi-Fi and join this computer to the network it opens before running this.",
    )
    parser.add_argument("--host", help="the cooker's address on its own network, if it isn't found without")
    parser.add_argument("--ssid", help="the Wi-Fi network to put it on (asked for if left out)")
    parser.add_argument(
        "--token-file", type=Path, metavar="FILE", help="save the token in FILE instead of showing it"
    )
    parser.add_argument(
        "--check", action="store_true", help="find the cooker and read its token, then stop without changing it"
    )
    args = parser.parse_args(argv)
    try:
        return run(args)
    except SetupError as err:
        print(f"\n{err}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
