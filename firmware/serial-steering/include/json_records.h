#pragma once

#include <cstdint>

#include "capture_types.h"

struct StatsSnapshot {
    std::uint32_t bytes{};
    std::uint32_t valid_4{};
    std::uint32_t valid_5{};
    std::uint32_t checksum_fail{};
    std::uint32_t parity_err{};
    std::uint32_t frame_err{};
    std::uint32_t break_err{};
    std::uint32_t fifo_overflow{};
    std::uint32_t buffer_full{};
    std::uint32_t capture_queue_drop{};
    std::uint32_t capture_bytes_dropped{};
    std::uint32_t output_queue_drop{};
    std::uint32_t captured_output_drop{};
    std::uint32_t captured_output_bytes_dropped{};
    std::uint32_t raw_bytes_discarded{};
};

const char *channel_name(ChannelId channel);
const char *direction_name(DirectionGuess direction);
const char *mode_name(ParserMode mode);
bool format_frame_record(OutputRecord &output, const ParsedRecord &record,
                         std::uint32_t sequence, bool decode_enabled,
                         bool include_detail);
bool format_raw_record(OutputRecord &output, const ParsedRecord &record,
                       std::uint32_t sequence);
bool format_uart_error_record(OutputRecord &output, std::int64_t time_us,
                              ChannelId channel, const char *error,
                              std::uint32_t count, int event_type = -1);
bool format_stats_record(OutputRecord &output, std::int64_t time_us,
                         ChannelId channel, DirectionGuess direction,
                         const StatsSnapshot &stats);
bool format_session_record(OutputRecord &output, const char *git_version,
                           const char *boot_id, int vehicle_baud, int console_baud,
                           int channel_a_gpio, int channel_b_gpio);
bool format_mark_record(OutputRecord &output, std::int64_t time_us,
                        const char *text);
bool format_console_record(OutputRecord &output, std::int64_t time_us,
                           const char *status, const char *message);
