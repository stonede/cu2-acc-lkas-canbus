#!/usr/bin/env python3
"""Summarize and optionally plot Honda serial logger JSONL."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path


PLOT_FIELDS = (
    "driver_torque_candidate",
    "apply_steer_candidate",
    "motor_torque_signed_candidate",
    "lkas_on_candidate",
    "flags_raw",
    "flags_b0_raw",
    "flags_b1_raw",
    "flags_b2_raw",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("log", type=Path)
    parser.add_argument("--channel", choices=("A", "B"))
    parser.add_argument("--start", type=float, help="minimum device time in seconds")
    parser.add_argument("--end", type=float, help="maximum device time in seconds")
    parser.add_argument("--plot", action="store_true")
    parser.add_argument("--plot-output", type=Path)
    return parser.parse_args()


def selected(record: dict[str, object], args: argparse.Namespace) -> bool:
    if args.channel and record.get("channel") != args.channel:
        return False
    time_us = record.get("t_us")
    if isinstance(time_us, (int, float)):
        if args.start is not None and time_us < args.start * 1_000_000:
            return False
        if args.end is not None and time_us > args.end * 1_000_000:
            return False
    return True


def load_records(path: Path, args: argparse.Namespace) -> tuple[list[dict], int]:
    records = []
    malformed = 0
    with path.open(encoding="utf-8") as source:
        for line in source:
            try:
                record = json.loads(line)
                if not isinstance(record, dict):
                    raise ValueError
            except (json.JSONDecodeError, ValueError):
                malformed += 1
                continue
            if selected(record, args):
                records.append(record)
    return records, malformed


def print_summary(records: list[dict], malformed: int) -> None:
    frames: dict[str, Counter[str]] = defaultdict(Counter)
    uart_errors: dict[tuple[str, str], int] = {}
    latest_stats: dict[str, dict] = {}
    for record in records:
        channel = str(record.get("channel", "-"))
        if record.get("type") == "frame":
            frames[channel]["frames"] += 1
            frames[channel]["checksum_ok"] += bool(record.get("checksum_ok"))
            frames[channel][f"len_{record.get('len')}"] += 1
        elif record.get("type") == "uart_error":
            key = (channel, str(record.get("error", "unknown")))
            uart_errors[key] = max(uart_errors.get(key, 0), int(record.get("count", 1)))
        elif record.get("type") == "stats":
            latest_stats[channel] = record

    for channel in sorted(set(frames) | set(latest_stats)):
        count = frames[channel]["frames"]
        rate = frames[channel]["checksum_ok"] / count if count else 0
        print(
            f"channel {channel}: frames={count} len4={frames[channel]['len_4']} "
            f"len5={frames[channel]['len_5']} checksum={rate:.2%}"
        )
        stats = latest_stats.get(channel, {})
        if stats:
            print(
                "  losses/errors: "
                f"parity={stats.get('parity_err', 0)} frame={stats.get('frame_err', 0)} "
                f"fifo={stats.get('fifo_overflow', 0)} "
                f"capture_drop={stats.get('capture_queue_drop', 0)} "
                f"output_drop={stats.get('queue_drop', 0)} "
                f"captured_output_drop={stats.get('captured_output_drop', 0)}"
            )
    for (channel, error), count in sorted(uart_errors.items()):
        print(f"uart error channel {channel}: {error}={count}")
    if malformed:
        print(f"malformed JSONL lines: {malformed}")


def plot_records(records: list[dict], output: Path | None) -> None:
    try:
        import matplotlib.pyplot as plt
    except ImportError as error:
        raise SystemExit("plotting requires: python -m pip install matplotlib") from error

    series: dict[str, tuple[list[float], list[float]]] = {}
    for field in PLOT_FIELDS:
        points = [
            (float(record["t_us"]) / 1_000_000, float(record[field]))
            for record in records
            if record.get("type") == "frame"
            and isinstance(record.get("t_us"), (int, float))
            and isinstance(record.get(field), (int, float, bool))
        ]
        if points:
            series[field] = ([point[0] for point in points], [point[1] for point in points])
    if not series:
        raise SystemExit("no provisional decoded fields found in the selected range")

    figure, axes = plt.subplots(len(series), 1, sharex=True, squeeze=False)
    for axis, (field, (times, values)) in zip(axes[:, 0], series.items()):
        axis.plot(times, values, linewidth=0.8)
        axis.set_ylabel(field)
        axis.grid(True, alpha=0.25)
    axes[-1, 0].set_xlabel("device time (s)")
    figure.suptitle("Provisional Honda serial decoding — raw values, unfiltered")
    figure.tight_layout()
    if output:
        figure.savefig(output, dpi=150)
        print(f"wrote {output}")
    else:
        plt.show()


def main() -> None:
    args = parse_args()
    records, malformed = load_records(args.log, args)
    print_summary(records, malformed)
    if args.plot or args.plot_output:
        plot_records(records, args.plot_output)


if __name__ == "__main__":
    main()
