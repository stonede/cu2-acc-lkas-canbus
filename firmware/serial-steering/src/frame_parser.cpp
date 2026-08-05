#include "frame_parser.h"

#include <algorithm>

#include "honda_serial_protocol.h"

FrameParser::FrameParser(ChannelId channel, std::int64_t auto_window_us,
                         std::uint32_t auto_min_valid,
                         std::uint32_t auto_min_percent,
                         std::uint32_t auto_winner_multiplier)
    : channel_(channel),
      auto_window_us_(auto_window_us),
      auto_min_valid_(auto_min_valid),
      auto_min_percent_(auto_min_percent),
      auto_winner_multiplier_(auto_winner_multiplier) {
    buffer_.reserve(128);
    four_.buffer.reserve(8);
    five_.buffer.reserve(10);
}

void FrameParser::feed(const std::uint8_t *data, std::size_t length,
                       std::int64_t capture_time_us, Callback callback,
                       void *context) {
    if (mode_ == ParserMode::kRaw || mode_ == ParserMode::kAuto) {
        std::array<TimedByte, 128> raw{};
        for (std::size_t offset = 0; offset < length; offset += 128) {
            const auto count = std::min<std::size_t>(128, length - offset);
            for (std::size_t i = 0; i < count; ++i) {
                raw[i] = {data[offset + i], capture_time_us};
            }
            emit_raw(raw.data(), count,
                     mode_ == ParserMode::kRaw ? "raw_mode" : "auto_unclassified",
                     callback, context);
        }
        if (mode_ == ParserMode::kRaw) return;
        for (std::size_t i = 0; i < length; ++i) {
            if (is_candidate_start(data[i])) ++counters_.candidate_starts;
            feed_auto(data[i], capture_time_us);
        }
        evaluate_auto(capture_time_us);
        return;
    }

    for (std::size_t i = 0; i < length; ++i) {
        if (is_candidate_start(data[i])) ++counters_.candidate_starts;
        feed_known(data[i], capture_time_us, callback, context);
    }
}

void FrameParser::set_mode(ParserMode mode, Callback callback, void *context) {
    if (mode == mode_) return;
    if (!buffer_.empty()) {
        emit_raw(buffer_.data(), buffer_.size(), "mode_change", callback, context);
        counters_.discarded_bytes += static_cast<std::uint32_t>(buffer_.size());
        buffer_.clear();
    }
    mode_ = mode;
    direction_ = mode == ParserMode::kFour
                     ? DirectionGuess::kLkasToEps
                     : mode == ParserMode::kFive ? DirectionGuess::kEpsToLkas
                                                 : DirectionGuess::kUnknown;
    reset_auto_window(-1);
}

void FrameParser::feed_auto(std::uint8_t value, std::int64_t time_us) {
    if (auto_window_start_us_ < 0) auto_window_start_us_ = time_us;
    feed_hypothesis(four_, value, counters_.valid_4);
    feed_hypothesis(five_, value, counters_.valid_5);
}

void FrameParser::feed_hypothesis(Hypothesis &hypothesis, std::uint8_t value,
                                  std::uint32_t &valid_counter) {
    hypothesis.buffer.push_back({value, 0});
    while (hypothesis.buffer.size() >= hypothesis.length) {
        if (!is_candidate_start(hypothesis.buffer.front().value)) {
            hypothesis.buffer.erase(hypothesis.buffer.begin());
            continue;
        }
        std::uint8_t candidate[5]{};
        for (std::size_t i = 0; i < hypothesis.length; ++i) {
            candidate[i] = hypothesis.buffer[i].value;
        }
        if (valid_frame(candidate, hypothesis.length)) {
            ++hypothesis.valid;
            ++valid_counter;
            hypothesis.buffer.erase(hypothesis.buffer.begin(),
                                    hypothesis.buffer.begin() + hypothesis.length);
        } else {
            ++hypothesis.failed;
            ++counters_.checksum_fail;
            hypothesis.buffer.erase(hypothesis.buffer.begin());
        }
    }
}

void FrameParser::evaluate_auto(std::int64_t time_us) {
    if (auto_window_start_us_ < 0 ||
        time_us - auto_window_start_us_ < auto_window_us_) {
        return;
    }
    const auto qualifies = [this](const Hypothesis &candidate,
                                  const Hypothesis &other) {
        const auto attempts = candidate.valid + candidate.failed;
        return candidate.valid >= auto_min_valid_ && attempts > 0 &&
               candidate.valid * 100U >= attempts * auto_min_percent_ &&
               candidate.valid >= other.valid * auto_winner_multiplier_;
    };
    if (qualifies(four_, five_)) {
        mode_ = ParserMode::kFour;
        direction_ = DirectionGuess::kLkasToEps;
    } else if (qualifies(five_, four_)) {
        mode_ = ParserMode::kFive;
        direction_ = DirectionGuess::kEpsToLkas;
    } else {
        reset_auto_window(time_us);
    }
}

void FrameParser::feed_known(std::uint8_t value, std::int64_t time_us,
                             Callback callback, void *context) {
    buffer_.push_back({value, time_us});
    const std::size_t frame_length = mode_ == ParserMode::kFour ? 4 : 5;
    while (buffer_.size() >= frame_length) {
        std::uint8_t candidate[5]{};
        for (std::size_t i = 0; i < frame_length; ++i) {
            candidate[i] = buffer_[i].value;
        }
        if (valid_frame(candidate, frame_length)) {
            emit_frame(frame_length, callback, context);
            if (frame_length == 4) {
                ++counters_.valid_4;
            } else {
                ++counters_.valid_5;
            }
            buffer_.erase(buffer_.begin(), buffer_.begin() + frame_length);
            continue;
        }
        if (is_candidate_start(buffer_.front().value)) ++counters_.checksum_fail;
        emit_raw(buffer_.data(), 1, "resync_discard", callback, context);
        ++counters_.discarded_bytes;
        buffer_.erase(buffer_.begin());
    }
}

void FrameParser::emit_frame(std::size_t length, Callback callback, void *context) {
    ParsedRecord record{};
    record.type = ParsedRecordType::kFrame;
    record.capture_time_us = buffer_.front().time_us;
    record.channel = channel_;
    record.direction = direction_;
    record.length = static_cast<std::uint16_t>(length);
    for (std::size_t i = 0; i < length; ++i) record.data[i] = buffer_[i].value;
    callback(record, context);
}

void FrameParser::emit_raw(const TimedByte *bytes, std::size_t length,
                           const char *reason, Callback callback, void *context) {
    for (std::size_t offset = 0; offset < length; offset += 128) {
        ParsedRecord record{};
        record.type = ParsedRecordType::kRawFragment;
        record.capture_time_us = bytes[offset].time_us;
        record.channel = channel_;
        record.direction = DirectionGuess::kUnknown;
        record.length = static_cast<std::uint16_t>(
            std::min<std::size_t>(128, length - offset));
        record.reason = reason;
        for (std::size_t i = 0; i < record.length; ++i) {
            record.data[i] = bytes[offset + i].value;
        }
        callback(record, context);
    }
}

void FrameParser::reset_auto_window(std::int64_t start_us) {
    auto_window_start_us_ = start_us;
    four_.buffer.clear();
    five_.buffer.clear();
    four_.valid = four_.failed = 0;
    five_.valid = five_.failed = 0;
}
