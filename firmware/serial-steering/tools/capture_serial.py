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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("port", help="serial port, for example COM5 or /dev/ttyUSB0")
    parser.add_argument("output", type=Path, help="destination .jsonl file")
    parser.add_argument("--baud", type=int, default=921600)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        import serial
    except ImportError as error:
        raise SystemExit("pyserial is required: python -m pip install pyserial") from error

    bad_path = args.output.with_suffix(args.output.suffix + ".bad.log")
    session_path = args.output.with_suffix(args.output.suffix + ".session.json")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    metadata = {
        "host_started_utc": utc_now(),
        "port": args.port,
        "baud": args.baud,
        "output": str(args.output.resolve()),
    }
    session_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    commands: SimpleQueue[str] = SimpleQueue()
    threading.Thread(target=keyboard_input, args=(commands,), daemon=True).start()
    counts: Counter[str] = Counter()
    clean_shutdown = False
    last_flush = last_summary = time.monotonic()

    with args.output.open("a", encoding="utf-8", newline="\n") as output, bad_path.open(
        "a", encoding="utf-8", newline="\n"
    ) as bad, serial.Serial(args.port, args.baud, timeout=0.2) as connection:
        print("capturing; type !status or !mark <text>; Ctrl+C stops")
        try:
            while True:
                try:
                    while True:
                        command = commands.get_nowait()
                        connection.write((command + "\n").encode("utf-8"))
                except Empty:
                    pass

                raw = connection.readline()
                if raw:
                    try:
                        line = raw.decode("utf-8").rstrip("\r\n")
                        record = json.loads(line)
                        if not isinstance(record, dict):
                            raise ValueError("JSON record is not an object")
                    except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                        bad.write(raw.decode("utf-8", errors="backslashreplace").rstrip("\r\n") + "\n")
                        counts["bad"] += 1
                    else:
                        output.write(line + "\n")
                        counts[str(record.get("type", "unknown"))] += 1

                now = time.monotonic()
                if now - last_flush >= 1:
                    output.flush()
                    bad.flush()
                    last_flush = now
                if now - last_summary >= 2:
                    print(
                        f"frames={counts['frame']} raw={counts['raw_fragment']} "
                        f"errors={counts['uart_error']} bad={counts['bad']}"
                    )
                    last_summary = now
        except KeyboardInterrupt:
            clean_shutdown = True
        finally:
            output.flush()
            bad.flush()
            if clean_shutdown:
                os.fsync(output.fileno())
                os.fsync(bad.fileno())

    metadata.update(
        host_ended_utc=utc_now(), clean_shutdown=clean_shutdown, counts=dict(counts)
    )
    session_path.write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"saved {counts['frame']} frames to {args.output}")


if __name__ == "__main__":
    main()
