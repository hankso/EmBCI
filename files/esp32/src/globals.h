/*
 * File: globals.h
 * Authors: Hank <hankso1106@gmail.com>
 * Create: 2019-04-20 00:34:02
 *
 * Copyright (c) 2019 EmBCI. All right reserved.
 *
 * Variables declared here are global to all source files in project.
*/

#ifndef GLOBALS_H
#define GLOBALS_H

#include "ADS1299_ESP32.h"

#include "esp_log.h"

extern const char *NAME, *prompt;
extern ADS1299 ads;
extern bool wifi_echo;
extern esp_log_level_t log_level;
extern const int log_level_min, log_level_max;
extern uint32_t sinc_freq;

enum spi_output_data {
    ADS_RAW,
    ADS_NOTCH,
    ESP_SQUARE,
    ESP_SINE,
} extern output_data;

enum spi_slave_status {
    IDLE, 
    POLL
} extern slave_status;

extern const char* const output_data_list[];
extern const char* const log_level_list[];
extern const char* const wakeup_reason_list[];
extern const int sample_rate_list[];

extern void verbose();
extern void quiet();
extern void set_sample_rate(uint32_t);
extern void clear_fifo_queue();
extern void version_info();
extern void summary();
extern int get_battery_level(int times = 8);

#endif // GLOBALS_H
