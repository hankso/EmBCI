/*
 File: ESP32_Sandbox.ino

 This file is ESP32 firmware source code used in EmBCI.

 Created by Song Tian Cheng, September 2018
 Page @ http://github.com/rotom407

 Modified by Gao Han Lin, October 2018
 Page @ http://github.com/hankso

 Copyright (c) 2018 EmBCI. All right reserved.

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

// local headers
#include "ADS1299_ESP32.h"

// Arduino core @ ${ARDUINO_ESP32}/cores/esp32
#include "Arduino.h"
#include "HardwareSerial.h"

// Arduino third-party lib @ ${ARDUINO_ESP32}/libraries
#include <SPI.h>
#include <WiFi.h>

// ESP-IDF SDK @ ${ESP_IDF}/components && ${ARDUINO_ESP32}/tools/sdk/include
#include "esp_log.h"
#include "esp_task_wdt.h"
#include "esp_heap_caps.h"
#include "driver/spi_slave.h"
#include "driver/gpio.h"
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

#define datatype float

#define btos(bool) (bool ? "True" : "False")

// char* itobs(n, char* ret="") {
//     if (!n) { return ret + "\0"; }
//     return itobs(n >> 1, ret + (n & 1 ? "1" : "0"));
// }

template<typename T>
class CyclicQueue {
    public:
        T *buf;
        uint32_t buffersiz;
        bool overriden = false;
        uint32_t sp, ep;
        int32_t len = 0;
        CyclicQueue(T* bp, uint32_t siz) {
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
        bool pop(T* val) {
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

enum SpiSlaveStatus{idle, poll} slaveStatus = idle;

uint32_t timeacc;
uint32_t adsStatusBit;
uint32_t sampfps = 0;
uint32_t sampfpsvi = 0;
uint32_t sampfpsi = 0;
uint32_t sampfpsv = 0;

static const int spiClk = 1000000; // 1 MHz
static const char *NAME = "EmBCI";

int drdypulsetime = 10;
long wavei = 0;
char* spibufrecv;
bool blinkstat = false;
bool wifiEcho = true;

int dataSrc = 0;
const char* const dataSrcList[] = {
    "ADS1299 Float32 Raw Wave",
    "ESP Generated Square Wave",
    "ESP Generated Sine Wave",
    "Constant 1.0"
};

esp_log_level_t logLevel = ESP_LOG_INFO;
int minLevel = 0, maxLevel = 6;
const char* const logLevelList[] = {
    "SILENT", "ERROR", "WARNING", "INFO", "DEBUG", "VERBOSE",
};

// Supported sample rates (Hz)
int fsList[] = {250, 500, 1000, 2000, 4000, 8000, 16000};

ADS1299 ads(HSPI, HSPI_SS);
SPIClass * vspi = NULL;
WiFiClient client;

datatype cqbuf[M_BUFFERSIZE];
datatype* spibuf;
CyclicQueue<datatype> *cq;

MillisClock clkgen;
MillisClock clkslavetimeout;
MillisClock clkblink;
MillisClock clkts;

spi_slave_transaction_t* t;

void my_post_setup_cb (spi_slave_transaction_t *trans) {}

void my_post_trans_cb (spi_slave_transaction_t *trans) {}

void sendToSPI() {
    // wait until ADS1299 DRDY pin fall down, why not use interrupt?
    if (digitalRead(ADS_DRDY_PIN) == HIGH) return;
    float res[8];
    adsStatusBit = ads.readData(res);
    if ((adsStatusBit & 0xF00000) != 0xC00000) return;
    for (int i = 0; i < 8; i++) {
        if (dataSrc == 1) {
            cq->push((float)((wavei / 10) % 100));
            wavei++;
        } else if (dataSrc == 2) {
            cq->push(sin(wavei / 10));
            wavei++;
        } else if(dataSrc == 3) {
            cq->push(1.0);
        } else {
            cq->push(res[i]);
        }
    }
    sampfpsvi++;
}

void handleSerialCommand() {
    ESP_LOGV(NAME, "Begin processing serial cmd");
    char inchar = Serial.read();
    if (inchar < 'a' || inchar > 'z') return;
    switch(inchar) {
        case 'c':
            cq->clear();
            ESP_LOGD(NAME, "Queue empty now");
            break;
        case 's':
            ESP_LOGI(NAME, "ADS data header: 0x%02X", adsStatusBit);
            ESP_LOGI(NAME, "Valid packets:   %d/%d Hz", sampfpsv, sampfps);
            ESP_LOGI(NAME, "Output data:     %s", dataSrcList[dataSrc]);
            ESP_LOGI(NAME, "Logging level:   %s", logLevelList[logLevel]);
            ESP_LOGI(NAME, "Serial to wifi:  %s", btos(wifiEcho));
            break;
        case 'd':
            dataSrc = (dataSrc + 1) % 4;
            ESP_LOGD(NAME, "Current output data: %s", dataSrcList[dataSrc]);
            break;
        case 'm':
            logLevel = esp_log_level_t( max((logLevel - 1), minLevel) );
            esp_log_level_set(NAME, logLevel);
            ESP_LOGW(NAME, "Current log level: %s", logLevelList[logLevel]);
            break;
        case 'v':
            logLevel = esp_log_level_t( max((logLevel + 1), minLevel) );
            esp_log_level_set(NAME, logLevel);
            ESP_LOGW(NAME, "Current log level: %s", logLevelList[logLevel]);
            break;
        case 'w':
            wifiEcho = !wifiEcho;
            ESP_LOGD(NAME, "Serial-to-wifi redirection: %s", btos(wifiEcho));
            break;
        case 'r':
            ESP_LOGI(NAME, "ADS first register value: 0x%02X", ads.init());
            break;
        case 'h':
            ESP_LOGW(NAME, "Supported commands:");
            ESP_LOGW(NAME, "\th - print this Help message");
            ESP_LOGW(NAME, "\tc - Clear spi fifo queue");
            ESP_LOGW(NAME, "\td - change esp output Data source");
            ESP_LOGW(NAME, "\ts - print Summary of current status");
            ESP_LOGW(NAME, "\tm - be less verbose (Mute)");
            ESP_LOGW(NAME, "\tv - be more Verbose");
            ESP_LOGW(NAME, "\tw - turn on/off serial-to-Wifi redirection");
            ESP_LOGW(NAME, "\tr - Read ads1299 id register (will reset ads!)");
            break;
        default:
            ESP_LOGE(NAME, "%c: command not supported", inchar);
    }
    ESP_LOGV(NAME, "End processing serial cmd");
}

void handleSerial() {
    if (Serial.available()) {
        handleSerialCommand();
    }
    if (wifiEcho && client.connected()) {
        ESP_LOGI(NAME, "Redirecting Serial1 to WiFi client.");
        return;
        while (Serial1.available()) {
            client.print(Serial1.readStringUntil('\n'));
        }
        while (client.available()) {
            Serial1.print(client.readStringUntil('\n'));
        }
    }
}

void handleSpiCommand() {
    ESP_LOGV(NAME, "Begin processing SPI");
    if(spibufrecv[0] == 0x00) {
        return;
    } else {
        char tmp[384+1];
        tmp[384] = 0;
        for (int i = 0; i < 128; i++) {
            snprintf(tmp + 3*i, 4, "%02X ", spibufrecv[i]);
        }
        ESP_LOGD(NAME, "SPI RECEIVED: %s", tmp);
    }
    if (spibufrecv[0] == 0x40) {
        ESP_LOGD(NAME, "INSTRUCTION: WREG");
        switch(spibufrecv[1]) {
            case 0x50:
                ESP_LOGD(NAME, "REGISTER: SAMPLE RATE: ");
                if (spibufrecv[2] <= 6) {
                    int samplerate = fsList[(uint8_t)spibufrecv[2]];
                    ads.setSampRate(samplerate);
                    ESP_LOGD(NAME, "SAMPLE RATE SET TO %d", samplerate);
                } else {
                    ESP_LOGD(NAME, "NOT IMPLEMENTED SAMPLERATE %d", spibufrecv[2]);
                }
                break;
            case 0x52:
                ESP_LOGD(NAME, "REGISTER: INPUT SOURCE: ");
                if (spibufrecv[2] == 0x05) {
                    ads.setTestSignal(true);
                    ESP_LOGD(NAME, "TEST SIGNAL ENABLED");
                } else if (spibufrecv[2] == 0x00) {
                    ads.setTestSignal(false);
                    ESP_LOGD(NAME, "NORMAL SIGNAL ENABLED");
                } else {
                    ESP_LOGD(NAME, "NOT IMPLEMENTED SIGNAL %d", spibufrecv[2]);
                }
                break;
            case 0x54:
                ESP_LOGD(NAME, "REGISTER: BIAS: ");
                if (spibufrecv[2] == 0x01) {
                    ads.setBias(true);
                    ESP_LOGD(NAME, "BIAS OUTPUT ENABLED");
                } else if (spibufrecv[2] == 0x00) {
                    ads.setBias(false);
                    ESP_LOGD(NAME, "BIAS OUTPUT DISABLED");
                } else {
                    ESP_LOGD(NAME, "NOT IMPLEMENTED BIAS CMD %d", spibufrecv[2]);
                }
                break;
            case 0x56:
                ESP_LOGD(NAME, "REGISTER: IMPEDANCE: ");
                if (spibufrecv[2] == 0x01) {
                    ads.setImpedance(true);
                    ESP_LOGD(NAME, "IMPEDANCE ENABLED");
                } else if (spibufrecv[2] == 0x00) {
                    ads.setImpedance(false);
                    ESP_LOGD(NAME, "IMPEDANCE DISABLED");
                } else {
                    ESP_LOGD(NAME, "NOT IMPLEMENTED IMPEDANCE CMD %d", spibufrecv[2]);
                }
                break;
        }
    } else {
        ESP_LOGD(NAME, "INSTRUCTION: NOT IMPLEMENTED");
    }
    ESP_LOGV(NAME, "End processing SPI");
}

void handleSPI() {
    switch (slaveStatus) {
        case idle:
            // Put data into spi_slave_queue, waiting spi_master to read
            if (cq->len > PACKETSIZE) {
                // SPI slave satatus reset to poll
                slaveStatus = poll;
                // buffer data in queue
                digitalWrite(DRDY_PIN, LOW);
                drdypulsetime = 10;
                for (int i = 0; i < PACKETSIZE; i++) {
                    cq->pop(&(spibuf[i]));
                }
                spibufrecv[0] = '\0';
                t->length = sizeof(datatype) * PACKETSIZE * 8;
                t->trans_len = t->length;
                t->tx_buffer = (char*)spibuf;
                t->rx_buffer = (char*)spibufrecv;
                spi_slave_queue_trans(VSPI_HOST, t, portMAX_DELAY);
                ESP_LOGV(NAME, "BUFFER USED: %F", (float)(cq->len) / M_BUFFERSIZE);
                if (cq->overriden) {
                    ESP_LOGD(NAME, "BUFFER OVERFLOW");
                    cq->overriden = false;
                }
                clkslavetimeout.reset();
            }
            break;
        case poll:
            // Data has not been read by spi_master yet
            if (clkslavetimeout.getdiff() > SLAVESENDTIMEOUT) {
                clkslavetimeout.reset();
                digitalWrite(DRDY_PIN, LOW);
                drdypulsetime = 10;
                ESP_LOGV(NAME, "SPI TIMED OUT, RESENDING");
            }
            if (spi_slave_get_trans_result(VSPI_HOST, &t, 0) != ESP_ERR_TIMEOUT) {
                // Spi_master read data, set spi_slave status back to idle
                slaveStatus = idle;

                // FIXME 1:
                // We HAVE TO add this because of spi transcation error between
                // ESP32 and OrangePi. This maybe solved in future hardware design.
                for (int i = 0; i < 128; i++) {
                    spibufrecv[i] /= 2;
                }

                handleSpiCommand();
            }
            break;
    }
}

void blinkTest() {
    ESP_LOGV(NAME, "Begin blink test");
    if (clkblink.getdiff() >= 1000) {
        clkblink.reset();
        if (blinkstat == true) {
            digitalWrite(BLINK_PIN, HIGH);
            blinkstat = false;
        } else {
            digitalWrite(BLINK_PIN, LOW);
            blinkstat = true;
        }
    }
    ESP_LOGV(NAME, "End blink test");
}

void setup() {
    ESP_LOGD(NAME, "ESP32 Firmware 2018.10-EmBCI");
    ESP_LOGD(NAME, "Board:  OrangePi Zero Plus 2");
    ESP_LOGD(NAME, "Shield: EmBCI Rev.A7 Oct 22 2018");
    ESP_LOGD(NAME, "Booting...");

#ifdef CONFIG_TASK_WDT
    if (esp_task_wdt_add(NULL) == ESP_OK && \
        esp_task_wdt_status(NULL) == ESP_OK) {
        ESP_LOGI(NAME, "Task loopTask @ CPU1 subscribed to TWDT");
    }
    if (esp_task_wdt_delete(xTaskGetIdleTaskHandleForCPU(1)) == ESP_OK) {
        ESP_LOGI(NAME, "Task IDLE1 @ CPU1 unsubscribed from TWDT");
    }
#endif

    ESP_LOGD(NAME, "Init Serial... ");
    // In `uartSetBaudRate`:
    //     CLK_DIV = (UART_CLK_FREQ(80MHz) << 4) / baudrate
    //     therefore best baudrates:
    //         [100000, 200000, 400000, 500000, 800000...]
    Serial.begin(115200);
    Serial1.begin(500000);
    ESP_LOGD(NAME, "done");

    ESP_LOGD(NAME, "Init GPIO... ");
    pinMode(DRDY_PIN, OUTPUT);
    digitalWrite(DRDY_PIN, HIGH);
    pinMode(BLINK_PIN, OUTPUT);
    digitalWrite(BLINK_PIN, LOW);
    pinMode(ADS_DRDY_PIN, INPUT);
    ESP_LOGD(NAME, "done");

    ESP_LOGD(NAME, "Init SPI... ");
    vspi = new SPIClass(VSPI);
    vspi->begin();
    ESP_LOGD(NAME, "done");

    ESP_LOGD(NAME, "Init WiFi... ");
    WiFi.mode(WIFI_STA);
    ESP_LOGD(NAME, "done");

    ESP_LOGD(NAME, "Init ADS... ");
    ads.begin();
    delay(10);
    ads.init();
    ESP_LOGD(NAME, "done");


    ESP_LOGD(NAME, "Begin setup");
    spibuf = (datatype*) heap_caps_malloc(
        sizeof(datatype) * M_BUFFERSIZESPI, MALLOC_CAP_DMA);
    spibufrecv = (char*) heap_caps_malloc(
        sizeof(datatype) * M_BUFFERSIZESPI, MALLOC_CAP_DMA);
    t = (spi_slave_transaction_t*) malloc(sizeof(spi_slave_transaction_t*));
    cq = new CyclicQueue<datatype>(cqbuf,M_BUFFERSIZE);
    for (int i = 0; i < M_BUFFERSIZE; i++) {
        cq->buf[i] = i;
    }

    clkgen.reset();
    clkts.reset();
    clkblink.reset();

    spi_bus_config_t buscfg;
    buscfg.mosi_io_num = GPIO_MOSI;
    buscfg.miso_io_num = GPIO_MISO;
    buscfg.sclk_io_num = GPIO_SCLK;

    spi_slave_interface_config_t slvcfg;
    slvcfg.mode = 0;
    slvcfg.spics_io_num = GPIO_CS;
    slvcfg.queue_size = 3;
    slvcfg.flags = 0;
    slvcfg.post_setup_cb = my_post_setup_cb;
    slvcfg.post_trans_cb = my_post_trans_cb;

    if (spi_slave_initialize(VSPI_HOST, &buscfg, &slvcfg, 1) != ESP_OK) {
        ESP_LOGE(NAME, "spi_slave_initialize FAILED!!!");
    }

    ESP_LOGD(NAME, "End setup");
    ESP_LOGI(NAME, "Press `h` for help message");
}

void loop() {
    sendToSPI();
    sampfpsi++;

    // blinkTest();

    handleSerial();

    handleSPI();

    if (drdypulsetime <= 0) {
        digitalWrite(DRDY_PIN, HIGH);
    } else {
        drdypulsetime--;
    }

    if (clkgen.getdiff() > 1000) {
        sampfps = sampfpsi;
        sampfpsv = sampfpsvi;
        sampfpsi = 0;
        sampfpsvi = 0;
        clkgen.reset();
    }
#ifdef CONFIG_TASK_WDT
    esp_task_wdt_reset();
#endif
}
