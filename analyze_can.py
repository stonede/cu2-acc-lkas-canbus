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
RELEASE_AFTER_US = 1_000_000

ROLE_ORDER = (
    "baseline", "set_speed", "acc_brake", "cmbs",
    "idle", "regular", "acc", "lkas",
)
ROLE_NAMES = {
    "baseline": "original mixed capture",
    "set_speed": "ACC set-speed reduction capture",
    "acc_brake": "lead-vehicle ACC braking capture",
    "cmbs": "CMBS capture",
    "idle": "stationary control",
    "regular": "regular-driving control",
    "acc": "ACC-only control",
    "lkas": "ACC+LKAS control",
}

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
    0x33D: "LKAS_HUD / LKAS context",
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
    onset_ms: float | None
    release_ms: float | None
    control: bool = False


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


def sample_event(
    log: LogData,
    event: Event,
    can_id: int,
    name: str,
    control: bool,
) -> Sample | None:
    before_frames = frames_between(
        log, can_id, event.start_us - PRE_US, event.start_us - BASELINE_END_US
    )
    near_frames = frames_between(
        log, can_id, event.start_us - NEAR_BEFORE_US, event.start_us + NEAR_AFTER_US
    )
    if not before_frames or not near_frames:
        return None

    before = statistics.median(feature_value(frame.data, name) for frame in before_frames)
    during = statistics.median(feature_value(frame.data, name) for frame in near_frames)
    delta = during - before
    onset_ms: float | None = None
    release_ms: float | None = None

    if delta:
        direction = 1 if delta > 0 else -1
        threshold = 0.5 if ".b" in name else max(1.0, abs(delta) * 0.25)
        crossings: list[int] = []
        crossed = False
        for frame in frames_between(
            log, can_id, event.start_us - BASELINE_END_US, event.start_us + NEAR_AFTER_US
        ):
            now_crossed = (feature_value(frame.data, name) - before) * direction >= threshold
            if now_crossed and not crossed:
                crossings.append(frame.time_us)
            crossed = now_crossed
        before_marker = [time_us for time_us in crossings if time_us <= event.start_us]
        selected = max(before_marker) if before_marker else (min(crossings) if crossings else None)
        if selected is not None:
            onset_ms = (selected - event.start_us) / 1_000

        if not control:
            for frame in frames_between(
                log, can_id, event.end_us, event.end_us + RELEASE_AFTER_US
            ):
                if abs(feature_value(frame.data, name) - before) < threshold:
                    release_ms = (frame.time_us - event.end_us) / 1_000
                    break

    return Sample(
        log.role, event.index, before, during, delta,
        onset_ms, release_ms, control,
    )


def event_samples(
    logs: dict[str, LogData],
    events: dict[str, list[Event]],
) -> dict[tuple[int, str], list[Sample]]:
    samples: dict[tuple[int, str], list[Sample]] = defaultdict(list)
    all_ids = sorted({can_id for log in logs.values() for can_id in log.by_id})
    work: list[tuple[LogData, Event, bool]] = []

    for role, log in logs.items():
        work += [(log, event, False) for event in events[role]]
        cursor = log.frames[0].time_us + 2_000_000
        limit = log.frames[-1].time_us - 2_000_000
        control_index = 0
        while cursor <= limit:
            if all(
                cursor < event.start_us - 2_000_000 or cursor > event.end_us + 2_000_000
                for event in events[role]
            ):
                control_index += 1
                work.append((log, Event(role, control_index, cursor, cursor), True))
            cursor += 3_000_000

    for log, event, control in work:
        for can_id in all_ids:
            series = log.by_id.get(can_id, [])
            if not series:
                continue
            length = min(len(frame.data) for frame in series)
            for name in feature_names(length):
                sample = sample_event(log, event, can_id, name, control)
                if sample is not None:
                    samples[(can_id, name)].append(sample)
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
    positive_roles = [role for role in ROLE_ORDER if events[role]]
    negative_roles = [role for role in ROLE_ORDER if not events[role]]

    for (can_id, name), feature_samples in samples.items():
        positive_by_role = {
            role: [
                sample for sample in feature_samples
                if sample.role == role and not sample.control
            ]
            for role in positive_roles
        }
        control_by_role = {
            role: [
                sample for sample in feature_samples
                if sample.role == role and sample.control
            ]
            for role in ROLE_ORDER
        }
        positive = [sample for role in positive_roles for sample in positive_by_role[role]]
        if not positive:
            continue
        values = [value for sample in feature_samples for value in (sample.before, sample.during)]
        span = max(values) - min(values)
        threshold = 0.5 if ".b" in name else max(1.0, span * 0.02)
        capture_deltas = {
            role: statistics.median(sample.delta for sample in positive_by_role[role])
            for role in positive_roles if positive_by_role[role]
        }
        rising = sum(delta >= threshold for delta in capture_deltas.values())
        falling = sum(delta <= -threshold for delta in capture_deltas.values())
        direction = 1 if rising >= falling else -1
        matching_roles = [
            role for role, delta in capture_deltas.items()
            if abs(delta) >= threshold and (1 if delta > 0 else -1) == direction
        ]
        if not matching_roles:
            continue

        matching = [
            sample for role in matching_roles for sample in positive_by_role[role]
            if abs(sample.delta) >= threshold
            and (1 if sample.delta > 0 else -1) == direction
        ]
        consistency = len(matching_roles) / max(1, len(positive_roles))
        capture_details: dict[str, dict[str, object]] = {}
        alignment_scores = []
        for role in positive_roles:
            role_matching = [
                sample for sample in positive_by_role[role]
                if abs(sample.delta) >= threshold
                and (1 if sample.delta > 0 else -1) == direction
            ]
            onsets = [sample.onset_ms for sample in role_matching if sample.onset_ms is not None]
            releases = [sample.release_ms for sample in role_matching if sample.release_ms is not None]
            onset = statistics.median(onsets) if onsets else None
            if onset is not None and onset <= 0:
                alignment_scores.append(max(0.0, 1 - abs(onset) / 500))
            else:
                alignment_scores.append(0.0)
            capture_details[role] = {
                "intervals": len(events[role]),
                "matched": len(role_matching),
                "onset_ms": onset,
                "release_ms": statistics.median(releases) if releases else None,
            }
        alignment = statistics.mean(alignment_scores) if alignment_scores else 0.0

        control_rates = {
            role: fraction_in_direction(control_by_role[role], direction, threshold)
            for role in ROLE_ORDER
        }
        false_positive_rate = statistics.mean(control_rates.values())
        specificity = 1 - false_positive_rate
        clean_negative_count = sum(control_rates[role] <= 0.05 for role in negative_roles)
        magnitude = min(
            1.0,
            statistics.median(abs(capture_deltas[role]) for role in matching_roles)
            / max(threshold, span * 0.25, 1.0),
        ) if matching_roles else 0.0
        score = (
            0.35 * consistency
            + 0.25 * alignment
            + 0.25 * specificity
            + 0.15 * magnitude
        )
        if can_id == 0x1A4:
            score *= 0.45
        elif can_id in KNOWN_IDS:
            score *= 0.70
        onsets = [
            capture_details[role]["onset_ms"] for role in matching_roles
            if capture_details[role]["onset_ms"] is not None
        ]
        releases = [
            capture_details[role]["release_ms"] for role in matching_roles
            if capture_details[role]["release_ms"] is not None
        ]
        cmb_vote = 1.0 if "cmbs" in matching_roles else 0.0
        other_votes = [
            1.0 if role in matching_roles else 0.0
            for role in positive_roles if role != "cmbs"
        ]
        ranked.append({
            "can_id": can_id,
            "feature": name,
            "score": score,
            "direction": direction,
            "consistency": consistency,
            "positive_capture_count": len(matching_roles),
            "positive_capture_total": len(positive_roles),
            "clean_negative_count": clean_negative_count,
            "negative_capture_total": len(negative_roles),
            "control": false_positive_rate,
            "specificity": specificity,
            "alignment": alignment,
            "onset_ms": statistics.median(onsets) if onsets else None,
            "release_ms": statistics.median(releases) if releases else None,
            "cmbs_only": cmb_vote * (1 - statistics.mean(other_votes)) * specificity
            if other_votes else 0.0,
            "samples": matching,
            "capture_details": capture_details,
            "control_by_role": control_rates,
        })

    ranked.sort(key=lambda row: (-float(row["score"]), int(row["can_id"]), str(row["feature"])))
    best_by_id: dict[int, dict[str, object]] = {}
    for row in ranked:
        can_id = int(row["can_id"])
        if can_id == 0x1C0 and row["feature"] == "D3.b0":
            best_by_id[can_id] = row
        else:
            best_by_id.setdefault(can_id, row)
    return list(best_by_id.values())


def confidence(row: dict[str, object]) -> str:
    score = float(row["score"])
    onset = row["onset_ms"]
    if (
        score >= 0.75
        and int(row["positive_capture_count"]) >= 3
        and int(row["clean_negative_count"]) >= 3
        and onset is not None and abs(float(onset)) <= 100
    ):
        return "high"
    if (
        score >= 0.55
        and int(row["positive_capture_count"]) >= 2
        and int(row["clean_negative_count"]) >= 3
        and onset is not None and abs(float(onset)) <= 250
    ):
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


def signal_rate(log: LogData, can_id: int, start: int, length: int) -> float:
    frames = log.by_id.get(can_id, [])
    return (
        sum(motorola(frame.data, start, length) for frame in frames) / len(frames)
        if frames else 0.0
    )


def capture_state(log: LogData) -> dict[str, object]:
    speeds = [
        motorola(frame.data, 7, 16) * 0.01
        for frame in log.by_id.get(0x158, [])
    ]
    max_speed = max(speeds, default=0.0)
    moving = sum(speed > 1 for speed in speeds) / len(speeds) if speeds else 0.0
    acc_status = signal_rate(log, 0x17C, 38, 1)
    acc_on = signal_rate(log, 0x30C, 52, 1)
    set_speeds = []
    for frame in log.by_id.get(0x30C, []):
        set_speed = motorola(frame.data, 31, 8)
        if motorola(frame.data, 52, 1) and 0 < set_speed < 0xFF:
            set_speeds.append(set_speed)
    lead_shown = sum(
        motorola(frame.data, 45, 2) > 0
        for frame in log.by_id.get(0x30C, [])
    ) / max(1, len(log.by_id.get(0x30C, [])))
    lkas_ready = signal_rate(log, 0x33D, 0, 1)
    dashed = signal_rate(log, 0x33D, 14, 1)
    solid = signal_rate(log, 0x33D, 10, 1)
    steering_required = signal_rate(log, 0x33D, 8, 1)

    if max_speed < 1:
        mode = "stationary; ACC and LKAS off"
    elif acc_on >= 0.75 and solid >= 0.75:
        mode = "ACC and LKAS active"
    elif acc_on >= 0.75:
        mode = "ACC active; LKAS not actively steering"
    elif acc_on <= 0.05 and moving >= 0.5:
        mode = "regular driving; ACC and LKAS off"
    else:
        mode = "mixed capture; ACC active part-time"
    return {
        "mode": mode,
        "max_speed": max_speed,
        "acc_status": acc_status,
        "acc_on": acc_on,
        "set_speed": (
            f"{min(set_speeds)}–{max(set_speeds)} km/h" if set_speeds else "off"
        ),
        "lead_shown": lead_shown,
        "lkas_ready": lkas_ready,
        "dashed": dashed,
        "solid": solid,
        "steering_required": steering_required,
        "lkas_dlcs": sorted({len(frame.data) for frame in log.by_id.get(0x33D, [])}),
    }


def feature_active_fraction(log: LogData, can_id: int, name: str) -> float:
    frames = log.by_id.get(can_id, [])
    return sum(bool(feature_value(frame.data, name)) for frame in frames) / len(frames) if frames else 0.0


def feature_runs(log: LogData, can_id: int, name: str) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    last: int | None = None
    for frame in log.by_id.get(can_id, []):
        active = bool(feature_value(frame.data, name))
        if active and start is None:
            start = frame.time_us
        if active:
            last = frame.time_us
        elif start is not None and last is not None:
            runs.append((start, last))
            start = last = None
    if start is not None and last is not None:
        runs.append((start, last))
    return runs


def format_ms(value: object) -> str:
    return f"{float(value):+.0f} ms" if value is not None else "—"


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
        "## Input data and verified capture modes",
        "",
        "| Intended role | File | Verified dominant mode | Frames | Duration | ACC status | ACC HUD | Set speed | Lead shown | LKAS ready | Dashed | Solid | Steering required | 0x33D DLC |",
        "|---|---|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    states = {role: capture_state(log) for role, log in logs.items()}
    for role in ROLE_ORDER:
        log = logs[role]
        state = states[role]
        lines.append(
            f"| {ROLE_NAMES[role]} | `{log.path.name}` | {state['mode']} | "
            f"{len(log.frames)} | {log.duration_us / 1_000_000:.2f} s | "
            f"{float(state['acc_status']):.1%} | {float(state['acc_on']):.1%} | "
            f"{state['set_speed']} | {float(state['lead_shown']):.1%} | "
            f"{float(state['lkas_ready']):.1%} | {float(state['dashed']):.1%} | "
            f"{float(state['solid']):.1%} | {float(state['steering_required']):.1%} | "
            f"{state['lkas_dlcs']} |"
        )

    all_ids = sorted({can_id for log in logs.values() for can_id in log.by_id})
    lines += [
        "",
        f"- `0x1E7`: {'present' if 0x1E7 in all_ids else 'absent'}.",
        f"- Standard Nidec `0x1FA`: {'present' if 0x1FA in all_ids else 'absent from every log'}.",
        "",
        "### Capture integrity",
        "",
        "| File | CAN IDs | Timestamp wraps | Zero timestamps | Time anomalies | SHA-256 |",
        "|---|---:|---:|---:|---:|---|",
    ]
    for role in ROLE_ORDER:
        log = logs[role]
        lines.append(
            f"| `{log.path.name}` | {len(log.by_id)} | {log.wraps} | "
            f"{log.zero_timestamps} | {log.anomalies} | `{log.sha256[:12]}…` |"
        )
    lines += [
        "",
        "## Frame frequencies",
        "",
        "| ID | " + " | ".join(logs[role].path.stem for role in ROLE_ORDER) + " |",
        "|---:|" + "|".join("---:" for _ in ROLE_ORDER) + "|",
    ]
    for can_id in all_ids:
        rates = []
        for role in ROLE_ORDER:
            log = logs[role]
            rates.append(len(log.by_id.get(can_id, [])) / max(log.duration_us / 1_000_000, 0.001))
        lines.append(f"| `0x{can_id:03X}` | " + " | ".join(f"{rate:.1f} Hz" for rate in rates) + " |")

    lines += [
        "",
        "## Observed `0x1A4 COMPUTER_BRAKING` intervals",
        "",
        "These are controller-state intervals, not counts of distinct physical braking maneuvers. "
        "One real-world maneuver may contain multiple intervals.",
        "",
        "| Log | # | Start | End | Duration | Speed before → after | 0x1E7 raw before → max | 0x17C / 0x30C context |",
        "|---|---:|---:|---:|---:|---|---|---|",
    ]
    for role in ROLE_ORDER:
        log = logs[role]
        origin = log.frames[0].time_us
        if not events[role]:
            lines.append(f"| `{log.path.name}` | — | — | — | no intervals | — | — | — |")
            continue
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
        "## Capture-level candidate ranking",
        "",
        "Each CSV contributes at most one consistency vote, regardless of how many marker "
        "intervals it contains. The score weights positive-capture consistency (35%), onset "
        "alignment (25%), control specificity (25%), and magnitude (15%).",
        "",
        "| # | ID / field | Known role | Score | Confidence | Positive captures | Clean negatives | Onset | Release | Control false positives | Payload before → during → after |",
        "|---:|---|---|---:|---|---:|---:|---:|---:|---:|---|",
    ]
    for index, row in enumerate(ranked[:20], 1):
        can_id = int(row["can_id"])
        lines.append(
            f"| {index} | `0x{can_id:03X}` `{row['feature']}` | "
            f"{KNOWN_IDS.get(can_id, 'unknown')} | {float(row['score']):.3f} | "
            f"{confidence(row)} | {row['positive_capture_count']}/{row['positive_capture_total']} | "
            f"{row['clean_negative_count']}/{row['negative_capture_total']} | "
            f"{format_ms(row['onset_ms'])} | {format_ms(row['release_ms'])} | "
            f"{float(row['control']):.0%} | "
            f"`{example_payloads(row, logs, events)}` |"
        )

    focus = next(
        (row for row in ranked if int(row["can_id"]) == 0x1C0 and row["feature"] == "D3.b0"),
        next((row for row in ranked if int(row["can_id"]) not in KNOWN_IDS), None),
    )
    if focus:
        lines += [
            "",
            f"## Focused evidence: `0x{int(focus['can_id']):03X} {focus['feature']}`",
            "",
            "| Positive capture | Marker intervals | Matching intervals | Median onset | Median release | Candidate active runs |",
            "|---|---:|---:|---:|---:|---|",
        ]
        details = focus["capture_details"]
        for role in ROLE_ORDER:
            if not events[role]:
                continue
            log = logs[role]
            item = details[role]
            origin = log.frames[0].time_us
            runs = feature_runs(log, int(focus["can_id"]), str(focus["feature"]))
            run_text = ", ".join(
                f"{(start - origin) / 1_000_000:.3f}–{(end - origin) / 1_000_000:.3f} s"
                for start, end in runs
            ) or "none"
            lines.append(
                f"| `{log.path.name}` | {item['intervals']} | {item['matched']} | "
                f"{format_ms(item['onset_ms'])} | {format_ms(item['release_ms'])} | {run_text} |"
            )
        lines += [
            "",
            "| Negative capture | Candidate active fraction | COMPUTER_BRAKING active fraction |",
            "|---|---:|---:|",
        ]
        for role in ROLE_ORDER:
            if events[role]:
                continue
            log = logs[role]
            lines.append(
                f"| `{log.path.name}` | "
                f"{feature_active_fraction(log, int(focus['can_id']), str(focus['feature'])):.2%} | "
                f"{signal_rate(log, 0x1A4, 23, 1):.2%} |"
            )

    cmbs_rows = sorted(ranked, key=lambda row: -float(row["cmbs_only"]))
    lines += [
        "",
        "## CMBS-specific changes",
        "",
        "These fields may represent AEB/CMBS status rather than a pressure command.",
        "",
        "| ID / field | CMBS-only | Score | Positive captures | Control false positives |",
        "|---|---:|---:|---:|---:|",
    ]
    for row in cmbs_rows[:10]:
        lines.append(
            f"| `0x{int(row['can_id']):03X}` `{row['feature']}` | "
            f"{float(row['cmbs_only']):.3f} | {float(row['score']):.3f} | "
            f"{row['positive_capture_count']}/{row['positive_capture_total']} | "
            f"{float(row['control']):.0%} |"
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
        "Physical maneuver count is intentionally left unknown. Confirmation still requires "
        "separate annotated captures with repeatable onset timing; do not transmit candidate "
        "frames on public roads.",
        "",
        "## Method and limitations",
        "",
        "- Off-marker control windows are sampled from all eight captures, including captures "
        "that also contain marker intervals.",
        "- Counter and checksum bits in the lower six bits of the last byte are ignored for ranking.",
        "- `0x1A4`, `0x1E7`, `0x158`, `0x1D0`, `0x17C`, and `0x30C` are tagged as known status/response frames.",
        "- CU2 emits `0x33D` with DLC 4. Signal positions in the first four bytes match upstream "
        "[`LKAS_HUD`](https://github.com/commaai/opendbc/blob/master/opendbc/dbc/generator/honda/_lkas_hud_5byte.dbc), "
        "which defines a five-byte message.",
        "- Zero timestamps are interpolated and the microsecond field is unwrapped once per second.",
        "- The analysis does not create TX frames or modify openpilot or panda safety code.",
        "",
    ]
    return "\n".join(lines)


def synthetic_log(
    role: str,
    marker_ranges: tuple[tuple[int, int], ...] = (),
    mode: str = "acc",
) -> LogData:
    frames: list[Frame] = []
    for tick in range(400):
        time_us = tick * 20_000
        active_marker = any(start <= time_us <= end for start, end in marker_ranges)
        active_command = bool(marker_ranges) and (
            marker_ranges[0][0] - 40_000 <= time_us < marker_ranges[-1][1] + 400_000
        )
        acc_on = mode in {"acc", "lkas"}
        speed_raw = 0 if mode == "idle" else 5_000
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
        frames.append(Frame(time_us, 0x158, bytes([
            speed_raw >> 8, speed_raw & 0xFF, 0, 0, 0, 0, 0,
            (counter << 4) | checksum,
        ])))
        frames.append(Frame(time_us, 0x17C, bytes([
            0, 0, 0, 0, 0x40 if acc_on else 0, 0, 0,
            (counter << 4) | checksum,
        ])))
        frames.append(Frame(time_us, 0x30C, bytes([
            0, 0, 0, 60 if acc_on else 0, 0, 0x20 if acc_on else 0,
            0x10 if acc_on else 0, (counter << 4) | checksum,
        ])))
        lkas_byte_2 = 0x04 if mode == "lkas" else (0x40 if mode == "acc" else 0)
        frames.append(Frame(time_us, 0x33D, bytes([
            0x01 if mode in {"acc", "lkas"} else 0,
            lkas_byte_2, 0, (counter << 4) | checksum,
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
        "baseline": synthetic_log(
            "baseline", ((3_000_000, 3_300_000), (3_600_000, 4_000_000))
        ),
        "set_speed": synthetic_log("set_speed", ((3_000_000, 4_000_000),)),
        "acc_brake": synthetic_log("acc_brake", ((3_000_000, 4_000_000),)),
        "cmbs": synthetic_log("cmbs", ((3_000_000, 4_000_000),)),
        "idle": synthetic_log("idle", mode="idle"),
        "regular": synthetic_log("regular", mode="regular"),
        "acc": synthetic_log("acc", mode="acc"),
        "lkas": synthetic_log("lkas", mode="lkas"),
    }
    events = {role: braking_events(log) for role, log in logs.items()}
    assert len(events["baseline"]) == 2
    ranked = rank_candidates(event_samples(logs, events), events)
    assert ranked and ranked[0]["can_id"] == 0x123, ranked[:3]
    candidate = next(row for row in ranked if row["can_id"] == 0x123)
    assert candidate["positive_capture_count"] == 4
    assert candidate["clean_negative_count"] == 4
    assert candidate["onset_ms"] == -40
    assert candidate["release_ms"] == 400
    assert capture_state(logs["idle"])["mode"] == "stationary; ACC and LKAS off"
    assert capture_state(logs["regular"])["mode"] == "regular driving; ACC and LKAS off"
    assert capture_state(logs["acc"])["mode"] == "ACC active; LKAS not actively steering"
    assert capture_state(logs["lkas"])["mode"] == "ACC and LKAS active"
    assert capture_state(logs["acc"])["lkas_dlcs"] == [4]
    assert capture_state(logs["acc"])["dashed"] == 1
    assert capture_state(logs["acc"])["solid"] == 0
    assert capture_state(logs["lkas"])["solid"] == 1

    with tempfile.TemporaryDirectory() as directory:
        invalid = Path(directory) / "invalid.csv"
        invalid.write_text("bad,header\n1,2\n", encoding="utf-8")
        try:
            parse_log(invalid, "invalid")
        except ValueError:
            pass
        else:
            raise AssertionError("invalid header was accepted")
        malformed = Path(directory) / "malformed.csv"
        malformed.write_text(
            "Time Stamp,ID,Extended,Dir,Bus,LEN,D1,D2,D3,D4,D5,D6,D7,D8\n"
            "1,123,false,Rx,0,1,GG,00,00,00,00,00,00,00\n",
            encoding="utf-8",
        )
        try:
            parse_log(malformed, "malformed")
        except ValueError:
            pass
        else:
            raise AssertionError("malformed payload was accepted")
    print("self-test: OK")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=Path("bra.csv"))
    parser.add_argument("--set-speed", type=Path, default=Path("bra2.csv"))
    parser.add_argument("--acc-brake", type=Path, default=Path("brk_full.csv"))
    parser.add_argument("--cmbs", type=Path, default=Path("cmb.csv"))
    parser.add_argument("--idle", type=Path, default=Path("idle.csv"))
    parser.add_argument("--regular", type=Path, default=Path("reg.csv"))
    parser.add_argument("--acc", type=Path, default=Path("acc.csv"))
    parser.add_argument("--lkas", type=Path, default=Path("lkas.csv"))
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
        "idle": args.idle,
        "regular": args.regular,
        "acc": args.acc,
        "lkas": args.lkas,
    }
    logs = {}
    for role, path in paths.items():
        print(f"reading {path}...")
        logs[role] = parse_log(path, role)
    events = {role: braking_events(log) for role, log in logs.items()}
    positive_capture_count = sum(bool(items) for items in events.values())
    if not positive_capture_count:
        raise SystemExit("no COMPUTER_BRAKING intervals found in any capture")
    samples = event_samples(logs, events)
    ranked = rank_candidates(samples, events)
    report = render_report(logs, events, ranked)
    args.output.write_text(report, encoding="utf-8", newline="\n")
    print(
        f"wrote {args.output} ({len(ranked)} candidate IDs; "
        f"{sum(len(items) for items in events.values())} marker intervals in "
        f"{positive_capture_count} captures)"
    )


if __name__ == "__main__":
    main()
