#pragma once

#include <cstddef>
#include <cstdint>
#include <vector>

#include "capture_types.h"

class FrameParser {
public:
    using Callback = void (*)(const ParsedRecord &, void *);

    explicit FrameParser(ChannelId channel,
                         std::int64_t auto_window_us = 5'000'000,
                         std::uint32_t auto_min_valid = 20,
                         std::uint32_t auto_min_percent = 90,
                         std::uint32_t auto_winner_multiplier = 3);

    void feed(const std::uint8_t *data, std::size_t length,
              std::int64_t capture_time_us, Callback callback, void *context);
    void set_mode(ParserMode mode, Callback callback, void *context);
    ParserMode mode() const { return mode_; }
    DirectionGuess direction() const { return direction_; }
    const ParserCounters &counters() const { return counters_; }

private:
    struct TimedByte {
        std::uint8_t value;
        std::int64_t time_us;
    };

    struct Hypothesis {
        explicit Hypothesis(std::size_t frame_length) : length(frame_length) {}
        std::size_t length;
        std::vector<TimedByte> buffer;
        std::uint32_t valid{};
        std::uint32_t failed{};
    };

    void feed_auto(std::uint8_t value, std::int64_t time_us);
    void feed_hypothesis(Hypothesis &hypothesis, std::uint8_t value,
                         std::uint32_t &valid_counter);
    void evaluate_auto(std::int64_t time_us);
    void feed_known(std::uint8_t value, std::int64_t time_us,
                    Callback callback, void *context);
    void emit_frame(std::size_t length, Callback callback, void *context);
    void emit_raw(const TimedByte *bytes, std::size_t length, const char *reason,
                  Callback callback, void *context);
    void reset_auto_window(std::int64_t start_us);

    ChannelId channel_;
    ParserMode mode_{ParserMode::kAuto};
    DirectionGuess direction_{DirectionGuess::kUnknown};
    std::vector<TimedByte> buffer_;
    Hypothesis four_{4};
    Hypothesis five_{5};
    ParserCounters counters_{};
    std::int64_t auto_window_start_us_{-1};
    std::int64_t auto_window_us_;
    std::uint32_t auto_min_valid_;
    std::uint32_t auto_min_percent_;
    std::uint32_t auto_winner_multiplier_;
};
