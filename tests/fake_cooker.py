"""A pretend cooker for the tests. It speaks miIO on a local UDP port, so no test touches a real hob.

It copies what a real cooker was seen to do:

- a start command only selects the mode, and heating needs a press on the cooker itself;
- power and temperature changes answer code 1 and change nothing while it's idle;
- an action sent with plain values instead of {"piid": n, "value": v} gets a reply that isn't JSON;
- a packet it can't decrypt gets no reply at all;
- a hello gets back ff bytes where the token would be, as it does from a cooker on Wi-Fi.

Where a real cooker hasn't been seen (pausing while idle, say), this answers code 1.
"""
from __future__ import annotations

import hashlib
import json
import socket
import struct
import threading
import time
from typing import Any

from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

HELLO = bytes.fromhex("21310020" + "ff" * 28)
TOKEN = "00112233445566778899aabbccddeeff"  # made up for the tests. gitleaks:allow
MAC = "AA:BB:CC:DD:EE:FF"
MODEL = "chunmi.ihcooker.cbhw"

# Target temperature each built-in mode loads, as read back from a real cooker.
MODE_TARGETS = {1: 185, 2: 180, 3: 199, 4: 199, 5: 155}

OFF, IDLE, COOKING, PAUSED = 5, 0, 1, 4


class FakeCooker:
    def __init__(self, token_hex: str = TOKEN, model: str = MODEL) -> None:
        self.model = model
        self._token = bytes.fromhex(token_hex)
        self._key = hashlib.md5(self._token).digest()
        self._iv = hashlib.md5(self._key + self._token).digest()
        self._device_id = bytes.fromhex("0badcafe")
        # (siid, piid): value. It starts switched off.
        self.props: dict[tuple[int, int], Any] = {
            (2, 1): OFF,  # status
            (2, 2): 0,  # fault
            (2, 5): 0,  # left-time
            (2, 6): 0,  # working-time
            (3, 1): "",  # menu
            (3, 2): 19,  # phase
            (3, 3): 11,  # work-status
            (3, 7): 22,  # temperature
            (3, 8): 0,  # target-temperature
            (3, 9): 0,  # fire-gears
            (3, 15): 0,  # recipe-type
        }
        self.actions: list[tuple[int, int, list[Any]]] = []
        self.requests: list[dict[str, Any]] = []
        self.silent = False
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind(("127.0.0.1", 0))
        self._sock.settimeout(0.1)
        self.port: int = self._sock.getsockname()[1]
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._serve, name="fake-cooker", daemon=True)

    def __enter__(self) -> FakeCooker:
        self._thread.start()
        return self

    def __exit__(self, *_: object) -> None:
        self._stop.set()
        self._thread.join(2)
        self._sock.close()

    @property
    def status(self) -> int:
        return self.props[(2, 1)]

    def press_start(self) -> None:
        """What a finger on the cooker's own button does. Nothing on the network can do this."""
        self.props[(2, 1)] = COOKING
        self.props[(3, 3)] = 2
        self.props[(3, 9)] = 70
        if not self.props[(3, 8)]:
            self.props[(3, 8)] = MODE_TARGETS[1]

    # --- the protocol ---

    def _cipher(self) -> Cipher:
        return Cipher(algorithms.AES(self._key), modes.CBC(self._iv))

    def _decrypt(self, data: bytes) -> bytes:
        decryptor = self._cipher().decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(decryptor.update(data) + decryptor.finalize()) + unpadder.finalize()

    def _encrypt(self, plain: bytes) -> bytes:
        padder = padding.PKCS7(128).padder()
        encryptor = self._cipher().encryptor()
        return encryptor.update(padder.update(plain) + padder.finalize()) + encryptor.finalize()

    def _send(self, addr: tuple[str, int], body: bytes) -> None:
        encrypted = self._encrypt(body)
        head = struct.pack(">HHI4sI", 0x2131, 32 + len(encrypted), 0, self._device_id, int(time.time()))
        checksum = hashlib.md5(head + self._token + encrypted).digest()
        self._sock.sendto(head + checksum + encrypted, addr)

    def _serve(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(65535)
            except socket.timeout:  # the same thing as TimeoutError from Python 3.10
                continue
            except OSError:
                return
            if self.silent:
                continue
            if data == HELLO:
                head = struct.pack(">HHI4sI", 0x2131, 32, 0, self._device_id, int(time.time()))
                self._sock.sendto(head + b"\xff" * 16, addr)
                continue
            try:
                request = json.loads(self._decrypt(data[32:]))
            except ValueError:
                continue  # the wrong token: a real cooker stays silent too
            self.requests.append(request)
            self._answer(addr, request)

    def _answer(self, addr: tuple[str, int], request: dict[str, Any]) -> None:
        method, params = request.get("method"), request.get("params")
        result: Any
        if method == "miIO.info":
            result = {"model": self.model, "mac": MAC, "fw_ver": "2.2.0_0002"}
        elif method == "get_properties":
            result = []
            for item in params:
                pair = (item["siid"], item["piid"])
                known = pair in self.props
                answer = {"did": item["did"], "siid": pair[0], "piid": pair[1], "code": 0 if known else -4001}
                if known:
                    answer["value"] = self.props[pair]
                result.append(answer)
        elif method == "action":
            inputs = params.get("in", [])
            if any(not isinstance(item, dict) for item in inputs):
                self._send(addr, b'{"id":%d,"result":{"code":0,"out":[}' % request["id"])
                return
            self.actions.append((params["siid"], params["aiid"], inputs))
            code = self._act(params["siid"], params["aiid"], {item["piid"]: item["value"] for item in inputs})
            result = {"did": params["did"], "siid": params["siid"], "aiid": params["aiid"], "code": code, "out": []}
        else:
            body = {"id": request["id"], "error": {"code": -32601, "message": "Method not found."}}
            self._send(addr, json.dumps(body).encode())
            return
        self._send(addr, json.dumps({"id": request["id"], "result": result}).encode())

    def _act(self, siid: int, aiid: int, values: dict[int, Any]) -> int:
        adjustable = self.status in (COOKING, PAUSED)
        if (siid, aiid) == (2, 1):  # start-cook: wakes it and loads the mode. It never heats.
            if values.get(8) not in MODE_TARGETS:
                return 1
            if self.status in (OFF, IDLE):
                self.props[(2, 1)] = IDLE
                self.props[(3, 3)] = 1
                self.props[(3, 8)] = MODE_TARGETS[values[8]]
            return 0
        if (siid, aiid) == (3, 13):  # set-fire
            if not adjustable:
                return 1
            self.props[(3, 9)] = values[9]
            return 0
        if (siid, aiid) == (3, 14):  # set-temperature
            if not adjustable:
                return 1
            self.props[(3, 8)] = values[8]
            return 0
        if (siid, aiid) == (2, 3):  # pause
            if self.status != COOKING:
                return 1
            self.props[(2, 1)] = PAUSED
            self.props[(3, 3)] = 12
            return 0
        if (siid, aiid) == (3, 3):  # pause-recover
            if self.status != PAUSED:
                return 1
            self.props[(2, 1)] = COOKING
            self.props[(3, 3)] = 2
            return 0
        if (siid, aiid) == (2, 2):  # cancel-cooking: back to idle. It doesn't switch off.
            self.props[(2, 1)] = IDLE
            self.props[(3, 3)] = 1
            self.props[(3, 8)] = 0
            self.props[(3, 9)] = 0
            return 0
        return 1
