/*
 File: globals.h
 Author: Hankso
 Webpage: http://github.com/hankso
 Time: Sat 20 Apr 2019 00:34:02 CST
 
 Global variables are declared here.
 
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
