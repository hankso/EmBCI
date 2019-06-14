/*
 File: ESP32_Sandbox.h
 Author: Hankso
 Webpage: http://github.com/hankso
 Time: Tue 19 Mar 2019 17:59:58 CST

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

#ifndef ESP32_SANDBOX_H
#define ESP32_SANDBOX_H

// local headers
#include "globals.h"
#include "configs.h"
#include "utils.h"
#include "console_cmds.h"

// Arduino core @ ${ARDUINO_ESP32}/cores/esp32
#include "Arduino.h"

// Arduino third-party lib @ ${ARDUINO_ESP32}/libraries
#include <SPI.h>
#include <WiFi.h>

// ESP-IDF SDK @ ${ESP_IDF}/components && ${ARDUINO_ESP32}/tools/sdk/include
#include "esp_log.h"
#include "esp_system.h"
#include "esp_vfs_dev.h"
#include "esp_spi_flash.h"
#include "esp_task_wdt.h"
#include "esp_heap_caps.h"
#include "driver/adc.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "driver/spi_slave.h"
#include "freertos/task.h"
#include "freertos/FreeRTOS.h"

#ifdef LOG_LOCAL_LEVEL
    #undef LOG_LOCAL_LEVEL
    #define LOG_LOCAL_LEVEL ESP_LOG_VERBOSE
    // #define LOGLOCAL_LEVEL ESP_LOG_NONE
#endif

/******************************************************************************
 * Global variables definition
 */

ADS1299 ads = ADS1299(HSPI, GPIO_CS);

bool wifi_echo = WIFI_ECHO;

esp_log_level_t log_level = LOG_LEVEL;

const int log_level_min = 0, log_level_max = 5;

spi_output_data output_data = ADS_RAW;

spi_slave_status slave_status = IDLE;

CyclicQueue<bufftype> *cq;

MillisClock
    clkts,
    clkgen,
    clkblink,
    clkslavetimeout;

Counter counter;

const char *NAME = "EmBCI";

const char *prompt = "EmBCI> ";

/******************************************************************************
 * Constants
 */

const char* const output_data_list[] = {
    "ADS1299 Float32 Raw Wave",
    "ESP Generated Square Wave",
    "ESP Generated Sine Wave",
    "Constant 1.0"
};

const char* const log_level_list[] = {
    "SILENT", "ERROR", "WARNING", "INFO", "DEBUG", "VERBOSE",
};

const char* const wakeup_reason_list[] = {
    "Undefined", "Undefined", "EXT0", "EXT1", 
    "Timer", "Touchpad", "ULP", "GPIO", "UART",
};

const int sample_rate_list[] = {
    250, 500, 1000, 2000, 4000, 8000, 16000
};

/******************************************************************************
 * Functions
 */

void verbose() {
    log_level = esp_log_level_t( min((log_level + 1), log_level_max) );
    esp_log_level_set(NAME, log_level);
    ESP_LOGE(NAME, "Current log level: %s", log_level_list[log_level]);
}

void quiet() {
    log_level = esp_log_level_t( max((log_level - 1), log_level_min) );
    esp_log_level_set(NAME, log_level);
    ESP_LOGE(NAME, "Current log level: %s", log_level_list[log_level]);
}

void set_sample_rate(uint32_t rate_or_index) {
    uint32_t fs = 0;
    if (rate_or_index < 7) {
        fs = sample_rate_list[rate_or_index];
    } else {
        for (uint8_t i = 0; i < 7; i++) {
            if (sample_rate_list[i] == rate_or_index) {
                fs = sample_rate_list[i]; break;
            }
        }
    }
    if (fs) {
        ads.setSampleRate(fs);
        ESP_LOGD(NAME, "SAMPLE RATE SET TO %d", fs);
    } else {
        ESP_LOGE(NAME, "NOT IMPLEMENTED SAMPLERATE %d", rate_or_index);
    }
}

void clear_fifo_queue() {
    cq->clear();
    float bufrate = (float)(cq->len) / M_BUFFERSIZE;
    ESP_LOGD(NAME, "ESP buffer used:  %.2f%%", bufrate * 100);
}

void version_info() {
    esp_chip_info_t info;
    esp_chip_info(&info);
    ESP_LOGE(NAME, "IDF Version: %s", esp_get_idf_version());
    ESP_LOGE(NAME, "Chip info:");
    ESP_LOGE(NAME, "\tmodel: %s", info.model == CHIP_ESP32 ? "ESP32" : "???");
    ESP_LOGE(NAME, "\tcores: %d", info.cores);
    ESP_LOGE(NAME, "\tfeature: %s%s%s/%s-Flash: %d MB", 
        info.features & CHIP_FEATURE_WIFI_BGN ? "/802.11bgn" : "",
        info.features & CHIP_FEATURE_BLE ? "/BLE" : "",
        info.features & CHIP_FEATURE_BT ? "/BT" : "",
        info.features & CHIP_FEATURE_EMB_FLASH ? "Embedded" : "External",
        spi_flash_get_chip_size() / (1024 * 1024));
    ESP_LOGE(NAME, "\trevision number: %d", info.revision);
    ESP_LOGE(NAME, "Firmware Version: 2019.4-EmBCI");
    ESP_LOGE(NAME, "ARM Board: OrangePi Zero Plus 2");
    ESP_LOGE(NAME, "EmBCI Shield: EmBCI Rev.B1 Apr 12 2019");
}

int get_battery_level(int times) {
    long value = 0;
    for (int i = 0; i < times; i++) {
        value += adc1_get_raw(ADC1_CHANNEL_5);
    }
    value /= times;  // average filter
    double percent;
    if (value > 3490) {
        percent = 60.0 + (value - 3490) / 10.475;
    }
    else if (value > 3398) {
        percent = 10.0 + (value - 3398) / 1.84;
    }
    else {
        percent = (value - 3258) / 104.0;
    }
    return max(0, min((int)percent, 100));
}


void summary() {
    char tmp[8 + 1];
    itoa(ads.statusBit, tmp, 2);
    const char *bias = ads.getBias() ? "ON" : "OFF";
    const char *imped = ads.getImpedance() ? "ON" : "OFF";
    uint32_t v0 = counter.value(0), v1 = counter.value(1);
    float bufrate = (float)(cq->len) / M_BUFFERSIZE;
    ESP_LOGW(NAME, "ADS data header:  0b%s", tmp);
    ESP_LOGW(NAME, "ADS data source:  %s", ads.getDataSource());
    ESP_LOGW(NAME, "ADS sample rate:  %d Hz", ads.getSampleRate());
    ESP_LOGW(NAME, "ADS BIAS | IMPED: %s | %s", bias, imped);
    ESP_LOGW(NAME, "ESP valid packet: %d / %d Hz", v1, v0);
    ESP_LOGW(NAME, "ESP output data:  %s", output_data_list[output_data]);
    ESP_LOGW(NAME, "ESP buffer used:  %.2f%%", bufrate * 100);
    ESP_LOGW(NAME, "ESP log level:    %s", log_level_list[log_level]);
    ESP_LOGW(NAME, "Serial to wifi:   %s", wifi_echo ? "ON" : "OFF");
    ESP_LOGW(NAME, "Battery level:    %d%%", get_battery_level(5));
}

#endif // ESP32_SANDBOX_H
