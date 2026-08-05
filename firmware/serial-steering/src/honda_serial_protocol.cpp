#include "honda_serial_protocol.h"

std::uint8_t serial_checksum(const std::uint8_t *data,
                             std::size_t length_without_checksum) {
    std::uint8_t total = 0;
    for (std::size_t i = 0; i < length_without_checksum; ++i) {
        total = static_cast<std::uint8_t>(total + data[i]);
    }
    total = static_cast<std::uint8_t>(256U - total);
    total = static_cast<std::uint8_t>(total % 128U);
    return static_cast<std::uint8_t>(total + 128U);
}

bool is_candidate_start(std::uint8_t value) { return (value >> 4U) < 4; }

bool valid_frame(const std::uint8_t *frame, std::size_t length) {
    return (length == 4 || length == 5) && is_candidate_start(frame[0]) &&
           serial_checksum(frame, length - 1) == frame[length - 1];
}

namespace {

std::int16_t decode_signed_9(std::uint8_t big, std::uint8_t little) {
    const auto raw = static_cast<std::uint16_t>(((big & 0x07U) << 5U) |
                                                (little & 0x1FU));
    return (big & 0x08U) ? static_cast<std::int16_t>(raw) - 256
                         : static_cast<std::int16_t>(raw);
}

}  // namespace

LkasToEpsDecoded decode_lkas_to_eps(const std::uint8_t *frame) {
    LkasToEpsDecoded result{};
    result.counter_raw = frame[0] >> 5U;
    result.big_steer_raw = frame[0] & 0x0FU;
    result.little_steer_raw = frame[1] & 0x1FU;
    result.lkas_on_candidate = ((frame[1] >> 5U) & 0x01U) != 0;
    result.flags_raw = frame[2];
    result.apply_steer_candidate =
        decode_signed_9(result.big_steer_raw, result.little_steer_raw);
    return result;
}

EpsToLkasDecoded decode_eps_to_lkas(const std::uint8_t *frame) {
    EpsToLkasDecoded result{};
    result.big_driver_torque_raw = frame[0] & 0x0FU;
    result.little_driver_torque_raw = frame[1] & 0x1FU;
    result.driver_torque_candidate = decode_signed_9(
        result.big_driver_torque_raw, result.little_driver_torque_raw);
    result.motor_torque_raw_10bit = static_cast<std::uint16_t>(
        (static_cast<std::uint16_t>((frame[2] >> 4U) & 0x03U) << 8U) |
        (static_cast<std::uint16_t>((frame[2] >> 3U) & 0x01U) << 7U) |
        static_cast<std::uint16_t>(frame[3] & 0x7FU));
    result.motor_torque_signed_candidate =
        (result.motor_torque_raw_10bit & 0x0200U)
            ? static_cast<std::int16_t>(result.motor_torque_raw_10bit) - 1024
            : static_cast<std::int16_t>(result.motor_torque_raw_10bit);
    result.flags_b0_raw = frame[0];
    result.flags_b1_raw = frame[1];
    result.flags_b2_raw = frame[2];
    return result;
}
