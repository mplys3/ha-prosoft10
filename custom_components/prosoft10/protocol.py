"""Read-only ProSOFT 10 BLE protocol.

The app sends Latin-1/ASCII requests to ABF1 and receives notifications there.
Replies observed on the device have no required CR/LF terminator.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable

from bleak import BleakClient

from .const import CHARACTERISTIC_UUID


class ProtocolError(Exception):
    """The device did not return a usable reply."""


def make_request(code: str) -> bytes:
    """Encode a four-digit read request; never writes a setting."""
    if len(code) != 4 or not code.isascii() or not code.isdecimal():
        raise ValueError("Parameter code must be four ASCII decimal digits")
    return f"@{code}\r\n".encode("ascii")


def parse_reply(code: str, data: bytes) -> str:
    """Extract one value from a notification sequence for a requested code."""
    text = data.decode("latin-1").strip("\x00\r\n ")
    prefix = f"@{code}"
    position = text.find(prefix)
    if position < 0:
        raise ProtocolError(f"No reply for parameter {code}")
    value = text[position + len(prefix) :].split("@", 1)[0].strip("\x00\r\n ")
    if not value or value.lower() == "invalid data":
        raise ProtocolError(f"Empty or invalid reply for parameter {code}")
    return value


async def read_parameter(
    client: BleakClient,
    code: str,
    queue: asyncio.Queue[bytes],
    *,
    timeout: float = 5.0,
    quiet_time: float = 0.25,
) -> str:
    """Send a request and collect its notification fragments until the line goes quiet."""
    while not queue.empty():
        queue.get_nowait()

    async with asyncio.timeout(timeout):
        await client.write_gatt_char(
            CHARACTERISTIC_UUID, make_request(code), response=True
        )
    fragments: list[bytes] = []
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    matched = False

    while loop.time() < deadline:
        remaining = deadline - loop.time()
        wait = min(quiet_time, remaining) if matched else remaining
        try:
            fragment = await asyncio.wait_for(queue.get(), wait)
        except TimeoutError:
            if matched:
                break
            raise ProtocolError(f"Timed out waiting for parameter {code}") from None
        fragments.append(fragment)
        matched = f"@{code}".encode("ascii") in b"".join(fragments)

    return parse_reply(code, b"".join(fragments))


def notification_handler(
    queue: asyncio.Queue[bytes],
) -> Callable[[object, bytearray], None]:
    """Return the Bleak callback for this connection."""

    def handle(_sender: object, data: bytearray) -> None:
        queue.put_nowait(bytes(data))

    return handle
