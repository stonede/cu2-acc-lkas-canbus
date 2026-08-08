#pragma once

#include <atomic>
#include <cstdint>

#include "capture_types.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"

struct ChannelRuntimeStats {
    std::atomic<std::uint32_t> bytes{};
    std::atomic<std::uint32_t> valid_4{};
    std::atomic<std::uint32_t> valid_5{};
    std::atomic<std::uint32_t> checksum_fail{};
    std::atomic<std::uint32_t> parity_err{};
    std::atomic<std::uint32_t> frame_err{};
    std::atomic<std::uint32_t> break_err{};
    std::atomic<std::uint32_t> fifo_overflow{};
    std::atomic<std::uint32_t> buffer_full{};
    DropAccounting capture_drop{};
    DropAccounting captured_output_drop{};
    std::atomic<std::uint32_t> output_queue_drop{};
    std::atomic<std::uint32_t> raw_bytes_discarded{};
};

extern QueueHandle_t g_capture_queue;
extern QueueHandle_t g_output_queue;
extern ChannelRuntimeStats g_channel_stats[2];
extern std::atomic<ParserMode> g_requested_modes[2];
extern std::atomic<DirectionGuess> g_directions[2];
extern std::atomic<bool> g_decode_enabled;
extern std::atomic<std::uint32_t> g_sequence;

std::size_t channel_index(ChannelId channel);
bool enqueue_output(const OutputRecord &record, ChannelId channel);
std::uint32_t next_sequence();
void reset_runtime_stats();
void start_uart_capture();
