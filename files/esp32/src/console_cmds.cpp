/*
 File: console_cmds.cpp
 Authors: Hank <hankso1106@gmail.com>
 Create: 2019-04-18 23:02:44
 
 Definition of commands and callback functions.
 
 Copyright (c) 2019 EmBCI. All right reserved.

 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:

 The above copyright notice and this permission notice shall be included in all
 copies or substantial portions of the Software.

 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 SOFTWARE.
*/

#include "console_cmds.h"
#include "globals.h"
#include "configs.h"

#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_system.h"
#include "esp_console.h"
#include "rom/uart.h"
#include "driver/uart.h"
#include "freertos/task.h"
#include "freertos/FreeRTOS.h"
#include "linenoise/linenoise.h"
#include "argtable3/argtable3.h"

/******************************************************************************
 * Common
 */

/* The argtables of each sub-commands are defined as a struct, containing 
 * declaration of arguments. When an argtable is initialized by
 * `struct XXX_args_t xxx_args = { ... }`, arguments are defined, too.
 * In this way it's not necessary to make argument variables global because
 * they can be accessed by `xxx_args.yyy`
 */
static struct arg_str *action = arg_str0(
        NULL, NULL, "<on|off>", "action can also be <true|false>");
static struct arg_int *channel = arg_int0(
        "c", "channel", "<0-7>", "specify channel number, default all");


// static struct action_args_t {
//     struct arg_str *action;
//     struct arg_end *end;
// } bool_args = {
//     .action = action,
//     .end = arg_end(1)
// };

typedef struct {
    struct arg_str *action;
    struct arg_int *channel;
    struct arg_end *end;
} action_channel_args_t;

action_channel_args_t
    action_args = {
        .action = action,
        .channel = arg_int0(NULL, NULL, "", NULL),
        .end = arg_end(1)
    },
    channel_args = {
        .action = action,
        .channel = channel,
        .end = arg_end(2),
    };

/* @brief   Get action value of commands, same as `bool(str) -> 0|1|2`
 * @return
 *          - 0     : Turn off (false)
 *          - 1     : Turn on (true)
 *          - other : Invalid action or argument not specified
 */
static int get_action(action_channel_args_t argtable) {
    if (argtable.action->count) {
        String action = String(argtable.action->sval[0]);
        if (action.equalsIgnoreCase("true") || 
            action.equalsIgnoreCase("on")) {
            return 1;
        } 
        if (action.equalsIgnoreCase("false") ||
            action.equalsIgnoreCase("off")) {
            return 0;
        }
        ESP_LOGE(NAME, "Invalid action: %s", action.c_str());
    }
    return -1;
}

/* @brief   Get channel value of commands, valid channel number is [0-7]
 * @return
 *          - -1  : invalid channel
 *          - num : channel number
 */
// static int get_channel(void **argtable) {
    // struct arg_hdr **table = (struct arg_hdr **) argtable;
static int get_channel(action_channel_args_t argtable) {
    if (argtable.channel->count) {
        int channel = argtable.channel->ival[0];
        if (-1 < channel && channel < 8) {
            return channel;
        }
        ESP_LOGE(NAME, "Invalid channel: %d", channel);
    }
    return -1;
}

/* @brief   Parse command line arguments into argtable and catch any errors
 * @return
 *          - true  : arguments successfully parsed, no error
 *          - false : error occur
 * */
static bool arg_noerror(int argc, char **argv, void **argtable) {
    if (arg_parse(argc, argv, argtable) != 0) {
        struct arg_hdr **table = (struct arg_hdr **) argtable;
        int tabindex = 0;
        while (!(table[tabindex]->flag & ARG_TERMINATOR)) { tabindex++; }
        arg_print_errors(stderr, (struct arg_end *) table[tabindex], argv[0]);
        return false;
    }
    return true;
}

/******************************************************************************
 * ADS1299 commands
 */

static struct {
    struct arg_int *rate;
    struct arg_end *end;
} sample_rate_args = {
    .rate = arg_int0(
            "r", "rate", "<0-6|250|500|1k|2k|4k|8k|16k>",
            "specify sample rate (250-16000) or its index (0-6)"),
    .end = arg_end(1)
};

esp_console_cmd_t ads_sample_rate = {
    .command = "sample_rate",
    .help = "Print or set ADS1299 sample rate",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        if (!arg_noerror(argc, argv, (void **) &sample_rate_args)) return 1;
        if (sample_rate_args.rate->count) {
            uint16_t rate_or_idx = sample_rate_args.rate->ival[0];
            if (rate_or_idx < 7) {
                rate_or_idx = ads1299_sample_rate[6 - rate_or_idx];
            }
            if (!ads.setSampleRate(rate_or_idx)) {
                ESP_LOGE(NAME, "Invalid sample rate: %d", rate_or_idx);
            }
        }
        ESP_LOGI(NAME, "Current ADS1299 sample rate: %d", ads.getSampleRate());
        return 0;
    },
    .argtable = &sample_rate_args
};

static struct {
    struct arg_str *source;
    struct arg_int *channel;
    struct arg_end *end;
} input_source_args = {
    .source = arg_str0(
            "s", "source", "<0-5|Normal|BIAS|Shorted|MVDD|Temperature|Test>",
            "specify source name or its index (0-5)"),
    .channel = channel,
    .end = arg_end(2)
};

esp_console_cmd_t ads_source = {
    .command = "input_source",
    .help = "Print or set ADS1299 data source",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        if (!arg_noerror(argc, argv, (void **) &input_source_args)) return 1;
        int ch = input_source_args.channel->count ? (
            input_source_args.channel->ival[0]
        ) : -1;
        if (ch > 7) {
            ESP_LOGE(NAME, "Invalid channel: %d", ch);
            return 1;
        }
        if (input_source_args.source->count) {
            String str = String(input_source_args.source->sval[0]);
            uint8_t source = str.toInt();
            uint8_t length = 
                sizeof(ads1299_data_source) / sizeof(ads1299_data_source[0]);
            bool strtol = true;
            if (source == 0 && !str.equals("0")) {
                strtol = false;
                for (uint8_t i = 0; i < length; i++) {
                    if (!str.equalsIgnoreCase(ads1299_data_source[i])) continue;
                    strtol = true; source = i; break;
                }
            }
            if (!strtol) {
                ESP_LOGE(NAME, "Invalid ADS1299 Source Name: %s", str.c_str());
                return 1;
            }
            if (source >= length) {
                ESP_LOGE(NAME, "Invalid ADS1299 Source Index: %d", source);
                return 1;
            }
            ads.setDataSource(ch, source);
        }
        const char *src = ads.getDataSource(ch);
        if (ch == -1) {
            ESP_LOGI(NAME, "ADS1299 Sources: %s", src);
            // TODO: List ADS1299 Sources
        } else {
            ESP_LOGI(NAME, "ADS1299 Source CH%d: %s", ch, src);
        }
        return 0;
    },
    .argtable = &input_source_args
};

esp_console_cmd_t ads_bias = {
    .command = "bias_output",
    .help = "Print or set ADS1299 BIAS output state",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        if (!arg_noerror(argc, argv, (void **) &action_args)) return 1;
        int act = get_action(action_args);
        if (act == 0) {
            ads.setBias(false);
            ESP_LOGD(NAME, "BIAS OUTPUT DISABLED");
        } else if (act == 1) {
            ads.setBias(true);
            ESP_LOGD(NAME, "BIAS OUTPUT ENABLED");
        }
        ESP_LOGI(NAME, "ADS1299 BIAS: %s", ads.getBias() ? "ON" : "OFF");
        return 0;
    },
    .argtable = &action_args
};

esp_console_cmd_t ads_impedance = {
    .command = "impedance",
    .help = "Print or set ADS1299 impedance measurement",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        if (!arg_noerror(argc, argv, (void **) &channel_args)) return 1;
        int ch = get_channel(channel_args), act = get_action(channel_args);
        if (act == 0) {
            ads.setImpedance(ch, false);
            ESP_LOGD(NAME, "IMPEDANCE DISABLED");
        } else if (act == 1) {
            ads.setImpedance(ch, true);
            ESP_LOGD(NAME, "IMPEDANCE ENABLED");
        }
        uint8_t chs = ads.getChannel(ch);
        if (ch == -1) {
            char tmp[8 + 1]; itoa(chs, tmp, 2);
            ESP_LOGI(NAME, "ADS1299 Impedance: 0b%s", tmp);
        } else {
            ESP_LOGI(NAME, "ADS1299 Impedance CH%d: %s", ch, chs ? "ON" : "OFF");
        }
        return 0;
    },
    .argtable = &channel_args
};

esp_console_cmd_t ads_channel = {
    .command = "channel",
    .help = "Enable/disable channel. Get channel status.",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        if (!arg_noerror(argc, argv, (void **) &channel_args)) return 1;
        int ch = get_channel(channel_args), act = get_action(channel_args);
        if (act == 0) {
            ads.setChannel(ch, false);
            ESP_LOGD(NAME, "CHANNEL DISABLED");
        } else if (act == 1) {
            ads.setChannel(ch, true);
            ESP_LOGD(NAME, "CHANNEL ENABLED");
        }
        uint8_t chs = ads.getChannel(ch);
        if (ch == -1) {
            char tmp[8 + 1]; itoa(chs, tmp, 2);
            ESP_LOGI(NAME, "ADS1299 All Channels: 0b%s", tmp);
        } else {
            ESP_LOGI(NAME, "ADS1299 CH%d: %s", ch, chs ? "ON" : "OFF");
        }
        return 0;
    },
    .argtable = &channel_args
};

/******************************************************************************
 * SPI commands
 */

esp_console_cmd_t spi_clear = {
    .command = "clear",
    .help = "Clear SPI FIFO queue",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        clear_fifo_queue();
        ESP_LOGI(NAME, "Queue empty now");
        return 0;
    },
    .argtable = NULL
};

esp_console_cmd_t spi_reset = {
    .command = "reset",
    .help = "Reset ads1299 and read id register",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        char tmp[8 + 1];
        itoa(ads.init(), tmp, 2);
        ESP_LOGI(NAME, "ADS first register value: 0b%s", tmp);
        return 0;
    },
    .argtable = NULL
};

static struct {
    struct arg_int *source;
    struct arg_end *end;
} output_args = {
    .source = arg_int0(
            "d", "data", "<0|1|2|3>", "choose data source from one of "
            "[ADS1299 Raw, ADS1299 Notch, ESP Square, ESP Sine]"),
    .end = arg_end(1)
};

esp_console_cmd_t spi_output = {
    .command = "output",
    .help = "Display or change ESP output data source",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        if (!arg_noerror(argc, argv, (void **) &output_args)) return 1;
        if (output_args.source->count) {
            int source = output_args.source->ival[0];
            if (source < 0 || source > 3) {
                ESP_LOGE(NAME, "Invalid output data source: %d", source);
                return 1;
            }
            output_data = static_cast<spi_output_data>(source);
        }
        ESP_LOGI(NAME, "Current output data: %s", output_data_list[output_data]);
        return 0;
    },
    .argtable = &output_args
};

static struct {
    struct arg_int *freq;
    struct arg_end *end;
} sinfreq_args = {
    .freq = arg_int0(
            "f", "freq", "<int>", "center frequency of generated fake wave"),
    .end = arg_end(1)
};

esp_console_cmd_t spi_sinfreq = {
    .command = "sinfreq",
    .help = "Set/get ESP Sinc fake data frequency",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        if (!arg_noerror(argc, argv, (void **) &sinfreq_args)) return 1;
        if (sinfreq_args.freq->count) {
            sinc_freq = sinfreq_args.freq->ival[0];
        }
        ESP_LOGI(NAME, "Current center frequency: %d", sinc_freq);
        return 0;
    },
    .argtable = &sinfreq_args
};

/******************************************************************************
 * WiFi commands
 */

esp_console_cmd_t wifi_connect = {
    .command = "connect",
    .help = "not implemented yet",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int { return 1; },
    .argtable = NULL
};

esp_console_cmd_t wifi_disconnect = {
    .command = "disconnect",
    .help = "not implemented yet",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int { return 1; },
    .argtable = NULL
};

esp_console_cmd_t wifi_direction = {
    .command = "echoing",
    .help = "Turn on/off serial-to-Wifi direction",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        if (!arg_noerror(argc, argv, (void **) &action_args)) return 1;
        int act = get_action(action_args);
        wifi_echo = act == 0 ? false : (act == 1 ? true : wifi_echo);
        ESP_LOGI(NAME, "Serial-to-wifi echo: %s", wifi_echo ? "ON" : "OFF");
        return 0;
    },
    .argtable = &action_args,
};

/******************************************************************************
 * Power commands
 */

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
    .sleep = arg_str0(NULL, "method", "<light/deep>", "sleep mode"),
    .end = arg_end(4)
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

esp_console_cmd_t power_sleep = {
    .command = "sleep",
    .help = "Turn ESP32 into light/deep sleep mode",
    .hint = NULL,
    .func = [](int argc, char **argv) {
        if (!arg_noerror(argc, argv, (void **) &sleep_args)) return 1;
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
    .argtable = &sleep_args
};

esp_console_cmd_t power_restart = {
    .command = "reboot",
    .help = "Software reset of ESP32",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int { esp_restart(); return 0; },
    .argtable = NULL
};

esp_console_cmd_t power_off = {
    .command = "shutdown",
    .help = "Not Implemented! Cut off power supply of whole EmBCI Board",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        // TODO: pulse GPIO twice
        return 0;
    },
    .argtable = NULL
};

esp_console_cmd_t power_battery = {
    .command = "battery",
    .help = "Print battery capacity level in percent",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int { 
        ESP_LOGW(NAME, "Battery level: %2d%%", get_battery_level());
        return 0;
    },
    .argtable = NULL
};

/******************************************************************************
 * Utilities commands
 */

esp_console_cmd_t utils_verbose = {
    .command = "verbose",
    .help = "Increase verbosity",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int { verbose(); return 0; },
    .argtable = NULL
};

esp_console_cmd_t utils_quiet = {
    .command = "quiet",
    .help = "Decrease verbosity",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int { quiet();   return 0; },
    .argtable = NULL
};

esp_console_cmd_t utils_summary = {
    .command = "summary",
    .help = "Print summary of current status",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int { summary(); return 0; },
    .argtable = NULL
};

esp_console_cmd_t utils_version = {
    .command = "version",
    .help = "Get version of chip and SDK",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int { version_info(); return 0; },
    .argtable = NULL
};

esp_console_cmd_t utils_tasks = {
    .command = "tasks",
    .help = "Get information about running RTOS tasks",
    .hint = NULL,
    .func = [](int argc, char **argv) -> int {
        const size_t task_bytes = 40;
        char *taskstr = (char *)malloc(uxTaskGetNumberOfTasks() * task_bytes);
        if (taskstr == NULL) {
            ESP_LOGE(NAME, "allocation for tasks list failed");
            return 1;
        }
        vTaskList(taskstr);
        ESP_LOGE(NAME, "\nTask Name\tStatus\tPrio\tHWM\tTask#"
#ifdef CONFIG_FREERTOS_VTASKLIST_INCLUDE_COREID
                 "\tAffinity"
#endif
                 "\n%s", taskstr);
        free(taskstr);
        return 0;
    },
    .argtable = NULL
};

/******************************************************************************
 * Register commands and useful functions
 */

void register_commands() {
    ESP_ERROR_CHECK( esp_console_cmd_register(&ads_sample_rate) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&ads_source) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&ads_bias) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&ads_impedance) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&ads_channel) );

    ESP_ERROR_CHECK( esp_console_cmd_register(&spi_clear) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&spi_reset) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&spi_output) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&spi_sinfreq) );

    ESP_ERROR_CHECK( esp_console_cmd_register(&wifi_connect) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&wifi_disconnect) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&wifi_direction) );

    ESP_ERROR_CHECK( esp_console_cmd_register(&power_sleep) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&power_restart) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&power_off) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&power_battery) );

    ESP_ERROR_CHECK( esp_console_cmd_register(&utils_verbose) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&utils_quiet) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&utils_summary) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&utils_version) );
    ESP_ERROR_CHECK( esp_console_cmd_register(&utils_tasks) );
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
    register_commands();
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

// THE END
