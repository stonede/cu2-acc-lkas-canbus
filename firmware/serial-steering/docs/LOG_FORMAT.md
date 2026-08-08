# Logger JSONL format

The console emits newline-delimited JSON using schema version 1. Each line is a
standalone JSON object; human diagnostics use JSON records too. Hex strings are
uppercase with two characters per byte and no separators.

`t_us` is monotonic device time in microseconds from `esp_timer_get_time()`.
For captured data it is the time firmware serviced the UART RX event, not a
hardware timestamp for the first bit. Bytes from one serviced chunk share that
timestamp. No estimated per-byte timestamp is currently emitted.

## Records

- `session`: firmware/schema identity, build Git hash, random boot ID, UART
  format, GPIO map, and `capture_mode: "rx_only"`.
- `frame`: globally monotonic `seq`, capture time, channel, provisional
  direction, length, authoritative raw `data`, `checksum_ok`, and optional
  provisional decoder fields. `decode_status` is
  `field_decode_provisional` when fields are present and
  `checksum_valid_hypothesis` when detail decoding is disabled or shed under
  output pressure.
- `raw_fragment`: globally monotonic `seq`, raw bytes, and `reason`:
  `raw_mode`, `auto_unclassified`, `resync_discard`, or `mode_change`.
- `uart_error`: channel, cumulative error count, and one of `parity`, `frame`,
  `break`, `fifo_overflow`, `buffer_full`, or `unknown_event`.
- `stats`: cumulative byte/parser/error/loss counters and current direction.
  `capture_queue_drop` counts dropped chunks, `capture_bytes_dropped` counts
  their bytes, and `queue_drop` counts all records dropped from the output
  queue. `captured_output_drop` and `captured_output_bytes_dropped` isolate the
  captured frame/raw records and authoritative bytes lost there.
- `mark`: device timestamp and operator text from `!mark`.
- `console`: structured command acknowledgement or error.

Raw bytes remain authoritative. Names ending in `_candidate`, raw flag
interpretations, directions selected by auto-classification, and all physical
meaning are hypotheses. There are no physical torque units or sign normalization.

Firmware and the host capture tool use compact `frame` records by default to
reduce serial bandwidth. `tools/analyze_log.py` validates the raw frame checksum and
reconstructs the same provisional fields offline. It also checks global `seq`
continuity and derives LKAS-active time intervals from consecutive 4-byte frames
whose `lkas_on_candidate` bit is set. Operator markers are optional and are not
required for this analysis.

Schema changes that remove or reinterpret fields require a new integer
`schema`. Additive fields may be introduced within schema 1; readers should
ignore unknown keys.
