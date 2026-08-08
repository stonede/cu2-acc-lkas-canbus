"""Unit tests for host-side capture and analysis helpers."""

from __future__ import annotations

import sys
from pathlib import Path
import unittest


TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import analyze_log  # noqa: E402
import capture_serial  # noqa: E402


class AnalyzeLogTests(unittest.TestCase):
    def test_enriches_four_byte_compact_frame(self) -> None:
        record = {
            "type": "frame",
            "len": 4,
            "data": "21A780B8",
            "checksum_ok": True,
        }

        self.assertTrue(analyze_log.enrich_frame(record))
        self.assertEqual(record["direction"], "LKAS_TO_EPS")
        self.assertTrue(record["lkas_on_candidate"])
        self.assertEqual(record["apply_steer_candidate"], 39)
        self.assertEqual(record["flags_raw"], 128)

    def test_enriches_five_byte_compact_frame(self) -> None:
        record = {
            "type": "frame",
            "len": 5,
            "data": "209BC08085",
            "checksum_ok": True,
        }

        self.assertTrue(analyze_log.enrich_frame(record))
        self.assertEqual(record["direction"], "EPS_TO_LKAS")
        self.assertEqual(record["driver_torque_candidate"], 27)
        self.assertEqual(record["motor_torque_signed_candidate"], 0)

    def test_finds_active_intervals_without_markers(self) -> None:
        records = [
            {"type": "frame", "len": 4, "t_us": 1_000_000, "lkas_on_candidate": False},
            {
                "type": "frame",
                "len": 4,
                "t_us": 1_010_000,
                "lkas_on_candidate": True,
                "apply_steer_candidate": -5,
            },
            {
                "type": "frame",
                "len": 4,
                "t_us": 1_020_000,
                "lkas_on_candidate": True,
                "apply_steer_candidate": 8,
            },
            {"type": "frame", "len": 4, "t_us": 1_030_000, "lkas_on_candidate": False},
        ]

        intervals = analyze_log.lkas_active_intervals(records)
        self.assertEqual(len(intervals), 1)
        self.assertEqual(intervals[0]["frames"], 2)
        self.assertEqual(intervals[0]["command_min"], -5)
        self.assertEqual(intervals[0]["command_max"], 8)

    def test_reports_sequence_gaps(self) -> None:
        records = [{"seq": 10}, {"seq": 11}, {"seq": 15}, {"seq": 14}]
        self.assertEqual(analyze_log.sequence_gaps(records), (1, 3, 1))


class CaptureSerialTests(unittest.TestCase):
    def test_recovers_json_after_boot_noise(self) -> None:
        raw = b"\x80boot-noise" + b'{"type":"session","schema":1}\r\n'

        line, record, prefix = capture_serial.parse_json_record(raw)
        self.assertEqual(line, '{"type":"session","schema":1}')
        self.assertEqual(record["type"], "session")
        self.assertEqual(prefix, b"\x80boot-noise")

    def test_sequence_transition(self) -> None:
        self.assertEqual(capture_serial.sequence_transition(None, 10), (10, 0, False))
        self.assertEqual(capture_serial.sequence_transition(10, 14), (14, 3, False))
        self.assertEqual(capture_serial.sequence_transition(14, 13), (13, 0, True))
        self.assertEqual(capture_serial.sequence_transition(13, None), (13, 0, False))


if __name__ == "__main__":
    unittest.main()
