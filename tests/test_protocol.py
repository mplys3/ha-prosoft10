"""Protocol tests based on the ProSOFT 10 responses captured by nRF Connect."""

import asyncio
import sys
import types
import unittest
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
    parse_regeneration_time,
    parse_reply,
    read_parameter,
)


class ProtocolTests(unittest.TestCase):
    def test_regeneration_time_and_disabled_slot(self) -> None:
        self.assertEqual(str(parse_regeneration_time("02:30")), "02:30:00")
        self.assertIsNone(parse_regeneration_time("99:99"))
        self.assertIsNone(parse_regeneration_time("25:00"))

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
