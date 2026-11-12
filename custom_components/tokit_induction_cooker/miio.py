"""A small miIO client: Xiaomi's LAN protocol on UDP 54321.

Each packet is a 32-byte header plus an AES-128-CBC payload. The key is the MD5 of
the device token and the IV is the MD5 of key + token. Blocking; call it from an
executor.
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

PORT = 54321
HELLO = bytes.fromhex("21310020" + "ff" * 28)


class MiioError(Exception):
    """The device didn't answer, or answered with an error."""


class MiioDevice:
    def __init__(self, host: str, token_hex: str, timeout: float = 2.0, retries: int = 3) -> None:
        self.host = host
        self._token = bytes.fromhex(token_hex)
        self._key = hashlib.md5(self._token).digest()
        self._iv = hashlib.md5(self._key + self._token).digest()
        self._timeout = timeout
        self._retries = retries
        self._device_id: bytes | None = None
        self._stamp_delta = 0
        self._msg_id = int(time.time()) % 100000
        self._lock = threading.Lock()

    def _cipher(self) -> Cipher:
        return Cipher(algorithms.AES(self._key), modes.CBC(self._iv))

    def _encrypt(self, plain: bytes) -> bytes:
        padder = padding.PKCS7(128).padder()
        enc = self._cipher().encryptor()
        return enc.update(padder.update(plain) + padder.finalize()) + enc.finalize()

    def _decrypt(self, data: bytes) -> bytes:
        dec = self._cipher().decryptor()
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(dec.update(data) + dec.finalize()) + unpadder.finalize()

    def _hello(self, sock: socket.socket) -> None:
        sock.sendto(HELLO, (self.host, PORT))
        data, _ = sock.recvfrom(4096)
        if len(data) < 32 or data[:2] != b"\x21\x31":
            raise MiioError("bad handshake reply")
        self._device_id = data[8:12]
        self._stamp_delta = struct.unpack(">I", data[12:16])[0] - int(time.time())

    def send(self, method: str, params: Any) -> Any:
        with self._lock:
            last: Exception | None = None
            for _ in range(self._retries):
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(self._timeout)
                try:
                    if self._device_id is None:
                        self._hello(sock)
                    assert self._device_id is not None
                    self._msg_id += 1
                    body = json.dumps(
                        {"id": self._msg_id, "method": method, "params": params}, separators=(",", ":")
                    ).encode()
                    enc = self._encrypt(body)
                    stamp = int(time.time()) + self._stamp_delta
                    head = struct.pack(">HHI4sI", 0x2131, 32 + len(enc), 0, self._device_id, stamp)
                    checksum = hashlib.md5(head + self._token + enc).digest()
                    sock.sendto(head + checksum + enc, (self.host, PORT))
                    data, _ = sock.recvfrom(65535)
                    if len(data) <= 32:
                        raise MiioError("empty reply")
                    try:
                        text = self._decrypt(data[32:]).rstrip(b"\x00").decode(errors="replace")
                        reply = json.loads(text)
                    except ValueError as err:
                        # A wrong token fails here, and so does an action sent with plain
                        # values instead of {"piid": n, "value": v}.
                        raise MiioError("the reply could not be decoded") from err
                    if "error" in reply:
                        raise MiioError(f"device error: {reply['error']}")
                    return reply.get("result")
                except OSError as err:  # includes socket.timeout
                    last = err
                    self._device_id = None  # handshake again on the next try
                finally:
                    sock.close()
            raise MiioError(f"no reply from {self.host}: {last}")

    def info(self) -> dict[str, Any]:
        return self.send("miIO.info", [])

    def get_properties(self, pairs: list[tuple[int, int]]) -> dict[tuple[int, int], Any]:
        out: dict[tuple[int, int], Any] = {}
        for i in range(0, len(pairs), 12):
            chunk = [{"did": f"{s}-{p}", "siid": s, "piid": p} for s, p in pairs[i : i + 12]]
            for item in self.send("get_properties", chunk) or []:
                if item.get("code") == 0:
                    out[(item["siid"], item["piid"])] = item.get("value")
        return out

    def set_property(self, siid: int, piid: int, value: Any) -> None:
        """Write one property. Only the few the spec marks writable are accepted."""
        result = self.send(
            "set_properties", [{"did": f"set-{siid}-{piid}", "siid": siid, "piid": piid, "value": value}]
        )
        if not isinstance(result, list) or not result or result[0].get("code") != 0:
            raise MiioError(f"property {siid}.{piid} was refused: {result}")

    def action(self, siid: int, aiid: int, inputs: list[tuple[int, Any]]) -> dict[str, Any]:
        """Call an action. Inputs are (piid, value) pairs."""
        result = self.send(
            "action",
            {
                "did": f"call-{siid}-{aiid}",
                "siid": siid,
                "aiid": aiid,
                "in": [{"piid": piid, "value": value} for piid, value in inputs],
            },
        )
        if not isinstance(result, dict) or result.get("code") != 0:
            raise MiioError(f"action {siid}.{aiid} was refused: {result}")
        return result
