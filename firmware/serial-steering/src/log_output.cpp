#include "log_output.h"

#include <cstdio>

#include "app_config.h"
#include "esp_check.h"
#include "esp_random.h"
#include "esp_timer.h"
#include "frame_parser.h"
#include "json_records.h"
#include "uart_capture.h"

#ifndef APP_GIT_HASH
#define APP_GIT_HASH "unknown"
#endif

namespace {

FrameParser g_parsers[2]{
    FrameParser(ChannelId::kA,
                static_cast<std::int64_t>(app_config::kAutoClassifyWindowMs) * 1000,
                app_config::kAutoMinValidFrames, app_config::kAutoMinValidPercent,
                app_config::kAutoWinnerMultiplier),
    FrameParser(ChannelId::kB,
                static_cast<std::int64_t>(app_config::kAutoClassifyWindowMs) * 1000,
                app_config::kAutoMinValidFrames, app_config::kAutoMinValidPercent,
                app_config::kAutoWinnerMultiplier),
};

StatsSnapshot snapshot(const ChannelRuntimeStats &stats) {
    StatsSnapshot result{};
    result.bytes = stats.bytes.load(std::memory_order_relaxed);
    result.valid_4 = stats.valid_4.load(std::memory_order_relaxed);
    result.valid_5 = stats.valid_5.load(std::memory_order_relaxed);
    result.checksum_fail = stats.checksum_fail.load(std::memory_order_relaxed);
    result.parity_err = stats.parity_err.load(std::memory_order_relaxed);
    result.frame_err = stats.frame_err.load(std::memory_order_relaxed);
    result.break_err = stats.break_err.load(std::memory_order_relaxed);
    result.fifo_overflow = stats.fifo_overflow.load(std::memory_order_relaxed);
    result.buffer_full = stats.buffer_full.load(std::memory_order_relaxed);
    result.capture_queue_drop = stats.capture_drop.records();
    result.capture_bytes_dropped = stats.capture_drop.bytes();
    result.output_queue_drop =
        stats.output_queue_drop.load(std::memory_order_relaxed);
    result.captured_output_drop = stats.captured_output_drop.records();
    result.captured_output_bytes_dropped = stats.captured_output_drop.bytes();
    result.raw_bytes_discarded =
        stats.raw_bytes_discarded.load(std::memory_order_relaxed);
    return result;
}

void parsed_record_callback(const ParsedRecord &record, void *) {
    OutputRecord output{};
    const bool include_detail =
        uxQueueSpacesAvailable(g_output_queue) > app_config::kOutputDetailReserve;
    const bool formatted = record.type == ParsedRecordType::kFrame
                               ? format_frame_record(output, record, next_sequence(),
                                                     g_decode_enabled.load(),
                                                     include_detail)
                               : format_raw_record(output, record, next_sequence());
    if (formatted && !enqueue_output(output, record.channel)) {
        g_channel_stats[channel_index(record.channel)].captured_output_drop.add(
            record.length);
    }
}

void update_parser_stats(std::size_t index, const ParserCounters &before,
                         const ParserCounters &after) {
    auto &stats = g_channel_stats[index];
    stats.valid_4.fetch_add(after.valid_4 - before.valid_4,
                            std::memory_order_relaxed);
    stats.valid_5.fetch_add(after.valid_5 - before.valid_5,
                            std::memory_order_relaxed);
    stats.checksum_fail.fetch_add(after.checksum_fail - before.checksum_fail,
                                  std::memory_order_relaxed);
    stats.raw_bytes_discarded.fetch_add(
        after.discarded_bytes - before.discarded_bytes,
        std::memory_order_relaxed);
}

void parser_task(void *) {
    ByteChunk chunk{};
    while (true) {
        if (xQueueReceive(g_capture_queue, &chunk, portMAX_DELAY) != pdTRUE) continue;
        const auto index = channel_index(chunk.channel);
        auto &parser = g_parsers[index];
        const auto requested = g_requested_modes[index].load(std::memory_order_relaxed);
        if (requested != parser.mode()) {
            parser.set_mode(requested, parsed_record_callback, nullptr);
        }
        const auto before = parser.counters();
        parser.feed(chunk.data.data(), chunk.length, chunk.capture_time_us,
                    parsed_record_callback, nullptr);
        const auto after = parser.counters();
        update_parser_stats(index, before, after);
        if (parser.mode() != requested) {
            g_requested_modes[index].store(parser.mode(), std::memory_order_relaxed);
        }
        g_directions[index].store(parser.direction(), std::memory_order_relaxed);
    }
}

void write_record(const OutputRecord &record) {
    std::fwrite(record.text.data(), 1, record.length, stdout);
    std::fputc('\n', stdout);
}

void output_task(void *) {
    OutputRecord record{};
    std::int64_t next_stats = esp_timer_get_time() +
                              static_cast<std::int64_t>(app_config::kStatsPeriodMs) * 1000;
    while (true) {
        if (xQueueReceive(g_output_queue, &record, pdMS_TO_TICKS(100)) == pdTRUE) {
            write_record(record);
        }
        const auto now = esp_timer_get_time();
        if (now >= next_stats) {
            for (std::size_t i = 0; i < 2; ++i) {
                if (format_stats_record(record, now,
                                        i == 0 ? ChannelId::kA : ChannelId::kB,
                                        g_directions[i].load(std::memory_order_relaxed),
                                        snapshot(g_channel_stats[i]))) {
                    write_record(record);
                }
            }
            next_stats = now +
                         static_cast<std::int64_t>(app_config::kStatsPeriodMs) * 1000;
        }
    }
}

}  // namespace

void start_parser_and_output_tasks() {
    BaseType_t created = xTaskCreate(output_task, "output_task", 4096, nullptr, 8,
                                     nullptr);
    ESP_ERROR_CHECK(created == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
    created = xTaskCreate(parser_task, "parser_task", 6144, nullptr, 12, nullptr);
    ESP_ERROR_CHECK(created == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
}

void enqueue_session_record() {
    OutputRecord record{};
    char boot_id[17]{};
    std::snprintf(boot_id, sizeof(boot_id), "%08lX%08lX",
                  static_cast<unsigned long>(esp_random()),
                  static_cast<unsigned long>(esp_random()));
    if (format_session_record(record, APP_GIT_HASH, boot_id,
                              app_config::kVehicleBaud,
                              app_config::kConsoleBaud,
                              static_cast<int>(app_config::kChannelARxGpio),
                              static_cast<int>(app_config::kChannelBRxGpio))) {
        enqueue_output(record, ChannelId::kA);
    }
}

void enqueue_stats_records() {
    const auto now = esp_timer_get_time();
    for (std::size_t i = 0; i < 2; ++i) {
        OutputRecord record{};
        const auto channel = i == 0 ? ChannelId::kA : ChannelId::kB;
        if (format_stats_record(record, now, channel,
                                g_directions[i].load(std::memory_order_relaxed),
                                snapshot(g_channel_stats[i]))) {
            enqueue_output(record, channel);
        }
    }
}
