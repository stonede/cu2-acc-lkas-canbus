#include <cstdio>

#include "app_config.h"
#include "console_commands.h"
#include "driver/uart.h"
#include "driver/uart_vfs.h"
#include "esp_check.h"
#include "freertos/FreeRTOS.h"
#include "freertos/queue.h"
#include "log_output.h"
#include "uart_capture.h"

extern "C" void app_main() {
    std::setvbuf(stdout, nullptr, _IONBF, 0);
    ESP_ERROR_CHECK(uart_driver_install(
        UART_NUM_0, app_config::kConsoleRxBufferBytes,
        app_config::kConsoleTxBufferBytes, 0, nullptr, 0));
    uart_vfs_dev_use_driver(UART_NUM_0);
    ESP_ERROR_CHECK(uart_vfs_dev_port_set_rx_line_endings(
                        UART_NUM_0, ESP_LINE_ENDINGS_LF) == 0
                        ? ESP_OK
                        : ESP_FAIL);
    g_capture_queue =
        xQueueCreate(app_config::kCaptureQueueDepth, sizeof(ByteChunk));
    g_output_queue =
        xQueueCreate(app_config::kOutputQueueDepth, sizeof(OutputRecord));
    ESP_ERROR_CHECK(g_capture_queue != nullptr && g_output_queue != nullptr
                        ? ESP_OK
                        : ESP_ERR_NO_MEM);

    start_parser_and_output_tasks();
    enqueue_session_record();
    start_uart_capture();
    start_console_task();
}
