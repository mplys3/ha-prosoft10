"""Protocol tests based on the ProSOFT 10 responses captured by nRF Connect."""

import asyncio
import sys
import types
import unittest
from datetime import date
from pathlib import Path

# Load the protocol without importing Home Assistant from the integration setup.
package = types.ModuleType("custom_components.prosoft10")
package.__path__ = [
    str(Path(__file__).resolve().parents[1] / "custom_components" / "prosoft10")
]
sys.modules.setdefault("custom_components.prosoft10", package)

from custom_components.prosoft10.beacon import continuous_flow_alarm
from custom_components.prosoft10.protocol import (
    ProtocolError,
    make_request,
    parse_regeneration_date,
    parse_regeneration_time,
    parse_reply,
    read_log,
    read_parameter,
)


class ProtocolTests(unittest.TestCase):
    def test_log_codes_and_validation(self) -> None:
        for code in ("706", "707"):
            self.assertEqual(make_request(code), f"@{code}\r\n".encode())
        for code in ("700", "70", "0706x", "706\r\n", "１２３４"):
            with self.assertRaises(ValueError):
                make_request(code)

    def test_log_fragments_preserve_all_records(self) -> None:
        async def run():
            for code in ("706", "707"):
                queue = asyncio.Queue()
                class Client:
                    async def write_gatt_char(self, _uuid, data, response, code=code, queue=queue):
                        self.sent = data
                        for part in (b"@" + code.encode(), b"first\r", b"\nsecond @1014=11", b"\r\n", b"\r", b"\n"):
                            queue.put_nowait(part)
                client = Client()
                value = await read_log(client, code, queue, timeout=0.05)
                self.assertEqual(value, f"@{code}first\nsecond @1014=11")
                self.assertEqual(client.sent, f"@{code}\r\n".encode())
        asyncio.run(run())

    def test_incomplete_or_oversize_log_never_returns_partial_success(self) -> None:
        async def run():
            queue = asyncio.Queue()
            class Client:
                async def write_gatt_char(self, *_args, **_kwargs):
                    queue.put_nowait(b"record without terminator")
            with self.assertRaises(TimeoutError):
                await read_log(Client(), "706", queue, timeout=0.01)
            with self.assertRaises(ProtocolError):
                await read_log(Client(), "706", queue, max_bytes=5)
            class EmptyClient:
                async def write_gatt_char(self, *_args, **_kwargs):
                    queue.put_nowait(b"\r\n")
            self.assertEqual(await read_log(EmptyClient(), "707", queue), "")
        asyncio.run(run())

    def test_regeneration_time_and_disabled_slot(self) -> None:
        self.assertEqual(str(parse_regeneration_time("02:30")), "02:30:00")
        self.assertIsNone(parse_regeneration_time("99:99"))
        self.assertIsNone(parse_regeneration_time("25:00"))

    def test_regeneration_date(self) -> None:
        self.assertEqual(parse_regeneration_date("16/10/2026"), date(2026, 10, 16))
        self.assertEqual(parse_regeneration_date(" 29/02/2024 "), date(2024, 2, 29))
        for value in (None, "", "00/00/0000", "31/02/2026", "29/02/2025", "invalid data"):
            with self.subTest(value=value):
                self.assertIsNone(parse_regeneration_date(value))

    def test_continuous_flow_flag(self) -> None:
        self.assertIsNone(continuous_flow_alarm({}))
        self.assertIsNone(continuous_flow_alarm({65535: b"\x02\x00"}))
        self.assertFalse(continuous_flow_alarm({65535: b"\x00\x00\x00"}))
        self.assertTrue(continuous_flow_alarm({65535: b"\x02\x00\x00"}))
        self.assertTrue(continuous_flow_alarm({65535: b"\x03\x00\x00"}))

    def test_captured_frames(self) -> None:
        self.assertEqual(make_request("1005"), bytes.fromhex("40313030350d0a"))
        self.assertEqual(make_request("1146"), bytes.fromhex("40313134360d0a"))
        self.assertEqual(make_request("1169"), bytes.fromhex("40313136390d0a"))
        self.assertEqual(
            parse_reply("1169", bytes.fromhex("40313136393030303533")), "00053"
        )
        self.assertEqual(
            parse_reply("1006", bytes.fromhex("403130303632312e32")), "21.2"
        )
        self.assertEqual(parse_reply("1174", bytes.fromhex("403131373430")), "0")

    def test_rejects_wrong_or_empty_reply(self) -> None:
        with self.assertRaises(ProtocolError):
            parse_reply("1169", b"@11740")
        with self.assertRaises(ProtocolError):
            parse_reply("1169", b"@1169")

    def test_collects_split_notifications(self) -> None:
        async def run() -> None:
            queue: asyncio.Queue[bytes] = asyncio.Queue()

            class Client:
                async def write_gatt_char(
                    self, _uuid: str, data: bytes, response: bool
                ) -> None:
                    self.sent = data
                    self.response = response
                    queue.put_nowait(b"@11")
                    queue.put_nowait(b"6900053")

            client = Client()
            result = await read_parameter(client, "1169", queue, quiet_time=0.01)
            self.assertEqual(result, "00053")
            self.assertEqual(client.sent, b"@1169\r\n")
            self.assertTrue(client.response)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
