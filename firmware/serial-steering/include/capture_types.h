#pragma once

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>

enum class ChannelId : std::uint8_t { kA, kB };

enum class DirectionGuess : std::uint8_t {
    kUnknown,
    kLkasToEps,
    kEpsToLkas,
};

enum class ParserMode : std::uint8_t { kAuto, kRaw, kFour, kFive };

struct ByteChunk {
    std::int64_t capture_time_us{};
    ChannelId channel{ChannelId::kA};
    std::uint16_t length{};
    std::array<std::uint8_t, 128> data{};
};

enum class ParsedRecordType : std::uint8_t { kFrame, kRawFragment };

class DropAccounting {
public:
    void add(std::uint32_t bytes) {
        records_.fetch_add(1, std::memory_order_relaxed);
        bytes_.fetch_add(bytes, std::memory_order_relaxed);
    }
    std::uint32_t records() const {
        return records_.load(std::memory_order_relaxed);
    }
    std::uint32_t bytes() const { return bytes_.load(std::memory_order_relaxed); }
    void reset() {
        records_.store(0, std::memory_order_relaxed);
        bytes_.store(0, std::memory_order_relaxed);
    }

private:
    std::atomic<std::uint32_t> records_{};
    std::atomic<std::uint32_t> bytes_{};
};

struct ParsedRecord {
    ParsedRecordType type{ParsedRecordType::kRawFragment};
    std::int64_t capture_time_us{};
    ChannelId channel{ChannelId::kA};
    DirectionGuess direction{DirectionGuess::kUnknown};
    std::uint16_t length{};
    std::array<std::uint8_t, 128> data{};
    const char *reason{"resync_discard"};
};

struct ParserCounters {
    std::uint32_t valid_4{};
    std::uint32_t valid_5{};
    std::uint32_t checksum_fail{};
    std::uint32_t candidate_starts{};
    std::uint32_t discarded_bytes{};
};

struct OutputRecord {
    std::uint16_t length{};
    std::array<char, 640> text{};
};
