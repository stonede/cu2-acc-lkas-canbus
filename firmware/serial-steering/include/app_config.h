#pragma once

#include <cstddef>
#include <cstdint>

#include "driver/gpio.h"
#include "driver/uart.h"

namespace app_config {

constexpr uart_port_t kChannelAUart = UART_NUM_1;
constexpr uart_port_t kChannelBUart = UART_NUM_2;
constexpr gpio_num_t kChannelARxGpio = GPIO_NUM_32;
constexpr gpio_num_t kChannelBRxGpio = GPIO_NUM_33;
constexpr int kVehicleBaud = 9600;
constexpr int kConsoleBaud = 460800;
constexpr std::size_t kConsoleRxBufferBytes = 1024;
constexpr std::size_t kConsoleTxBufferBytes = 4096;
constexpr std::size_t kUartRxBufferBytes = 4096;
constexpr std::size_t kUartEventQueueDepth = 64;
constexpr std::size_t kCaptureQueueDepth = 512;
constexpr std::size_t kOutputQueueDepth = 64;
constexpr std::size_t kOutputDetailReserve = 16;
constexpr std::uint32_t kStatsPeriodMs = 5000;
constexpr std::uint32_t kAutoClassifyWindowMs = 5000;
constexpr std::uint32_t kAutoMinValidFrames = 20;
constexpr std::uint32_t kAutoMinValidPercent = 90;
constexpr std::uint32_t kAutoWinnerMultiplier = 3;

}  // namespace app_config
