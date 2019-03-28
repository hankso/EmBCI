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

#ifndef ESP32_Sandbox_h
#define ESP32_Sandbox_h

// local headers
#include "ADS1299_ESP32.h"

// Arduino core @ ${ARDUINO_ESP32}/cores/esp32
#include "Arduino.h"

// Arduino third-party lib @ ${ARDUINO_ESP32}/libraries
#include <SPI.h>
#include <WiFi.h>

// ESP-IDF SDK @ ${ESP_IDF}/components && ${ARDUINO_ESP32}/tools/sdk/include
#include "esp_log.h"
#include "esp_sleep.h"
#include "esp_vfs_dev.h"
#include "esp_task_wdt.h"
#include "esp_heap_caps.h"
#include "driver/spi_slave.h"
#include "driver/gpio.h"
#include "driver/uart.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#ifdef LOG_LOCAL_LEVEL
    #undef LOG_LOCAL_LEVEL
    #define LOG_LOCAL_LEVEL ESP_LOG_VERBOSE
    // #define LOGLOCAL_LEVEL ESP_LOG_NONE
#endif

#define M_BUFFERSIZE     8192
#define M_BUFFERSIZESPI  256
#define PACKETSIZE       256
#define SLAVESENDTIMEOUT 1000

#define VSPI_SS          5
#define HSPI_SS          15
#define DRDY_PIN         4
#define BLINK_PIN        2
#define ADS_DRDY_PIN     27

#define GPIO_MOSI        23
#define GPIO_MISO        19
#define GPIO_SCLK        18
#define GPIO_CS          5

#define GPIO_WAKEUP      0
#define UART_CONSOLE     UART_NUM_0
#define UART_BAUDRATE    115200
#define CLK_SPI          1000000

#define bufftype float

/* Constants */
const char *NAME = "EmBCI";
const char *prompt = "EmBCI> ";

ADS1299 ads(HSPI, HSPI_SS);

enum spi_data_source {
    ADS_RAW,
    ESP_SQUARE,
    ESP_SINE,
    ESP_CONST,
} data_source = ADS_RAW;

const char* const data_source_list[] = {
    "ADS1299 Float32 Raw Wave",
    "ESP Generated Square Wave",
    "ESP Generated Sine Wave",
    "Constant 1.0"
};

enum spi_slave_status {
    IDLE, 
    POLL
} slave_status = IDLE;

esp_log_level_t log_level = ESP_LOG_INFO;
const int log_level_min = 0, log_level_max = 5;
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

bool wifi_echo = false;

/* Utilities */
// 170 --> 0b"10101010"
char* itobs(int n, char *buff, int bits=8) {
    buff += bits;
    *buff-- = '\0';
    while (bits--) {
        *buff-- = (n & 1) + '0';
        n >>= 1;
    }
    return buff;
}

template<typename T>
class CyclicQueue {
    public:
        T *buf;
        uint32_t buffersiz;
        bool overriden = false;
        uint32_t sp, ep;
        int32_t len = 0;
        CyclicQueue(T *bp, uint32_t siz) {
            buf = bp;
            buffersiz = siz;
            clear();
        }
        void clear() {
            sp = 0;
            ep = 0;
            len = 0;
            for (uint32_t i = 0; i < buffersiz; i++) {
                buf[i] = 0;
            }
        }
        bool push(T val) {
            buf[sp] = val;
            sp = (sp + 1) % buffersiz;
            if (sp == ep) {
                overriden = true;
                ep = (ep + 1) % buffersiz;
                return false;
            } else {
                len++;
                return true;
            }
        }
        bool pop(T *val) {
            if (ep == sp) {
                return true;
            } else {
                *val = buf[ep];
                ep = (ep + 1) % buffersiz;
                len--;
                return false;
            }
        }
};

CyclicQueue<bufftype> *cq;

class MillisClock {
    public:
        uint32_t lasttime;
        void reset() {
            lasttime = millis();
        }
        uint32_t getdiff() {
            int32_t diff = millis() - lasttime;
            if (diff > 0) {
                return diff;
            } else {
                reset();
                return 0;
            }
        }
        uint32_t update() {
            int32_t diff = millis() - lasttime;
            reset();
            if (diff > 0) {
                return diff;
            } else {
                return 0;
            }
        }
};

MillisClock
    clkts,
    clkgen,
    // clkblink,
    clkslavetimeout;

class Counter {
    private:
        uint32_t
            length = 5,
            *counters = (uint32_t *)calloc(length, sizeof(uint32_t)),
            *freezers = (uint32_t *)calloc(length, sizeof(uint32_t));
    public:
        void count(uint16_t index = 0) {
            if (index >= length) {
                uint32_t
                    *tmp1 = (uint32_t *)realloc(counters, (index + 5) * sizeof(uint32_t)),
                    *tmp2 = (uint32_t *)realloc(freezers, (index + 5) * sizeof(uint32_t));
                if (tmp1 != NULL && tmp2 != NULL) {
                    counters = tmp1;
                    freezers = tmp2;
                    length = index + 5;
                } else {
                    ESP_LOGE(NAME, "Error (re)allocating memory");
                    return;
                }
            }
            counters[index]++;
        }
        void reset() {
            for (int i = 0; i < length; i++) {
                counters[i] = 0;
            }
        }
        void freeze() {
            memcpy(freezers, counters, length);
        }
        uint32_t value(uint16_t index) {
            if (index < length) {
                return freezers[index];
            }
            return 0;
        }
};

Counter counter;

#endif // ESP32_Sandbox_h
