/*
 File: console_cmds.h
 Author: Hankso
 Webpage: http://github.com/hankso
 Time: Tue 19 Mar 2019 16:53:48 CST
 
*/

#ifndef console_cmds_h
#define console_cmds_h


#include "ESP32_Sandbox.h"

#include "esp_log.h"
#include "esp_console.h"
#include "rom/uart.h"
#include "linenoise/linenoise.h"
#include "argtable3/argtable3.h"


void register_spi_cmds() {
    esp_console_cmd_t clear = {
        .command = "clear",
        .help = "Clear SPI FIFO queue",
        .hint = NULL,
        .func = [](int argc, char **argv) -> int {
            cq->clear();
            ESP_LOGI(NAME, "Queue empty now");
            return 0;
        },
        .argtable = NULL,
    };
    esp_console_cmd_t reset = {
        .command = "reset",
        .help = "Reset ads1299 and read id register",
        .hint = NULL,
        .func = [](int argc, char **argv) -> int {
            char tmp[24 + 1];
            itoa(ads.init(), tmp, 2);
            ESP_LOGI(NAME, "ADS first register value: 0b%s", tmp);
            return 0;
        },
        .argtable = NULL,
    };
    static struct {
        struct arg_int *data_source;
        struct arg_end *end;
    } source_args = {
        .data_source = arg_int0("d", "data", "<0|1|2|3>", "specify data source"),
        .end = arg_end(1),
    };
    esp_console_cmd_t source = {
        .command = "source",
        .help = "Display or change esp output data source",
        .hint = NULL,
        .func = [](int argc, char **argv) -> int {
            if (arg_parse(argc, argv, (void **) &source_args) != 0) {
                arg_print_errors(stderr, source_args.end, argv[0]);
                return 1;
            }
            if (source_args.data_source->count) {
                int source = source_args.data_source->ival[0];
                if (source < 0 || source > 3) {
                    ESP_LOGE(NAME, "Invalid data source: %d", source);
                    return 1;
                }
                data_source = static_cast<spi_data_source>(source);
            }
            const char *source_name = data_source_list[data_source];
            ESP_LOGI(NAME, "Current output data: %s", source_name);
            return 0;
        },
        .argtable = &source_args
    };
    ESP_ERROR_CHECK( esp_console_cmd_register(&clear) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&reset) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&source) );
}

void register_wifi_cmds() {
    static struct {
        struct arg_str *action;
        struct arg_end *end;
    } wifi_args = {
        .action = arg_str0("a", "action", "<on|off>", "also canbe true|false"),
        .end = arg_end(1),
    };
    esp_console_cmd_t wifi = {
        .command = "wifi",
        .help = "Turn on/off serial-to-Wifi redirection",
        .hint = NULL,
        .func = [](int argc, char **argv) -> int {
            if (arg_parse(argc, argv, (void **) &wifi_args) != 0) {
                arg_print_errors(stderr, wifi_args.end, argv[0]);
                return 1;
            }
            if (wifi_args.action->count) {
                const char *action = wifi_args.action->sval[0];
                if (!strcmp(action, "true") || !strcmp(action, "on")) {
                    wifi_echo = true;
                } else if (!strcmp(action, "false") || !strcmp(action, "off")) {
                    wifi_echo = false;
                } else {
                    ESP_LOGE(NAME, "Invalid wifi command: %s", action);
                    return 1;
                }
            }
            ESP_LOGI(NAME, "Serial-to-wifi redirection: %s", 
                     wifi_echo ? "ON" : "OFF");
            return 0;
        },
        .argtable = &wifi_args,
    };
    ESP_ERROR_CHECK( esp_console_cmd_register(&wifi) );
}

static struct {
    struct arg_int *wakeup_time;
    struct arg_int *wakeup_gpio_num;
    struct arg_int *wakeup_gpio_level;
    struct arg_str *sleep;
    struct arg_end *end;
} sleep_args = {
    .wakeup_time = arg_int0("t", "time", "<t>", "wakeup time, ms"),
    .wakeup_gpio_num = 
        arg_intn("p", "gpio", "<n>", 0, 8,
                 "If specified, wakeup using GPIO with given number"),
    .wakeup_gpio_level = 
        arg_intn("l", "level", "<0|1>", 0, 8,
                 "GPIO level to trigger wakeup"),
    .sleep = arg_str0(NULL, "method", "<s>", "sleep method"),
    .end = arg_end(4),
};

int enable_gpio_light_wakeup() {
    int gpio_count = sleep_args.wakeup_gpio_num->count;
    int level_count = sleep_args.wakeup_gpio_level->count;
    if (level_count && (gpio_count != level_count)) {
        ESP_LOGE(NAME, "GPIO and level mismatch!");
        return 1;
    }
    int gpio, level;
    gpio_int_type_t intr;
    for (int i = 0; i < gpio_count; i++) {
        gpio = sleep_args.wakeup_gpio_num->ival[i];
        if (level_count != 0) {
            level = sleep_args.wakeup_gpio_level->ival[i];
        } else {
            level = 0;
        }
        ESP_LOGI(NAME, "Enable GPIO wakeup, num: %d, level: %s",
                 gpio, level ? "HIGH" : "LOW");
        intr = level ? GPIO_INTR_HIGH_LEVEL : GPIO_INTR_LOW_LEVEL;
        ESP_ERROR_CHECK( gpio_wakeup_enable((gpio_num_t)gpio, intr) );
    }
    ESP_ERROR_CHECK( esp_sleep_enable_gpio_wakeup() );
    return 0;
}

int enable_gpio_deep_wakeup() {
    int gpio = sleep_args.wakeup_gpio_num->ival[0], level = 0;
    if (sleep_args.wakeup_gpio_level->count) {
        level = sleep_args.wakeup_gpio_level->ival[0];
        if (level != 0 && level != 1) {
            ESP_LOGE(NAME, "Invalid wakeup level: %d", level);
            return 1;
        }
    }
    ESP_LOGI(NAME, "Enable GPIO wakeup, num: %d, level: %s",
             gpio, level ? "HIGH" : "LOW");
    esp_sleep_ext1_wakeup_mode_t mode;
    mode = level ? ESP_EXT1_WAKEUP_ANY_HIGH : ESP_EXT1_WAKEUP_ALL_LOW;
    ESP_ERROR_CHECK( esp_sleep_enable_ext1_wakeup(1ULL << gpio, mode) );
    return 0;
}

void register_sleep_cmds() {
    esp_console_cmd_t sleep = {
        .command = "sleep",
        .help = "Turn ESP32 into light/deep sleep mode",
        .hint = NULL,
        .func = [](int argc, char **argv) {
            if (arg_parse(argc, argv, (void **) &sleep_args) != 0) {
                arg_print_errors(stderr, sleep_args.end, argv[0]);
                return 1;
            }
            if (sleep_args.wakeup_time->count) {
                uint64_t timeout = sleep_args.wakeup_time->ival[0];
                ESP_LOGI(NAME, "Enable timer wakeup, timeout: %llums", timeout);
                ESP_ERROR_CHECK( esp_sleep_enable_timer_wakeup(timeout * 1000) );
            }
            bool light_sleep = true;
            if (sleep_args.sleep->count) {
                const char *sleep = sleep_args.sleep->sval[0];
                if (strcmp(sleep, "deep") == 0) {
                    light_sleep = false;
                } else if (strcmp(sleep, "light") != 0) {
                    ESP_LOGE(NAME, "Invalid sleep method: %s", sleep);
                    return 1;
                }
            }
            if (light_sleep) {
                if (sleep_args.wakeup_gpio_num->count) {
                    if (enable_gpio_light_wakeup() != 0) return 1;
                }
                ESP_LOGI(NAME, "Enable UART wakeup, num: %d", UART_CONSOLE);
                ESP_ERROR_CHECK( uart_set_wakeup_threshold(UART_CONSOLE, 3) );
                ESP_ERROR_CHECK( esp_sleep_enable_uart_wakeup(UART_CONSOLE) );
            } else {
                if (sleep_args.wakeup_gpio_num->count) {
                    if (enable_gpio_deep_wakeup() != 0) return 1;
                }
            }

            ESP_LOGW(NAME, "ESP32 will turn into %s sleep mode",
                     light_sleep ? "light" : "deep");
            fflush(stdout); uart_tx_wait_idle(UART_CONSOLE);
            if (light_sleep) {
                esp_light_sleep_start();
            } else {
                esp_deep_sleep_start();
            }
            ESP_LOGW(NAME, "ESP32 is woken up from light sleep mode by %s", 
                     wakeup_reason_list[(int)esp_sleep_get_wakeup_cause()]);
            esp_sleep_disable_wakeup_source(ESP_SLEEP_WAKEUP_ALL);
            return 0;

        },
        .argtable = &sleep_args,
    };
    ESP_ERROR_CHECK( esp_console_cmd_register(&sleep) );
}

void register_utils_cmds() {
    esp_console_cmd_t verbose = {
        .command = "verbose",
        .help = "Be more verbose",
        .hint = NULL,
        .func = [](int argc, char **argv) -> int {
            log_level = esp_log_level_t( min((log_level + 1), log_level_max) );
            esp_log_level_set(NAME, log_level);
            ESP_LOGW(NAME, "Current log level: %s", log_level_list[log_level]);
            return 0;
        },
        .argtable = NULL
    };
    esp_console_cmd_t quiet = {
        .command = "quiet",
        .help = "Be more quiet",
        .hint = NULL,
        .func = [](int argc, char **argv) -> int {
            log_level = esp_log_level_t( max((log_level - 1), log_level_min) );
            esp_log_level_set(NAME, log_level);
            ESP_LOGW(NAME, "Current log level: %s", log_level_list[log_level]);
            return 0;
        },
        .argtable = NULL
    };
    esp_console_cmd_t summary = {
        .command = "summary",
        .help = "Print summary of current status",
        .hint = NULL,
        .func = [](int argc, char **argv) -> int {
            char tmp[8 + 1];
            itoa(ads.statusBit, tmp, 2);
            ESP_LOGW(NAME, "ADS data head:  0b%s", tmp);
            uint32_t v0 = counter.value(0), v1 = counter.value(1);
            ESP_LOGW(NAME, "Valid packets:  %d/%d Hz", v1, v0);
            ESP_LOGW(NAME, "Output data:    %s", data_source_list[data_source]);
            ESP_LOGW(NAME, "Logging level:  %s", log_level_list[log_level]);
            ESP_LOGW(NAME, "Serial to wifi: %s", wifi_echo ? "ON" : "OFF");
            float bufrate = (float)(cq->len) / M_BUFFERSIZE;
            ESP_LOGW(NAME, "buffer used:    %.2f%%", bufrate * 100);
            return 0;
        },
        .argtable = NULL
    };
    ESP_ERROR_CHECK( esp_console_cmd_register(&verbose) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&quiet) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&summary) );
}


void initialize_console() {
    linenoiseSetMultiLine(1);
    linenoiseSetCompletionCallback(&esp_console_get_completion);
    linenoiseSetHintsCallback((linenoiseHintsCallback*)&esp_console_get_hint);
    linenoiseHistorySetMaxLen(100);
    if (linenoiseProbe() != 0) {
        linenoiseSetDumbMode(1);
    }

    esp_console_config_t console_config = {
        .max_cmdline_length = 256,
        .max_cmdline_args = 8,
        .hint_color = atoi(LOG_COLOR_CYAN),
        .hint_bold = atoi(LOG_COLOR_CYAN)
    };
    ESP_ERROR_CHECK( esp_console_init(&console_config) );
    esp_console_register_help_command();
    register_spi_cmds();
    register_wifi_cmds();
    register_sleep_cmds();
    register_utils_cmds();
}

void handle_console() {
    char *line = linenoise(prompt);
    if (line == NULL) return;
    linenoiseHistoryAdd(line);
    int cbret;
    esp_err_t err = esp_console_run(line, &cbret);
    if (err == ESP_ERR_NOT_FOUND) {
        printf("Unrecognized command: %s\n", line);
    } else if (err == ESP_OK && cbret != ESP_OK) {
        printf("Command error: 0x%d (%s)\n", cbret, esp_err_to_name(cbret));
    } else if (err != ESP_OK) {
        printf("%s\n", esp_err_to_name(err));
    }
    linenoiseFree(line);
}

void console_loop(void *argv) {
    while (true) {
        handle_console();
    }
}

#endif // console_cmd_h
