"""Read-only ProSOFT 10 BLE protocol.

The app sends Latin-1/ASCII requests to ABF1 and receives notifications there.
Replies observed on the device have no required CR/LF terminator.
"""

from __future__ import annotations

import asyncio
import re
from collections.abc import Callable
from datetime import date, datetime, time

from bleak import BleakClient

from .const import CHARACTERISTIC_UUID


class ProtocolError(Exception):
    """The device did not return a usable reply."""


class LogReadError(ProtocolError):
    """An incomplete transfer with bounded raw data for diagnosis."""

    def __init__(self, message: str, data: bytes, stage: str) -> None:
        self.partial_log = data.decode("latin-1")
        self.received_bytes = len(data)
        self.tail_hex = data[-64:].hex(" ")
        self.stage = stage
        super().__init__(f"{message}; stage={stage}; received_bytes={len(data)}")


LOG_CODES = {"706", "707"}


def make_request(code: str) -> bytes:
    """Encode a parameter or supported log read request."""
    if (len(code) != 4 and code not in LOG_CODES) or not code.isascii() or not code.isdecimal():
        raise ValueError("Use a four-digit parameter or log code 706/707")
    return f"@{code}\r\n".encode("ascii")


def parse_regeneration_time(value: str | None) -> time | None:
    """Decode an HH:MM time; the device uses 99:99 for a disabled slot."""
    if value is None:
        return None
    try:
        hour, minute = (int(part) for part in value.strip().split(":"))
        return time(hour, minute)
    except (ValueError, TypeError):
        return None


def parse_regeneration_date(value: str | None) -> date | None:
    """Decode the device's DD/MM/YYYY date without inventing a time or timezone."""
    if value is None:
        return None
    try:
        return datetime.strptime(value.strip(), "%d/%m/%Y").date()
    except ValueError:
        return None


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


async def read_log(
    client: BleakClient,
    code: str,
    queue: asyncio.Queue[bytes],
    *,
    timeout: float = 20.0,
    total_timeout: float = 120.0,
    max_bytes: int = 262144,
) -> str:
    """Collect raw log text through its blank-line terminator, never truncate."""
    if code not in LOG_CODES:
        raise ValueError("Only log codes 706 and 707 are supported")
    while not queue.empty():
        queue.get_nowait()
    data = bytearray()
    stage = "write_request"
    try:
        async with asyncio.timeout(total_timeout):
            async with asyncio.timeout(5):
                await client.write_gatt_char(
                    CHARACTERISTIC_UUID, make_request(code), response=True
                )
            stage = "receive_log"
            while True:
                fragment = await asyncio.wait_for(queue.get(), timeout)
                data.extend(fragment)
                if len(data) > max_bytes:
                    raise LogReadError("Log exceeds size limit", bytes(data[:max_bytes]), stage)
                text = data.decode("latin-1")
                # Work on the accumulated buffer: CR/LF may span BLE notifications.
                normalized = text.replace("\r\n", "\n")
                end = re.search(r"(?:^|\n)[ \t]*\n", normalized)
                if end is not None:
                    return normalized[:end.start()].rstrip("\r\n")
    except TimeoutError as error:
        raise LogReadError(
            "Log transfer timed out before a recognized terminator",
            bytes(data), stage,
        ) from error


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
