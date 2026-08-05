#include "json_records.h"

#include <cstdarg>
#include <cstdio>
#include <cstring>

#include "honda_serial_protocol.h"

namespace {

bool finish(OutputRecord &output, int count) {
    if (count < 0 || static_cast<std::size_t>(count) >= output.text.size()) {
        output.length = 0;
        return false;
    }
    output.length = static_cast<std::uint16_t>(count);
    return true;
}

void hex_bytes(const std::uint8_t *data, std::size_t length, char *output) {
    static constexpr char kHex[] = "0123456789ABCDEF";
    for (std::size_t i = 0; i < length; ++i) {
        output[i * 2] = kHex[data[i] >> 4U];
        output[i * 2 + 1] = kHex[data[i] & 0x0FU];
    }
    output[length * 2] = '\0';
}

void json_escape(const char *input, char *output, std::size_t capacity) {
    std::size_t used = 0;
    for (; *input != '\0' && used + 2 < capacity; ++input) {
        const unsigned char value = static_cast<unsigned char>(*input);
        if (*input == '"' || *input == '\\') {
            output[used++] = '\\';
            output[used++] = *input;
        } else if (value >= 0x20) {
            output[used++] = *input;
        }
    }
    output[used] = '\0';
}

}  // namespace

const char *channel_name(ChannelId channel) {
    return channel == ChannelId::kA ? "A" : "B";
}

const char *direction_name(DirectionGuess direction) {
    switch (direction) {
        case DirectionGuess::kLkasToEps:
            return "LKAS_TO_EPS";
        case DirectionGuess::kEpsToLkas:
            return "EPS_TO_LKAS";
        default:
            return "UNKNOWN";
    }
}

const char *mode_name(ParserMode mode) {
    switch (mode) {
        case ParserMode::kRaw:
            return "raw";
        case ParserMode::kFour:
            return "4";
        case ParserMode::kFive:
            return "5";
        default:
            return "auto";
    }
}

bool format_frame_record(OutputRecord &output, const ParsedRecord &record,
                         std::uint32_t sequence, bool decode_enabled,
                         bool include_detail) {
    char data_hex[257]{};
    hex_bytes(record.data.data(), record.length, data_hex);
    if (!decode_enabled || !include_detail) {
        return finish(output, std::snprintf(
            output.text.data(), output.text.size(),
            "{\"type\":\"frame\",\"seq\":%lu,\"t_us\":%lld,\"channel\":\"%s\","
            "\"direction\":\"%s\",\"len\":%u,\"data\":\"%s\",\"checksum_ok\":true,"
            "\"decode_status\":\"checksum_valid_hypothesis\"}",
            static_cast<unsigned long>(sequence),
            static_cast<long long>(record.capture_time_us), channel_name(record.channel),
            direction_name(record.direction), record.length, data_hex));
    }
    if (record.length == 4) {
        const auto decoded = decode_lkas_to_eps(record.data.data());
        return finish(output, std::snprintf(
            output.text.data(), output.text.size(),
            "{\"type\":\"frame\",\"seq\":%lu,\"t_us\":%lld,\"channel\":\"%s\","
            "\"direction\":\"%s\",\"len\":4,\"data\":\"%s\",\"checksum_ok\":true,"
            "\"counter_raw\":%u,\"big_steer_raw\":%u,\"little_steer_raw\":%u,"
            "\"flags_raw\":%u,\"apply_steer_candidate\":%d,"
            "\"lkas_on_candidate\":%s,\"decode_status\":\"field_decode_provisional\"}",
            static_cast<unsigned long>(sequence),
            static_cast<long long>(record.capture_time_us), channel_name(record.channel),
            direction_name(record.direction), data_hex, decoded.counter_raw,
            decoded.big_steer_raw, decoded.little_steer_raw, decoded.flags_raw,
            decoded.apply_steer_candidate,
            decoded.lkas_on_candidate ? "true" : "false"));
    }
    const auto decoded = decode_eps_to_lkas(record.data.data());
    return finish(output, std::snprintf(
        output.text.data(), output.text.size(),
        "{\"type\":\"frame\",\"seq\":%lu,\"t_us\":%lld,\"channel\":\"%s\","
        "\"direction\":\"%s\",\"len\":5,\"data\":\"%s\",\"checksum_ok\":true,"
        "\"big_driver_torque_raw\":%u,\"little_driver_torque_raw\":%u,"
        "\"driver_torque_candidate\":%d,\"motor_torque_raw_10bit\":%u,"
        "\"motor_torque_signed_candidate\":%d,\"flags_b0_raw\":%u,"
        "\"flags_b1_raw\":%u,\"flags_b2_raw\":%u,"
        "\"decode_status\":\"field_decode_provisional\"}",
        static_cast<unsigned long>(sequence),
        static_cast<long long>(record.capture_time_us), channel_name(record.channel),
        direction_name(record.direction), data_hex, decoded.big_driver_torque_raw,
        decoded.little_driver_torque_raw, decoded.driver_torque_candidate,
        decoded.motor_torque_raw_10bit, decoded.motor_torque_signed_candidate,
        decoded.flags_b0_raw, decoded.flags_b1_raw, decoded.flags_b2_raw));
}

bool format_raw_record(OutputRecord &output, const ParsedRecord &record,
                       std::uint32_t sequence) {
    char data_hex[257]{};
    hex_bytes(record.data.data(), record.length, data_hex);
    return finish(output, std::snprintf(
        output.text.data(), output.text.size(),
        "{\"type\":\"raw_fragment\",\"seq\":%lu,\"t_us\":%lld,\"channel\":\"%s\","
        "\"data\":\"%s\",\"reason\":\"%s\"}",
        static_cast<unsigned long>(sequence),
        static_cast<long long>(record.capture_time_us), channel_name(record.channel),
        data_hex, record.reason));
}

bool format_uart_error_record(OutputRecord &output, std::int64_t time_us,
                              ChannelId channel, const char *error,
                              std::uint32_t count, int event_type) {
    const char *suffix = event_type < 0 ? "" : ",\"event_type\":";
    if (event_type < 0) {
        return finish(output, std::snprintf(
            output.text.data(), output.text.size(),
            "{\"type\":\"uart_error\",\"t_us\":%lld,\"channel\":\"%s\","
            "\"error\":\"%s\",\"count\":%lu}",
            static_cast<long long>(time_us), channel_name(channel), error,
            static_cast<unsigned long>(count)));
    }
    (void)suffix;
    return finish(output, std::snprintf(
        output.text.data(), output.text.size(),
        "{\"type\":\"uart_error\",\"t_us\":%lld,\"channel\":\"%s\","
        "\"error\":\"%s\",\"count\":%lu,\"event_type\":%d}",
        static_cast<long long>(time_us), channel_name(channel), error,
        static_cast<unsigned long>(count), event_type));
}

bool format_stats_record(OutputRecord &output, std::int64_t time_us,
                         ChannelId channel, DirectionGuess direction,
                         const StatsSnapshot &stats) {
    return finish(output, std::snprintf(
        output.text.data(), output.text.size(),
        "{\"type\":\"stats\",\"t_us\":%lld,\"channel\":\"%s\",\"bytes\":%lu,"
        "\"valid_4\":%lu,\"valid_5\":%lu,\"checksum_fail\":%lu,"
        "\"parity_err\":%lu,\"frame_err\":%lu,\"fifo_overflow\":%lu,"
        "\"buffer_full\":%lu,\"capture_queue_drop\":%lu,"
        "\"capture_bytes_dropped\":%lu,\"queue_drop\":%lu,"
        "\"captured_output_drop\":%lu,\"captured_output_bytes_dropped\":%lu,"
        "\"raw_bytes_discarded\":%lu,\"direction\":\"%s\"}",
        static_cast<long long>(time_us), channel_name(channel),
        static_cast<unsigned long>(stats.bytes),
        static_cast<unsigned long>(stats.valid_4),
        static_cast<unsigned long>(stats.valid_5),
        static_cast<unsigned long>(stats.checksum_fail),
        static_cast<unsigned long>(stats.parity_err),
        static_cast<unsigned long>(stats.frame_err),
        static_cast<unsigned long>(stats.fifo_overflow),
        static_cast<unsigned long>(stats.buffer_full),
        static_cast<unsigned long>(stats.capture_queue_drop),
        static_cast<unsigned long>(stats.capture_bytes_dropped),
        static_cast<unsigned long>(stats.output_queue_drop),
        static_cast<unsigned long>(stats.captured_output_drop),
        static_cast<unsigned long>(stats.captured_output_bytes_dropped),
        static_cast<unsigned long>(stats.raw_bytes_discarded),
        direction_name(direction)));
}

bool format_session_record(OutputRecord &output, const char *git_version,
                           const char *boot_id, int vehicle_baud,
                           int channel_a_gpio, int channel_b_gpio) {
    return finish(output, std::snprintf(
        output.text.data(), output.text.size(),
        "{\"type\":\"session\",\"schema\":1,\"firmware\":\"0.1.0\",\"git\":\"%s\","
        "\"boot_id\":\"%s\",\"vehicle_baud\":%d,\"format\":\"8E1\","
        "\"channel_a_gpio\":%d,\"channel_b_gpio\":%d,\"capture_mode\":\"rx_only\"}",
        git_version, boot_id, vehicle_baud, channel_a_gpio, channel_b_gpio));
}

bool format_mark_record(OutputRecord &output, std::int64_t time_us,
                        const char *text) {
    char escaped[512]{};
    json_escape(text, escaped, sizeof(escaped));
    return finish(output, std::snprintf(
        output.text.data(), output.text.size(),
        "{\"type\":\"mark\",\"t_us\":%lld,\"text\":\"%s\"}",
        static_cast<long long>(time_us), escaped));
}

bool format_console_record(OutputRecord &output, std::int64_t time_us,
                           const char *status, const char *message) {
    char escaped[512]{};
    json_escape(message, escaped, sizeof(escaped));
    return finish(output, std::snprintf(
        output.text.data(), output.text.size(),
        "{\"type\":\"console\",\"t_us\":%lld,\"status\":\"%s\",\"message\":\"%s\"}",
        static_cast<long long>(time_us), status, escaped));
}
