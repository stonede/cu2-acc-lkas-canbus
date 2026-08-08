#!/usr/bin/env python3
"""Capture ESP32 logger JSONL without mixing host status into the data file."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
from queue import Empty, SimpleQueue
import threading
import time


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def keyboard_input(commands: SimpleQueue[str]) -> None:
    while True:
        try:
            command = input()
        except EOFError:
            return
        if command == "!status" or command.startswith("!mark "):
            commands.put(command)
        elif command:
            print("keyboard accepts !status or !mark <text>")


def sequence_transition(previous: int | None, current: object) -> tuple[int | None, int, bool]:
    """Return updated sequence, missing-record count, and non-monotonic flag."""
    if not isinstance(current, int) or isinstance(current, bool):
        return previous, 0, False
    if previous is None:
        return current, 0, False
    if current > previous:
        return current, max(0, current - previous - 1), False
    return current, 0, True


def parse_json_record(raw: bytes) -> tuple[str, dict, bytes]:
    """Parse one JSON object, recovering it from a non-JSON startup prefix."""
    stripped = raw.rstrip(b"\r\n")
    starts = [index for index, value in enumerate(stripped) if value == ord("{")]
    for start in starts:
        try:
            line = stripped[start:].decode("utf-8")
            record = json.loads(line)
            if not isinstance(record, dict):
                continue
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
        return line, record, stripped[:start]
    raise ValueError("line does not contain one complete JSON object")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="serial port, for example COM5 or /dev/ttyUSB0")
    parser.add_argument("output", type=Path, help="destination .jsonl file")
    parser.add_argument("--baud", type=int, default=460800)
    parser.add_argument(
        "--decoded-json",
        action="store_true",
        help="ask firmware for verbose decoded fields (compact raw frames are the default)",
    )
    parser.add_argument(
        "--rx-buffer",
        type=int,
        default=1024 * 1024,
        help="requested host serial receive buffer size in bytes (default: 1 MiB)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        help="stop cleanly after this many seconds (default: run until Ctrl+C)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.duration is not None and args.duration <= 0:
        raise SystemExit("--duration must be greater than zero")
    try:
        import serial
    except ImportError as error:
        raise SystemExit("pyserial is required: python -m pip install pyserial") from error

    bad_path = args.output.with_suffix(args.output.suffix + ".bad.log")
    gaps_path = args.output.with_suffix(args.output.suffix + ".gaps.jsonl")
    session_path = args.output.with_suffix(args.output.suffix + ".session.json")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "host_started_utc": utc_now(),
        "port": args.port,
        "baud": args.baud,
        "output": str(args.output.resolve()),
        "json_mode_requested": "decoded" if args.decoded_json else "compact",
        "rx_buffer_requested": args.rx_buffer,
        "duration_requested_seconds": args.duration,
    }
    session_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    commands: SimpleQueue[str] = SimpleQueue()
    threading.Thread(target=keyboard_input, args=(commands,), daemon=True).start()
    counts: Counter[str] = Counter()
    clean_shutdown = False
    last_flush = last_summary = time.monotonic()
    last_sequence: int | None = None
    sequence_gap_events = 0
    sequence_records_missing = 0
    sequence_nonmonotonic = 0
    desired_decode = "on" if args.decoded_json else "off"
    decode_mode_confirmed = False
    configure_attempts = 0
    next_configure = time.monotonic() + 1.0
    rx_buffer_configured = False
    input_buffer_reset = False
    capture_started = time.monotonic()

    with args.output.open("a", encoding="utf-8", newline="\n") as output, bad_path.open(
        "a", encoding="utf-8", newline="\n"
    ) as bad, gaps_path.open("a", encoding="utf-8", newline="\n") as gaps, serial.Serial(
        args.port, args.baud, timeout=0.2
    ) as connection:
        try:
            connection.set_buffer_size(rx_size=args.rx_buffer)
            rx_buffer_configured = True
        except (AttributeError, NotImplementedError, OSError, ValueError):
            pass
        connection.reset_input_buffer()
        input_buffer_reset = True
        print(
            f"capturing compact={'no' if args.decoded_json else 'yes'}; "
            "markers are optional; Ctrl+C stops"
        )
        try:
            while True:
                now = time.monotonic()
                if args.duration is not None and now - capture_started >= args.duration:
                    clean_shutdown = True
                    break
                if (
                    not decode_mode_confirmed
                    and configure_attempts < 5
                    and now >= next_configure
                ):
                    connection.write(f"!decode {desired_decode}\n".encode("ascii"))
                    configure_attempts += 1
                    next_configure = now + 1.0

                try:
                    while True:
                        command = commands.get_nowait()
                        connection.write((command + "\n").encode("utf-8"))
                except Empty:
                    pass

                raw = connection.readline()
                if raw:
                    try:
                        line, record, discarded_prefix = parse_json_record(raw)
                    except ValueError:
                        bad.write(raw.decode("utf-8", errors="backslashreplace").rstrip("\r\n") + "\n")
                        category = (
                            "startup_noise"
                            if time.monotonic() - capture_started < 2.0
                            else "bad"
                        )
                        counts[category] += 1
                    else:
                        if discarded_prefix:
                            bad.write(
                                discarded_prefix.decode(
                                    "utf-8", errors="backslashreplace"
                                ).rstrip("\r\n")
                                + "\n"
                            )
                            category = (
                                "boot_noise"
                                if record.get("type") == "session"
                                else "bad_prefix"
                            )
                            counts[category] += 1
                        output.write(line + "\n")
                        counts[str(record.get("type", "unknown"))] += 1
                        if (
                            record.get("type") == "console"
                            and record.get("status") == "ok"
                            and record.get("message") == f"decode {desired_decode}"
                        ):
                            decode_mode_confirmed = True

                        previous_sequence = last_sequence
                        last_sequence, missing, nonmonotonic = sequence_transition(
                            last_sequence, record.get("seq")
                        )
                        if missing:
                            sequence_gap_events += 1
                            sequence_records_missing += missing
                            gap_record = {
                                "host_detected_utc": utc_now(),
                                "previous_seq": previous_sequence,
                                "current_seq": last_sequence,
                                "missing": missing,
                                "t_us": record.get("t_us"),
                                "channel": record.get("channel"),
                            }
                            gaps.write(json.dumps(gap_record, separators=(",", ":")) + "\n")
                            print(
                                f"WARNING: sequence gap: missing {missing} records "
                                f"between {previous_sequence} and {last_sequence}"
                            )
                        if nonmonotonic:
                            sequence_nonmonotonic += 1

                now = time.monotonic()
                if now - last_flush >= 1:
                    output.flush()
                    bad.flush()
                    gaps.flush()
                    last_flush = now
                if now - last_summary >= 2:
                    bad_count = counts["bad"] + counts["bad_prefix"]
                    print(
                        f"frames={counts['frame']} raw={counts['raw_fragment']} "
                        f"errors={counts['uart_error']} bad={bad_count} "
                        f"seq_missing={sequence_records_missing}"
                    )
                    last_summary = now
        except KeyboardInterrupt:
            clean_shutdown = True
        finally:
            output.flush()
            bad.flush()
            gaps.flush()
            if clean_shutdown:
                os.fsync(output.fileno())
                os.fsync(bad.fileno())
                os.fsync(gaps.fileno())

    metadata.update(
        host_ended_utc=utc_now(),
        clean_shutdown=clean_shutdown,
        counts=dict(counts),
        rx_buffer_configured=rx_buffer_configured,
        input_buffer_reset=input_buffer_reset,
        decode_mode_confirmed=decode_mode_confirmed,
        decode_configure_attempts=configure_attempts,
        sequence_gap_events=sequence_gap_events,
        sequence_records_missing=sequence_records_missing,
        sequence_nonmonotonic=sequence_nonmonotonic,
    )
    session_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"saved {counts['frame']} frames to {args.output}")


if __name__ == "__main__":
    main()
