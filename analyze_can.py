#!/usr/bin/env python3
"""Rank CAN fields that may command stock ACC/CMBS braking in a Honda CU2."""

from __future__ import annotations

import argparse
import bisect
import csv
import hashlib
import statistics
import tempfile
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

WRAP_US = 1_000_000
MERGE_GAP_US = 200_000
PRE_US = 1_000_000
BASELINE_END_US = 500_000
NEAR_BEFORE_US = 200_000
NEAR_AFTER_US = 200_000

REQUIRED_COLUMNS = {
    "Time Stamp", "ID", "Extended", "Dir", "Bus", "LEN",
    "D1", "D2", "D3", "D4", "D5", "D6", "D7", "D8",
}

KNOWN_IDS = {
    0x158: "ENGINE_DATA / vehicle speed",
    0x17C: "POWERTRAIN_DATA / ACC and pedal state",
    0x1A4: "VSA_STATUS / marker COMPUTER_BRAKING",
    0x1D0: "WHEEL_SPEEDS / vehicle response",
    0x1E7: "BRAKE_PRESSURE / VSA response",
    0x30C: "ACC_HUD / ACC context",
}
# Signal positions follow commaai/opendbc:
# opendbc/dbc/generator/honda/{_honda_common,_nidec_common}.dbc


@dataclass(frozen=True, slots=True)
class Frame:
    time_us: int
    can_id: int
    data: bytes


@dataclass(slots=True)
class LogData:
    role: str
    path: Path
    frames: list[Frame]
    by_id: dict[int, list[Frame]]
    times_by_id: dict[int, list[int]]
    wraps: int
    zero_timestamps: int
    anomalies: int
    sha256: str

    @property
    def duration_us(self) -> int:
        return self.frames[-1].time_us - self.frames[0].time_us


@dataclass(frozen=True, slots=True)
class Event:
    role: str
    index: int
    start_us: int
    end_us: int


@dataclass(frozen=True, slots=True)
class Sample:
    role: str
    event_index: int
    before: float
    during: float
    delta: float
    lead_ms: float | None


def motorola(data: bytes, start_bit: int, length: int) -> int:
    """Extract one unsigned DBC Motorola signal."""
    byte_index, bit_index = divmod(start_bit, 8)
    value = 0
    for _ in range(length):
        if byte_index >= len(data):
            raise ValueError("signal exceeds payload")
        value = (value << 1) | ((data[byte_index] >> bit_index) & 1)
        bit_index -= 1
        if bit_index < 0:
            byte_index += 1
            bit_index = 7
    return value


def rebuild_timestamps(raw: list[int]) -> tuple[list[int], int, int]:
    """Unwrap SavvyCAN's microsecond field and interpolate zero timestamps."""
    if not raw:
        raise ValueError("empty CSV")

    anchors: list[tuple[int, int]] = []
    epoch = wraps = anomalies = 0
    previous_raw: int | None = None
    previous_absolute: int | None = None

    for index, value in enumerate(raw):
        if value == 0:
            continue
        if not 0 <= value < WRAP_US:
            raise ValueError(f"timestamp outside 0..{WRAP_US - 1}: {value}")
        if previous_raw is not None and previous_raw - value > WRAP_US // 2:
            epoch += 1
            wraps += 1
        absolute = epoch * WRAP_US + value
        if previous_absolute is not None and absolute < previous_absolute:
            anomalies += 1
            absolute = previous_absolute
        anchors.append((index, absolute))
        previous_raw, previous_absolute = value, absolute

    if not anchors:
        raise ValueError("all timestamps are zero")

    steps = [
        (right_time - left_time) / (right_index - left_index)
        for (left_index, left_time), (right_index, right_time)
        in zip(anchors, anchors[1:])
        if right_index > left_index and right_time > left_time
    ]
    typical_step = statistics.median(steps) if steps else 1_000.0
    rebuilt = [0] * len(raw)

    first_index, first_time = anchors[0]
    for index in range(first_index + 1):
        rebuilt[index] = max(0, round(first_time - (first_index - index) * typical_step))

    for (left_index, left_time), (right_index, right_time) in zip(anchors, anchors[1:]):
        distance = right_index - left_index
        for offset in range(distance + 1):
            rebuilt[left_index + offset] = round(
                left_time + (right_time - left_time) * offset / distance
            )

    last_index, last_time = anchors[-1]
    for index in range(last_index, len(raw)):
        rebuilt[index] = round(last_time + (index - last_index) * typical_step)

    for index in range(1, len(rebuilt)):
        if rebuilt[index] < rebuilt[index - 1]:
            anomalies += 1
            rebuilt[index] = rebuilt[index - 1]
    return rebuilt, wraps, anomalies


def parse_log(path: Path, role: str) -> LogData:
    raw_times: list[int] = []
    raw_frames: list[tuple[int, bytes]] = []
    digest = hashlib.sha256()

    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)

    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or not REQUIRED_COLUMNS.issubset(reader.fieldnames):
            raise ValueError(f"{path}: invalid CSV header")
        for line_number, row in enumerate(reader, 2):
            try:
                timestamp = int(row["Time Stamp"])
                can_id = int(row["ID"], 16)
                length = int(row["LEN"])
                if not 0 <= can_id <= 0x1FFFFFFF or not 0 <= length <= 8:
                    raise ValueError
                data = bytes(int(row[f"D{i}"], 16) for i in range(1, length + 1))
            except (KeyError, TypeError, ValueError) as exc:
                raise ValueError(f"{path}:{line_number}: malformed frame") from exc
            raw_times.append(timestamp)
            raw_frames.append((can_id, data))

    timestamps, wraps, anomalies = rebuild_timestamps(raw_times)
    frames = [
        Frame(timestamp, can_id, data)
        for timestamp, (can_id, data) in zip(timestamps, raw_frames)
    ]
    by_id: dict[int, list[Frame]] = defaultdict(list)
    for frame in frames:
        by_id[frame.can_id].append(frame)
    return LogData(
        role=role,
        path=path,
        frames=frames,
        by_id=dict(by_id),
        times_by_id={
            can_id: [frame.time_us for frame in series]
            for can_id, series in by_id.items()
        },
        wraps=wraps,
        zero_timestamps=raw_times.count(0),
        anomalies=anomalies,
        sha256=digest.hexdigest(),
    )


def braking_events(log: LogData) -> list[Event]:
    marker = log.by_id.get(0x1A4, [])
    intervals: list[tuple[int, int]] = []
    start: int | None = None
    last_active: int | None = None

    for frame in marker:
        active = bool(motorola(frame.data, 23, 1))
        if active and start is None:
            start = frame.time_us
        if active:
            last_active = frame.time_us
        elif start is not None and last_active is not None:
            intervals.append((start, last_active))
            start = last_active = None
    if start is not None and last_active is not None:
        intervals.append((start, last_active))

    merged: list[list[int]] = []
    for start, end in intervals:
        if merged and start - merged[-1][1] <= MERGE_GAP_US:
            merged[-1][1] = end
        else:
            merged.append([start, end])
    return [
        Event(log.role, index, start, end)
        for index, (start, end) in enumerate(merged, 1)
    ]


def frames_between(log: LogData, can_id: int, start_us: int, end_us: int) -> list[Frame]:
    series = log.by_id.get(can_id, [])
    times = log.times_by_id.get(can_id, [])
    return series[bisect.bisect_left(times, start_us):bisect.bisect_right(times, end_us)]


def frame_at(log: LogData, can_id: int, time_us: int) -> Frame | None:
    series = log.by_id.get(can_id, [])
    times = log.times_by_id.get(can_id, [])
    index = bisect.bisect_right(times, time_us) - 1
    return series[index] if index >= 0 else None


def masked_payload(data: bytes) -> bytes:
    """Ignore the common Honda checksum nibble and two-bit rolling counter."""
    if not data:
        return data
    masked = bytearray(data)
    masked[-1] &= 0xC0
    return bytes(masked)


def feature_names(length: int) -> list[str]:
    names = [f"D{i + 1}" for i in range(length)]
    names += [f"D{i + 1}:D{i + 2}" for i in range(length - 1)]
    for byte_index in range(length):
        lowest_bit = 6 if byte_index == length - 1 else 0
        names += [f"D{byte_index + 1}.b{bit}" for bit in range(7, lowest_bit - 1, -1)]
    return names


def feature_value(data: bytes, name: str) -> int:
    data = masked_payload(data)
    if ":" in name:
        left = int(name[1:name.index(":")]) - 1
        return (data[left] << 8) | data[left + 1]
    if ".b" in name:
        byte_text, bit_text = name.split(".b")
        return (data[int(byte_text[1:]) - 1] >> int(bit_text)) & 1
    return data[int(name[1:]) - 1]


def event_samples(
    logs: dict[str, LogData],
    events: dict[str, list[Event]],
) -> dict[tuple[int, str], list[Sample]]:
    samples: dict[tuple[int, str], list[Sample]] = defaultdict(list)
    all_ids = sorted({can_id for log in logs.values() for can_id in log.by_id})

    work: list[tuple[str, LogData, Event]] = []
    for role in ("acc_brake", "cmbs", "set_speed"):
        work += [(role, logs[role], event) for event in events[role]]

    baseline = logs["baseline"]
    excluded = events["baseline"]
    pseudo_index = 0
    cursor = baseline.frames[0].time_us + 2_000_000
    limit = baseline.frames[-1].time_us - 2_000_000
    while cursor <= limit:
        if all(cursor < event.start_us - 2_000_000 or cursor > event.end_us + 2_000_000 for event in excluded):
            pseudo_index += 1
            work.append(("control", baseline, Event("control", pseudo_index, cursor, cursor)))
        cursor += 3_000_000

    for role, log, event in work:
        for can_id in all_ids:
            before_frames = frames_between(
                log, can_id, event.start_us - PRE_US, event.start_us - BASELINE_END_US
            )
            near_frames = frames_between(
                log, can_id, event.start_us - NEAR_BEFORE_US, event.start_us + NEAR_AFTER_US
            )
            if not before_frames or not near_frames:
                continue
            length = min(len(frame.data) for frame in before_frames + near_frames)
            for name in feature_names(length):
                before = statistics.median(feature_value(frame.data, name) for frame in before_frames)
                during = statistics.median(feature_value(frame.data, name) for frame in near_frames)
                lead_ms: float | None = None
                for frame in frames_between(
                    log, can_id, event.start_us - BASELINE_END_US, event.start_us + NEAR_AFTER_US
                ):
                    if feature_value(frame.data, name) != round(before):
                        lead_ms = (frame.time_us - event.start_us) / 1_000
                        break
                samples[(can_id, name)].append(
                    Sample(role, event.index, before, during, during - before, lead_ms)
                )
    return samples


def fraction_in_direction(samples: list[Sample], direction: int, threshold: float) -> float:
    if not samples:
        return 0.0
    return sum(
        1 for sample in samples
        if abs(sample.delta) >= threshold and (1 if sample.delta > 0 else -1) == direction
    ) / len(samples)


def rank_candidates(
    samples: dict[tuple[int, str], list[Sample]],
    events: dict[str, list[Event]],
) -> list[dict[str, object]]:
    ranked: list[dict[str, object]] = []
    expected = {
        role: len(events[role])
        for role in ("acc_brake", "cmbs", "set_speed")
    }

    for (can_id, name), feature_samples in samples.items():
        grouped = {
            role: [sample for sample in feature_samples if sample.role == role]
            for role in ("acc_brake", "cmbs", "set_speed", "control")
        }
        primary = grouped["acc_brake"] + grouped["cmbs"]
        if not primary:
            continue
        values = [value for sample in feature_samples for value in (sample.before, sample.during)]
        span = max(values) - min(values)
        threshold = 0.5 if ".b" in name else max(1.0, span * 0.02)
        positive = sum(sample.delta >= threshold for sample in primary)
        negative = sum(sample.delta <= -threshold for sample in primary)
        direction = 1 if positive >= negative else -1
        significant = [sample for sample in primary if abs(sample.delta) >= threshold]
        if not significant:
            continue

        primary_total = max(1, expected["acc_brake"] + expected["cmbs"])
        consistency = max(positive, negative) / primary_total
        brk = fraction_in_direction(grouped["acc_brake"], direction, threshold)
        cmb = fraction_in_direction(grouped["cmbs"], direction, threshold)
        set_speed = fraction_in_direction(grouped["set_speed"], direction, threshold)
        control = fraction_in_direction(grouped["control"], direction, threshold)
        matching = [
            sample for sample in significant
            if (1 if sample.delta > 0 else -1) == direction
        ]
        lead = (
            sum(sample.lead_ms is not None and sample.lead_ms <= 0 for sample in matching)
            / len(matching)
            if matching else 0.0
        )
        magnitude = min(
            1.0,
            statistics.median(abs(sample.delta) for sample in matching)
            / max(threshold, span * 0.25, 1.0),
        ) if matching else 0.0
        score = (
            0.35 * consistency
            + 0.20 * lead
            + 0.15 * magnitude
            + 0.20 * (1 - control)
            + 0.10 * set_speed
        )
        if can_id == 0x1A4:
            score *= 0.45
        elif can_id in KNOWN_IDS:
            score *= 0.70
        leads = [sample.lead_ms for sample in matching if sample.lead_ms is not None]
        ranked.append({
            "can_id": can_id,
            "feature": name,
            "score": score,
            "direction": direction,
            "consistency": consistency,
            "brk": brk,
            "cmb": cmb,
            "set_speed": set_speed,
            "control": control,
            "lead_ms": statistics.median(leads) if leads else None,
            "cmbs_only": cmb * (1 - brk) * (1 - control),
            "samples": matching,
        })

    ranked.sort(key=lambda row: (-float(row["score"]), int(row["can_id"]), str(row["feature"])))
    best_by_id: dict[int, dict[str, object]] = {}
    for row in ranked:
        best_by_id.setdefault(int(row["can_id"]), row)
    return list(best_by_id.values())


def confidence(row: dict[str, object]) -> str:
    score = float(row["score"])
    if score >= 0.75 and float(row["brk"]) >= 0.5 and float(row["cmb"]) >= 0.5:
        return "high"
    if score >= 0.55 and float(row["brk"]) > 0 and float(row["cmb"]) > 0:
        return "medium"
    return "hypothesis"


def payload_text(frame: Frame | None) -> str:
    return frame.data.hex(" ").upper() if frame else "—"


def example_payloads(
    row: dict[str, object],
    logs: dict[str, LogData],
    events: dict[str, list[Event]],
) -> str:
    matching = list(row["samples"])
    if not matching:
        return "—"
    sample = matching[0]
    event = events[sample.role][sample.event_index - 1]
    log = logs[sample.role]
    can_id = int(row["can_id"])
    return " → ".join((
        payload_text(frame_at(log, can_id, event.start_us - 600_000)),
        payload_text(frame_at(log, can_id, event.start_us + 100_000)),
        payload_text(frame_at(log, can_id, event.end_us + 300_000)),
    ))


def known_signal_at(log: LogData, can_id: int, time_us: int, start: int, length: int) -> int | None:
    frame = frame_at(log, can_id, time_us)
    return motorola(frame.data, start, length) if frame else None


def render_report(
    logs: dict[str, LogData],
    events: dict[str, list[Event]],
    ranked: list[dict[str, object]],
) -> str:
    lines = [
        "# Honda Accord CU2 Brake Command Analysis",
        "",
        "> Heuristic report. Correlation does not prove that a frame is a safe TX command.",
        "",
        "## Input data",
        "",
        "| Role | File | Frames | Duration | IDs | Zero timestamps | Wraps | Anomalies | SHA-256 |",
        "|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    role_names = {
        "baseline": "normal ACC/LKAS driving",
        "set_speed": "braking after reducing the ACC set speed",
        "acc_brake": "ACC braking behind a lead vehicle",
        "cmbs": "braking with CMBS activation",
    }
    for role in ("baseline", "set_speed", "acc_brake", "cmbs"):
        log = logs[role]
        lines.append(
            f"| {role_names[role]} | `{log.path.name}` | {len(log.frames)} | "
            f"{log.duration_us / 1_000_000:.2f} s | {len(log.by_id)} | "
            f"{log.zero_timestamps} | {log.wraps} | {log.anomalies} | `{log.sha256[:12]}` |"
        )

    all_ids = sorted({can_id for log in logs.values() for can_id in log.by_id})
    lines += [
        "",
        f"- `0x1E7`: {'present' if 0x1E7 in all_ids else 'absent'}.",
        f"- Standard Nidec `0x1FA`: {'present' if 0x1FA in all_ids else 'absent from every log'}.",
        "",
        "## Frame frequencies",
        "",
        "| ID | bra | bra2 | brk_full | cmb |",
        "|---:|---:|---:|---:|---:|",
    ]
    for can_id in all_ids:
        rates = []
        for role in ("baseline", "set_speed", "acc_brake", "cmbs"):
            log = logs[role]
            rates.append(len(log.by_id.get(can_id, [])) / max(log.duration_us / 1_000_000, 0.001))
        lines.append(
            f"| `0x{can_id:03X}` | {rates[0]:.1f} Hz | {rates[1]:.1f} Hz | "
            f"{rates[2]:.1f} Hz | {rates[3]:.1f} Hz |"
        )

    lines += [
        "",
        "## Detected `0x1A4 COMPUTER_BRAKING` intervals",
        "",
        "| Log | # | Start | End | Duration | Speed before → after | 0x1E7 raw before → max | 0x17C / 0x30C context |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for role in ("baseline", "set_speed", "acc_brake", "cmbs"):
        log = logs[role]
        origin = log.frames[0].time_us
        for event in events[role]:
            speed_before = known_signal_at(log, 0x158, event.start_us - 500_000, 7, 16)
            speed_after = known_signal_at(log, 0x158, event.end_us + 300_000, 7, 16)
            pressure_before = known_signal_at(log, 0x1E7, event.start_us - 500_000, 7, 10)
            pressure_frames = frames_between(log, 0x1E7, event.start_us, event.end_us)
            pressure_peak = max(
                (max(motorola(frame.data, 7, 10), motorola(frame.data, 9, 10))
                 for frame in pressure_frames),
                default=None,
            )
            speed_text = (
                f"{speed_before * 0.01:.1f} → {speed_after * 0.01:.1f} km/h"
                if speed_before is not None and speed_after is not None else "—"
            )
            pressure_text = (
                f"{pressure_before} → {pressure_peak}"
                if pressure_before is not None and pressure_peak is not None else "—"
            )
            acc_status = known_signal_at(log, 0x17C, event.start_us - 100_000, 38, 1)
            pedal_brake = known_signal_at(log, 0x17C, event.start_us - 100_000, 53, 1)
            cruise_speed = known_signal_at(log, 0x30C, event.start_us - 100_000, 31, 8)
            hud_lead = known_signal_at(log, 0x30C, event.start_us - 100_000, 45, 2)
            context = (
                f"ACC={acc_status}, brake pedal={pedal_brake}, set={cruise_speed} km/h, lead={hud_lead}"
                if None not in (acc_status, pedal_brake, cruise_speed, hud_lead) else "—"
            )
            lines.append(
                f"| `{log.path.name}` | {event.index} | "
                f"{(event.start_us - origin) / 1_000_000:.3f} s | "
                f"{(event.end_us - origin) / 1_000_000:.3f} s | "
                f"{(event.end_us - event.start_us) / 1_000_000:.2f} s | "
                f"{speed_text} | {pressure_text} | {context} |"
            )

    lines += [
        "",
        "## Candidate ranking",
        "",
        "The score is relative: it rewards changes before the marker, agreement between "
        "`brk_full` and `cmb`, confirmation in `bra2`, and the absence of similar changes "
        "in control windows from `bra`.",
        "",
        "| # | ID / field | Known role | Score | Confidence | brk | cmb | bra2 | Control false positives | Lead | Payload before → during → after |",
        "|---:|---|---|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for index, row in enumerate(ranked[:20], 1):
        can_id = int(row["can_id"])
        lead = row["lead_ms"]
        lines.append(
            f"| {index} | `0x{can_id:03X}` `{row['feature']}` | "
            f"{KNOWN_IDS.get(can_id, 'unknown')} | {float(row['score']):.3f} | "
            f"{confidence(row)} | {float(row['brk']):.0%} | {float(row['cmb']):.0%} | "
            f"{float(row['set_speed']):.0%} | {float(row['control']):.0%} | "
            f"{f'{float(lead):+.0f} ms' if lead is not None else '—'} | "
            f"`{example_payloads(row, logs, events)}` |"
        )

    cmbs_rows = sorted(ranked, key=lambda row: -float(row["cmbs_only"]))
    lines += [
        "",
        "## CMBS-specific changes",
        "",
        "These fields may represent AEB/CMBS status rather than a pressure command.",
        "",
        "| ID / pole | CMBS-only | cmb | brk_full | Kontrola |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in cmbs_rows[:10]:
        lines.append(
            f"| `0x{int(row['can_id']):03X}` `{row['feature']}` | "
            f"{float(row['cmbs_only']):.3f} | {float(row['cmb']):.0%} | "
            f"{float(row['brk']):.0%} | {float(row['control']):.0%} |"
        )

    unknown = next((row for row in ranked if int(row["can_id"]) not in KNOWN_IDS), None)
    lines += ["", "## Conclusion", ""]
    if unknown:
        lines.append(
            f"The highest-ranked unknown frame is `0x{int(unknown['can_id']):03X}` "
            f"(`{unknown['feature']}`, score {float(unknown['score']):.3f}, "
            f"confidence: **{confidence(unknown)}**). It is a candidate for further decoding, "
            "not a confirmed command."
        )
    else:
        lines.append("No unknown candidate met the minimum criteria.")
    lines += [
        "",
        "The next capture should contain separate, annotated trials: steady ACC without braking, "
        "one ACC set-speed reduction, one lead-vehicle braking event, and one separate CMBS event. "
        "Confirmation requires the same field to repeat with similar lead time; do not transmit "
        "candidate frames on public roads.",
        "",
        "## Method and limitations",
        "",
        "- Counter and checksum bits in the lower six bits of the last byte are ignored for ranking.",
        "- `0x1A4`, `0x1E7`, `0x158`, `0x1D0`, `0x17C`, and `0x30C` are tagged as known status/response frames.",
        "- Zero timestamps are interpolated and the microsecond field is unwrapped once per second.",
        "- The analysis does not create TX frames or modify openpilot or panda safety code.",
        "",
    ]
    return "\n".join(lines)


def synthetic_log(role: str, command: bool, marker: bool) -> LogData:
    frames: list[Frame] = []
    for tick in range(400):
        time_us = tick * 20_000
        active_command = command and 2_700_000 <= time_us <= 4_000_000
        active_marker = marker and 3_000_000 <= time_us <= 4_000_000
        counter = tick % 4
        checksum = (tick * 7) & 0xF
        frames.append(Frame(time_us, 0x123, bytes([
            0x80 if active_command else 0,
            0,
            (counter << 4) | checksum,
        ])))
        frames.append(Frame(time_us, 0x1A4, bytes([
            0,
            0,
            0x80 if active_marker else 0,
            (counter << 4) | checksum,
            0, 0, 0, (counter << 4) | checksum,
        ])))
    frames.sort(key=lambda frame: (frame.time_us, frame.can_id))
    by_id: dict[int, list[Frame]] = defaultdict(list)
    for frame in frames:
        by_id[frame.can_id].append(frame)
    return LogData(
        role, Path(f"{role}.csv"), frames, dict(by_id),
        {can_id: [frame.time_us for frame in series] for can_id, series in by_id.items()},
        7, 0, 0, "0" * 64,
    )


def self_test() -> None:
    rebuilt, wraps, anomalies = rebuild_timestamps([990_000, 0, 1_000, 2_000])
    assert wraps == 1 and anomalies == 0
    assert rebuilt == sorted(rebuilt) and 990_000 < rebuilt[1] < 1_001_000
    assert motorola(bytes([0, 0, 0x80]), 23, 1) == 1
    assert masked_payload(bytes([0x12, 0xFF])) == bytes([0x12, 0xC0])

    logs = {
        "baseline": synthetic_log("baseline", False, False),
        "set_speed": synthetic_log("set_speed", True, True),
        "acc_brake": synthetic_log("acc_brake", True, True),
        "cmbs": synthetic_log("cmbs", True, True),
    }
    events = {role: braking_events(log) for role, log in logs.items()}
    ranked = rank_candidates(event_samples(logs, events), events)
    assert ranked and ranked[0]["can_id"] == 0x123, ranked[:3]

    with tempfile.TemporaryDirectory() as directory:
        invalid = Path(directory) / "invalid.csv"
        invalid.write_text("bad,header\n1,2\n", encoding="utf-8")
        try:
            parse_log(invalid, "invalid")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid header was accepted")
    print("self-test: OK")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("bra.csv"))
    parser.add_argument("--set-speed", type=Path, default=Path("bra2.csv"))
    parser.add_argument("--acc-brake", type=Path, default=Path("brk_full.csv"))
    parser.add_argument("--cmbs", type=Path, default=Path("cmb.csv"))
    parser.add_argument("--output", type=Path, default=Path("analysis_report.md"))
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.self_test:
        self_test()
        return
    paths = {
        "baseline": args.baseline,
        "set_speed": args.set_speed,
        "acc_brake": args.acc_brake,
        "cmbs": args.cmbs,
    }
    logs = {}
    for role, path in paths.items():
        print(f"reading {path}...")
        logs[role] = parse_log(path, role)
    events = {role: braking_events(log) for role, log in logs.items()}
    if not events["acc_brake"] or not events["cmbs"]:
        raise SystemExit("no COMPUTER_BRAKING events in brk_full/cmb logs")
    samples = event_samples(logs, events)
    ranked = rank_candidates(samples, events)
    report = render_report(logs, events, ranked)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    print(
        f"wrote {args.output} ({len(ranked)} candidate IDs; "
        f"{sum(len(items) for items in events.values())} braking events)"
    )


if __name__ == "__main__":
    main()
