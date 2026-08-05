#include "uart_capture.h"

#include <algorithm>

#include "app_config.h"
#include "driver/uart.h"
#include "esp_check.h"
#include "esp_timer.h"
#include "json_records.h"

QueueHandle_t g_capture_queue{};
QueueHandle_t g_output_queue{};
ChannelRuntimeStats g_channel_stats[2]{};
std::atomic<ParserMode> g_requested_modes[2]{ParserMode::kAuto, ParserMode::kAuto};
std::atomic<DirectionGuess> g_directions[2]{DirectionGuess::kUnknown,
                                            DirectionGuess::kUnknown};
std::atomic<bool> g_decode_enabled{true};
std::atomic<std::uint32_t> g_sequence{};

namespace {

struct UartTaskConfig {
    uart_port_t uart;
    gpio_num_t rx_gpio;
    ChannelId channel;
    QueueHandle_t event_queue;
    const char *task_name;
};

UartTaskConfig g_uart_configs[2]{
    {app_config::kChannelAUart, app_config::kChannelARxGpio, ChannelId::kA,
     nullptr, "channel_a_uart_task"},
    {app_config::kChannelBUart, app_config::kChannelBRxGpio, ChannelId::kB,
     nullptr, "channel_b_uart_task"},
};

void emit_uart_error(ChannelId channel, const char *name, std::uint32_t count,
                     int event_type = -1) {
    OutputRecord output{};
    if (format_uart_error_record(output, esp_timer_get_time(), channel, name,
                                 count, event_type)) {
        enqueue_output(output, channel);
    }
}

void uart_task(void *argument) {
    auto &config = *static_cast<UartTaskConfig *>(argument);
    auto &stats = g_channel_stats[channel_index(config.channel)];
    uart_event_t event{};
    while (true) {
        if (xQueueReceive(config.event_queue, &event, portMAX_DELAY) != pdTRUE) continue;
        switch (event.type) {
            case UART_DATA: {
                std::size_t remaining = event.size;
                while (remaining > 0) {
                    ByteChunk chunk{};
                    chunk.channel = config.channel;
                    const auto requested = std::min<std::size_t>(chunk.data.size(), remaining);
                    const int read = uart_read_bytes(config.uart, chunk.data.data(), requested, 0);
                    if (read <= 0) break;
                    chunk.capture_time_us = esp_timer_get_time();
                    chunk.length = static_cast<std::uint16_t>(read);
                    stats.bytes.fetch_add(static_cast<std::uint32_t>(read),
                                          std::memory_order_relaxed);
                    if (xQueueSend(g_capture_queue, &chunk, 0) != pdTRUE) {
                        stats.capture_drop.add(static_cast<std::uint32_t>(read));
                    }
                    remaining -= static_cast<std::size_t>(read);
                }
                break;
            }
            case UART_FIFO_OVF: {
                const auto count =
                    stats.fifo_overflow.fetch_add(1, std::memory_order_relaxed) + 1;
                uart_flush_input(config.uart);
                xQueueReset(config.event_queue);
                emit_uart_error(config.channel, "fifo_overflow", count);
                break;
            }
            case UART_BUFFER_FULL: {
                const auto count =
                    stats.buffer_full.fetch_add(1, std::memory_order_relaxed) + 1;
                uart_flush_input(config.uart);
                xQueueReset(config.event_queue);
                emit_uart_error(config.channel, "buffer_full", count);
                break;
            }
            case UART_PARITY_ERR: {
                const auto count =
                    stats.parity_err.fetch_add(1, std::memory_order_relaxed) + 1;
                emit_uart_error(config.channel, "parity", count);
                break;
            }
            case UART_FRAME_ERR: {
                const auto count =
                    stats.frame_err.fetch_add(1, std::memory_order_relaxed) + 1;
                emit_uart_error(config.channel, "frame", count);
                break;
            }
            default:
                emit_uart_error(config.channel, "unknown_event", 1, event.type);
                break;
        }
    }
}

void configure_uart(UartTaskConfig &task) {
    uart_config_t config{};
    config.baud_rate = app_config::kVehicleBaud;
    config.data_bits = UART_DATA_8_BITS;
    config.parity = UART_PARITY_EVEN;
    config.stop_bits = UART_STOP_BITS_1;
    config.flow_ctrl = UART_HW_FLOWCTRL_DISABLE;
    config.rx_flow_ctrl_thresh = 0;
    config.source_clk = UART_SCLK_DEFAULT;
    ESP_ERROR_CHECK(uart_param_config(task.uart, &config));
    ESP_ERROR_CHECK(uart_set_pin(task.uart, UART_PIN_NO_CHANGE, task.rx_gpio,
                                 UART_PIN_NO_CHANGE, UART_PIN_NO_CHANGE));
    ESP_ERROR_CHECK(uart_driver_install(
        task.uart, app_config::kUartRxBufferBytes, 0,
        app_config::kUartEventQueueDepth, &task.event_queue, 0));
    ESP_ERROR_CHECK(uart_set_rx_timeout(task.uart, 2));
    const BaseType_t created = xTaskCreate(uart_task, task.task_name, 4096, &task,
                                           18, nullptr);
    ESP_ERROR_CHECK(created == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
}

}  // namespace

std::size_t channel_index(ChannelId channel) {
    return channel == ChannelId::kA ? 0U : 1U;
}

bool enqueue_output(const OutputRecord &record, ChannelId channel) {
    if (xQueueSend(g_output_queue, &record, 0) == pdTRUE) return true;
    g_channel_stats[channel_index(channel)].output_queue_drop.fetch_add(
        1, std::memory_order_relaxed);
    return false;
}

std::uint32_t next_sequence() {
    return g_sequence.fetch_add(1, std::memory_order_relaxed) + 1;
}

void reset_runtime_stats() {
    for (auto &stats : g_channel_stats) {
        stats.bytes = 0;
        stats.valid_4 = 0;
        stats.valid_5 = 0;
        stats.checksum_fail = 0;
        stats.parity_err = 0;
        stats.frame_err = 0;
        stats.fifo_overflow = 0;
        stats.buffer_full = 0;
        stats.capture_drop.reset();
        stats.captured_output_drop.reset();
        stats.output_queue_drop = 0;
        stats.raw_bytes_discarded = 0;
    }
}

void start_uart_capture() {
    for (auto &config : g_uart_configs) configure_uart(config);
}
