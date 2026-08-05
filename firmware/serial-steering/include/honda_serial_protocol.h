#pragma once

#include <cstddef>
#include <cstdint>

struct LkasToEpsDecoded {
    std::uint8_t counter_raw{};
    std::uint8_t big_steer_raw{};
    std::uint8_t little_steer_raw{};
    bool lkas_on_candidate{};
    std::uint8_t flags_raw{};
    std::int16_t apply_steer_candidate{};
};

struct EpsToLkasDecoded {
    std::uint8_t big_driver_torque_raw{};
    std::uint8_t little_driver_torque_raw{};
    std::int16_t driver_torque_candidate{};
    std::uint16_t motor_torque_raw_10bit{};
    std::int16_t motor_torque_signed_candidate{};
    std::uint8_t flags_b0_raw{};
    std::uint8_t flags_b1_raw{};
    std::uint8_t flags_b2_raw{};
};

std::uint8_t serial_checksum(const std::uint8_t *data,
                             std::size_t length_without_checksum);
bool is_candidate_start(std::uint8_t value);
bool valid_frame(const std::uint8_t *frame, std::size_t length);
LkasToEpsDecoded decode_lkas_to_eps(const std::uint8_t *frame);
EpsToLkasDecoded decode_eps_to_lkas(const std::uint8_t *frame);
