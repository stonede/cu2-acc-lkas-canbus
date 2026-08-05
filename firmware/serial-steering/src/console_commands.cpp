#include "console_commands.h"

#include <cstdio>
#include <cstring>

#include "esp_check.h"
#include "esp_timer.h"
#include "json_records.h"
#include "log_output.h"
#include "uart_capture.h"

namespace {

void reply(const char *status, const char *message) {
    OutputRecord record{};
    if (format_console_record(record, esp_timer_get_time(), status, message)) {
        enqueue_output(record, ChannelId::kA);
    }
}

bool parse_mode(const char *text, ParserMode &mode) {
    if (std::strcmp(text, "auto") == 0) mode = ParserMode::kAuto;
    else if (std::strcmp(text, "raw") == 0) mode = ParserMode::kRaw;
    else if (std::strcmp(text, "4") == 0) mode = ParserMode::kFour;
    else if (std::strcmp(text, "5") == 0) mode = ParserMode::kFive;
    else return false;
    return true;
}

void handle_command(char *line) {
    if (std::strcmp(line, "!status") == 0) {
        enqueue_stats_records();
        char message[96]{};
        std::snprintf(message, sizeof(message), "A=%s B=%s decode=%s",
                      mode_name(g_requested_modes[0].load()),
                      mode_name(g_requested_modes[1].load()),
                      g_decode_enabled.load() ? "on" : "off");
        reply("ok", message);
        return;
    }
    if (std::strcmp(line, "!stats reset") == 0) {
        reset_runtime_stats();
        reply("ok", "statistics reset");
        return;
    }
    if (std::strncmp(line, "!mark ", 6) == 0 && line[6] != '\0') {
        OutputRecord record{};
        if (format_mark_record(record, esp_timer_get_time(), line + 6)) {
            enqueue_output(record, ChannelId::kA);
        }
        return;
    }
    if (std::strncmp(line, "!decode ", 8) == 0) {
        const char *value = line + 8;
        if (std::strcmp(value, "on") == 0 || std::strcmp(value, "off") == 0) {
            g_decode_enabled.store(std::strcmp(value, "on") == 0);
            reply("ok", g_decode_enabled.load() ? "decode on" : "decode off");
        } else {
            reply("error", "usage: !decode on|off");
        }
        return;
    }
    if (std::strncmp(line, "!channel ", 9) == 0) {
        char channel = '\0';
        char mode_text[8]{};
        ParserMode mode{};
        if (std::sscanf(line, "!channel %c %7s", &channel, mode_text) == 2 &&
            (channel == 'A' || channel == 'B') && parse_mode(mode_text, mode)) {
            g_requested_modes[channel == 'A' ? 0 : 1].store(mode);
            reply("ok", "channel mode queued");
        } else {
            reply("error", "usage: !channel A|B auto|raw|4|5");
        }
        return;
    }
    if (std::strcmp(line, "!help") == 0) {
        reply("ok", "!status; !mark TEXT; !stats reset; !channel A|B auto|raw|4|5; !decode on|off; !help");
        return;
    }
    reply("error", "unknown command; use !help");
}

void console_task(void *) {
    char line[256]{};
    while (std::fgets(line, sizeof(line), stdin) != nullptr) {
        line[std::strcspn(line, "\r\n")] = '\0';
        if (line[0] == '!') handle_command(line);
    }
    vTaskDelete(nullptr);
}

}  // namespace

void start_console_task() {
    const BaseType_t created =
        xTaskCreate(console_task, "console_task", 4096, nullptr, 5, nullptr);
    ESP_ERROR_CHECK(created == pdPASS ? ESP_OK : ESP_ERR_NO_MEM);
}
