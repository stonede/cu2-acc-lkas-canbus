#include <unity.h>

#include <algorithm>
#include <array>
#include <cstdint>
#include <cstring>
#include <string>
#include <vector>

#include "frame_parser.h"
#include "honda_serial_protocol.h"
#include "json_records.h"

void setUp() {}
void tearDown() {}

namespace {

std::vector<ParsedRecord> g_records;

void collect(const ParsedRecord &record, void *) { g_records.push_back(record); }

std::vector<std::uint8_t> frame(std::initializer_list<std::uint8_t> payload) {
    std::vector<std::uint8_t> result(payload);
    result.push_back(serial_checksum(result.data(), result.size()));
    return result;
}

std::size_t frame_count() {
    std::size_t count = 0;
    for (const auto &record : g_records) {
        if (record.type == ParsedRecordType::kFrame) ++count;
    }
    return count;
}

void feed_forced(FrameParser &parser, ParserMode mode,
                 const std::vector<std::uint8_t> &bytes) {
    g_records.clear();
    parser.set_mode(mode, collect, nullptr);
    parser.feed(bytes.data(), bytes.size(), 1234, collect, nullptr);
}

std::array<std::uint8_t, 4> command_for(std::int16_t value) {
    const std::uint16_t raw = value < 0 ? static_cast<std::uint16_t>(value + 256)
                                        : static_cast<std::uint16_t>(value);
    std::array<std::uint8_t, 4> result{};
    result[0] = static_cast<std::uint8_t>(((raw >> 5U) & 0x07U) |
                                          (value < 0 ? 0x08U : 0U));
    result[1] = static_cast<std::uint8_t>(raw & 0x1FU);
    result[3] = serial_checksum(result.data(), 3);
    return result;
}

std::array<std::uint8_t, 5> feedback_for_motor(std::int16_t value) {
    const std::uint16_t raw = value < 0 ? static_cast<std::uint16_t>(value + 1024)
                                        : static_cast<std::uint16_t>(value);
    std::array<std::uint8_t, 5> result{};
    result[2] = static_cast<std::uint8_t>(((raw >> 8U) & 0x03U) << 4U);
    result[2] |= static_cast<std::uint8_t>(((raw >> 7U) & 0x01U) << 3U);
    result[3] = static_cast<std::uint8_t>(raw & 0x7FU);
    result[4] = serial_checksum(result.data(), 4);
    return result;
}

void test_checksum_and_frame_validation() {
    const std::uint8_t command_payload[]{0x20, 0xA0, 0x80};
    const std::uint8_t feedback_payload[]{0x00, 0x00, 0x00, 0x00};
    TEST_ASSERT_EQUAL_HEX8(0xC0, serial_checksum(command_payload, 3));
    TEST_ASSERT_EQUAL_HEX8(0x80, serial_checksum(feedback_payload, 4));
    const auto valid4 = frame({0x20, 0xA0, 0x80});
    const auto valid5 = frame({0x20, 0x40, 0x40, 0x40});
    TEST_ASSERT_TRUE(valid_frame(valid4.data(), valid4.size()));
    TEST_ASSERT_TRUE(valid_frame(valid5.data(), valid5.size()));
    auto corrupt = valid4;
    corrupt[1] ^= 1U;
    TEST_ASSERT_FALSE(valid_frame(corrupt.data(), corrupt.size()));
}

void test_parser_recovers_after_insert_remove_and_noise() {
    const auto valid = frame({0x20, 0xA0, 0x80});
    std::vector<std::uint8_t> stream{0xFF, 0x7A};
    stream.insert(stream.end(), valid.begin(), valid.end());
    stream.push_back(0x11);
    stream.insert(stream.end(), valid.begin(), valid.end() - 1);
    stream.insert(stream.end(), valid.begin(), valid.end());
    FrameParser parser(ChannelId::kA);
    feed_forced(parser, ParserMode::kFour, stream);
    TEST_ASSERT_EQUAL_UINT32(2, frame_count());
    TEST_ASSERT_GREATER_THAN_UINT32(0, parser.counters().discarded_bytes);
    TEST_ASSERT_GREATER_THAN_UINT32(0, parser.counters().checksum_fail);
}

void test_two_parser_instances_are_independent() {
    const auto valid4 = frame({0x20, 0xA0, 0x80});
    const auto valid5 = frame({0x00, 0x00, 0x00, 0x00});
    FrameParser a(ChannelId::kA);
    FrameParser b(ChannelId::kB);
    a.set_mode(ParserMode::kFour, collect, nullptr);
    b.set_mode(ParserMode::kFive, collect, nullptr);
    g_records.clear();
    a.feed(valid4.data(), valid4.size(), 1, collect, nullptr);
    b.feed(valid5.data(), valid5.size(), 2, collect, nullptr);
    TEST_ASSERT_EQUAL_UINT32(2, frame_count());
    TEST_ASSERT_EQUAL(ChannelId::kA, g_records[0].channel);
    TEST_ASSERT_EQUAL(ChannelId::kB, g_records[1].channel);
}

void test_signed_9_bit_decode_boundaries() {
    for (const std::int16_t expected : {-256, -1, 0, 1, 255}) {
        const auto bytes = command_for(expected);
        TEST_ASSERT_EQUAL_INT16(expected,
                                decode_lkas_to_eps(bytes.data()).apply_steer_candidate);
    }
}

void test_signed_10_bit_motor_decode_boundaries() {
    for (const std::int16_t expected : {-512, -1, 0, 1, 511}) {
        const auto bytes = feedback_for_motor(expected);
        const auto decoded = decode_eps_to_lkas(bytes.data());
        TEST_ASSERT_EQUAL_INT16(expected, decoded.motor_torque_signed_candidate);
    }
}

void test_auto_classifies_synthetic_streams() {
    const auto valid4 = frame({0x20, 0xA0, 0x80});
    const auto valid5 = frame({0x20, 0x40, 0x40, 0x40});
    std::vector<std::uint8_t> stream4;
    std::vector<std::uint8_t> stream5;
    for (int i = 0; i < 25; ++i) {
        stream4.insert(stream4.end(), valid4.begin(), valid4.end());
        stream5.insert(stream5.end(), valid5.begin(), valid5.end());
    }
    FrameParser a(ChannelId::kA, 100, 20, 90, 3);
    FrameParser b(ChannelId::kB, 100, 20, 90, 3);
    g_records.clear();
    a.feed(stream4.data(), stream4.size(), 0, collect, nullptr);
    b.feed(stream5.data(), stream5.size(), 0, collect, nullptr);
    a.feed(valid4.data(), valid4.size(), 101, collect, nullptr);
    b.feed(valid5.data(), valid5.size(), 101, collect, nullptr);
    TEST_ASSERT_EQUAL(ParserMode::kFour, a.mode());
    TEST_ASSERT_EQUAL(ParserMode::kFive, b.mode());
    TEST_ASSERT_EQUAL(DirectionGuess::kLkasToEps, a.direction());
    TEST_ASSERT_EQUAL(DirectionGuess::kEpsToLkas, b.direction());
}

void test_output_serialization_is_standalone_json() {
    const auto bytes = command_for(0);
    ParsedRecord parsed{};
    parsed.type = ParsedRecordType::kFrame;
    parsed.capture_time_us = 42;
    parsed.channel = ChannelId::kA;
    parsed.direction = DirectionGuess::kLkasToEps;
    parsed.length = 4;
    std::copy(bytes.begin(), bytes.end(), parsed.data.begin());
    OutputRecord output{};
    TEST_ASSERT_TRUE(format_frame_record(output, parsed, 7, true, true));
    const std::string json(output.text.data(), output.length);
    TEST_ASSERT_EQUAL_CHAR('{', json.front());
    TEST_ASSERT_EQUAL_CHAR('}', json.back());
    TEST_ASSERT_EQUAL_STRING(nullptr, std::strchr(json.c_str(), '\n'));
    TEST_ASSERT_NOT_NULL(std::strstr(json.c_str(), "\"data\":\"00000080\""));
    TEST_ASSERT_NOT_NULL(
        std::strstr(json.c_str(), "\"decode_status\":\"field_decode_provisional\""));
}

void test_queue_drop_accounting() {
    DropAccounting drops;
    drops.add(4);
    drops.add(5);
    TEST_ASSERT_EQUAL_UINT32(2, drops.records());
    TEST_ASSERT_EQUAL_UINT32(9, drops.bytes());
    drops.reset();
    TEST_ASSERT_EQUAL_UINT32(0, drops.records());
    TEST_ASSERT_EQUAL_UINT32(0, drops.bytes());
}

}  // namespace

int main(int, char **) {
    UNITY_BEGIN();
    RUN_TEST(test_checksum_and_frame_validation);
    RUN_TEST(test_parser_recovers_after_insert_remove_and_noise);
    RUN_TEST(test_two_parser_instances_are_independent);
    RUN_TEST(test_signed_9_bit_decode_boundaries);
    RUN_TEST(test_signed_10_bit_motor_decode_boundaries);
    RUN_TEST(test_auto_classifies_synthetic_streams);
    RUN_TEST(test_output_serialization_is_standalone_json);
    RUN_TEST(test_queue_drop_accounting);
    return UNITY_END();
}
