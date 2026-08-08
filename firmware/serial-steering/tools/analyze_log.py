#!/usr/bin/env python3
"""Summarize and optionally plot Honda serial logger JSONL."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path
from statistics import median


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

PLOT_LABELS = {
    "driver_torque_candidate": "driver torque\ncandidate",
    "apply_steer_candidate": "steer command\ncandidate",
    "motor_torque_signed_candidate": "motor torque\ncandidate",
    "lkas_on_candidate": "LKAS on\ncandidate",
    "flags_raw": "flags raw",
    "flags_b0_raw": "flags b0",
    "flags_b1_raw": "flags b1",
    "flags_b2_raw": "flags b2",
}


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


def serial_checksum(data: bytes) -> int:
    return ((256 - sum(data)) % 256) % 128 + 128


def decode_signed_9(big: int, little: int) -> int:
    raw = ((big & 0x07) << 5) | (little & 0x1F)
    return raw - 256 if big & 0x08 else raw


def enrich_frame(record: dict) -> bool:
    """Add provisional fields to compact frame records without changing raw data."""
    if record.get("type") != "frame" or not isinstance(record.get("data"), str):
        return False
    try:
        frame = bytes.fromhex(record["data"])
    except ValueError:
        return False
    if len(frame) not in (4, 5) or len(frame) != record.get("len"):
        return False
    if serial_checksum(frame[:-1]) != frame[-1]:
        return False

    if len(frame) == 4:
        big = frame[0] & 0x0F
        little = frame[1] & 0x1F
        decoded = {
            "counter_raw": frame[0] >> 5,
            "big_steer_raw": big,
            "little_steer_raw": little,
            "flags_raw": frame[2],
            "apply_steer_candidate": decode_signed_9(big, little),
            "lkas_on_candidate": bool((frame[1] >> 5) & 1),
        }
        record.setdefault("direction", "LKAS_TO_EPS")
    else:
        big = frame[0] & 0x0F
        little = frame[1] & 0x1F
        motor_raw = (
            (((frame[2] >> 4) & 0x03) << 8)
            | (((frame[2] >> 3) & 0x01) << 7)
            | (frame[3] & 0x7F)
        )
        decoded = {
            "big_driver_torque_raw": big,
            "little_driver_torque_raw": little,
            "driver_torque_candidate": decode_signed_9(big, little),
            "motor_torque_raw_10bit": motor_raw,
            "motor_torque_signed_candidate": motor_raw - 1024
            if motor_raw & 0x0200
            else motor_raw,
            "flags_b0_raw": frame[0],
            "flags_b1_raw": frame[1],
            "flags_b2_raw": frame[2],
        }
        record.setdefault("direction", "EPS_TO_LKAS")
    for field, value in decoded.items():
        record.setdefault(field, value)
    record["offline_decoded"] = True
    return True


def load_records(path: Path) -> tuple[list[dict], int]:
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
            enrich_frame(record)
            records.append(record)
    return records, malformed


def sequence_gaps(records: list[dict]) -> tuple[int, int, int]:
    previous: int | None = None
    events = missing = nonmonotonic = 0
    for record in records:
        current = record.get("seq")
        if not isinstance(current, int) or isinstance(current, bool):
            continue
        if previous is not None:
            if current > previous + 1:
                events += 1
                missing += current - previous - 1
            elif current <= previous:
                nonmonotonic += 1
        previous = current
    return events, missing, nonmonotonic


def lkas_active_intervals(
    records: list[dict], max_gap_seconds: float = 0.05
) -> list[dict[str, float | int]]:
    frames = sorted(
        (
            record
            for record in records
            if record.get("type") == "frame"
            and record.get("len") == 4
            and isinstance(record.get("t_us"), (int, float))
        ),
        key=lambda record: float(record["t_us"]),
    )
    intervals: list[dict[str, float | int]] = []
    active: list[dict] = []

    def finish() -> None:
        if not active:
            return
        commands = [
            int(record["apply_steer_candidate"])
            for record in active
            if isinstance(record.get("apply_steer_candidate"), int)
        ]
        start = float(active[0]["t_us"]) / 1_000_000
        end = float(active[-1]["t_us"]) / 1_000_000
        intervals.append(
            {
                "start": start,
                "end": end,
                "duration": end - start,
                "frames": len(active),
                "command_min": min(commands) if commands else 0,
                "command_max": max(commands) if commands else 0,
            }
        )
        active.clear()

    for frame in frames:
        if active:
            gap = (float(frame["t_us"]) - float(active[-1]["t_us"])) / 1_000_000
            if gap > max_gap_seconds:
                finish()
        if frame.get("lkas_on_candidate") is True:
            active.append(frame)
        else:
            finish()
    finish()
    return intervals


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
                f"break={stats.get('break_err', 0)} "
                f"fifo={stats.get('fifo_overflow', 0)} "
                f"capture_drop={stats.get('capture_queue_drop', 0)} "
                f"output_drop={stats.get('queue_drop', 0)} "
                f"captured_output_drop={stats.get('captured_output_drop', 0)}"
            )
    for (channel, error), count in sorted(uart_errors.items()):
        print(f"uart error channel {channel}: {error}={count}")
    if malformed:
        print(f"malformed JSONL lines: {malformed}")

    intervals = lkas_active_intervals(records)
    if intervals:
        print("LKAS active intervals (automatic 4-byte hypothesis):")
        for index, interval in enumerate(intervals, start=1):
            print(
                f"  {index}: {interval['start']:.3f}-{interval['end']:.3f}s "
                f"duration={interval['duration']:.3f}s frames={interval['frames']} "
                f"command={interval['command_min']}..{interval['command_max']}"
            )
    elif any(record.get("type") == "frame" and record.get("len") == 4 for record in records):
        print("LKAS active intervals: none detected")


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
            intervals = [right[0] - left[0] for left, right in zip(points, points[1:])]
            typical_interval = median(intervals) if intervals else 0.01
            break_after = max(0.1, typical_interval * 5)
            times: list[float] = []
            values: list[float] = []
            previous_time: float | None = None
            for point_time, point_value in points:
                if previous_time is not None and point_time - previous_time > break_after:
                    times.append(float("nan"))
                    values.append(float("nan"))
                times.append(point_time)
                values.append(point_value)
                previous_time = point_time
            series[field] = (times, values)
    if not series:
        raise SystemExit("no provisional decoded fields found in the selected range")

    figure, axes = plt.subplots(
        len(series),
        1,
        sharex=True,
        squeeze=False,
        figsize=(12, 10),
    )
    for axis, (field, (times, values)) in zip(axes[:, 0], series.items()):
        axis.plot(times, values, linewidth=0.8)
        axis.set_ylabel(
            PLOT_LABELS.get(field, field),
            rotation=0,
            horizontalalignment="right",
            verticalalignment="center",
            labelpad=12,
        )
        axis.grid(True, alpha=0.25)
    axes[-1, 0].set_xlabel("device time (s)")
    figure.suptitle("Provisional Honda serial decoding — raw values, unfiltered")
    figure.subplots_adjust(left=0.18, right=0.98, top=0.95, bottom=0.07, hspace=0.28)
    if output:
        figure.savefig(output, dpi=150)
        print(f"wrote {output}")
    else:
        plt.show()


def main() -> None:
    args = parse_args()
    all_records, malformed = load_records(args.log)
    records = [record for record in all_records if selected(record, args)]
    gap_events, missing, nonmonotonic = sequence_gaps(all_records)
    print(
        f"host sequence: gap_events={gap_events} missing_records={missing} "
        f"nonmonotonic={nonmonotonic}"
    )
    print_summary(records, malformed)
    if args.plot or args.plot_output:
        plot_records(records, args.plot_output)


if __name__ == "__main__":
    main()
