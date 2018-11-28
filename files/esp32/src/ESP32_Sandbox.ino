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

/*
 You need to configure `Arduino-Log` lib before compiling in directory
 `${arduino-esp32}/libraries/Arduino-Log`. Lib page @
 https://github.com/thijse/Arduino-Log
*/

#include "ADS1299_ESP32.h"

#include <ArduinoLog.h>
#include <SPI.h>
// #include <WiFi.h>
#include <Arduino.h>
#include <HardwareSerial.h>

// #include "esp_heap_alloc_caps.h"
#include "esp_heap_caps.h"
#include "driver/spi_slave.h"
#include "driver/adc.h"
#include "driver/gpio.h"
#include "driver/rtc_io.h"

// Uncomment line below to disable logging.
// #define DISABLE_LOGGING

#define M_BUFFERSIZ 8192
#define M_BUFFERSIZSPI 256
#define PACKETSIZ 256
#define SLAVESENDTIMEOUT 1000

#define VSPI_SS 5
#define HSPI_SS 15
#define DRDY_PIN 4
#define BLINK_PIN 2
#define ADS_DRDY_PIN 27

#define GPIO_MOSI 23
#define GPIO_MISO 19
#define GPIO_SCLK 18
#define GPIO_CS 5

#define datatyp float

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

enum SpiSlaveStatus{
    idle,
    poll
};

datatyp cqbuf[M_BUFFERSIZ];
datatyp* spibuf;
CyclicQueue<datatyp> *cq;

MillisClock clkgen;
MillisClock clkslavetimeout;
MillisClock clkblink;
MillisClock clkts;

uint32_t timeacc;
uint32_t adsStatusBit;
uint32_t sampfps = 0;
uint32_t sampfpsvi = 0;
uint32_t sampfpsi = 0;
uint32_t sampfpsv = 0;

ADS1299 ads(HSPI, HSPI_SS);

static const int spiClk = 1000000; // 1 MHz

SPIClass * vspi = NULL;

// WiFiClient client;

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

// default log level is NOTICE, here we only use ERROR - VERBOSE
int logLevel = 4;
int minLevel = 2;
int maxLevel = 7;
const char* const logLevelList[] = {
    "SILENT", "FATAL", "ERROR", "WARNING", "NOTICE", "TRACE", "VERBOSE"
};

// Supported sample rates (Hz)
int fsList[7] = {250, 500, 1000, 2000, 4000, 8000, 16000};

SpiSlaveStatus slaveStatus = idle;
spi_slave_transaction_t* t;
esp_err_t ret;

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
    char inchar = Serial.read();
    if (inchar < 'a' || inchar > 'z') return;
    switch(inchar) {
        case 'c':
            cq->clear();
            Log.notice("Queue empty now\n");
            break;
        case 's':
            Log.notice("ADS data header: %B\n", adsStatusBit);
            Log.notice("Valid packets:   %d/%d Hz\n", sampfpsv, sampfps);
            Log.notice("Output data:     %s\n", dataSrcList[dataSrc]);
            Log.notice("Logging level:   %s\n", logLevelList[logLevel]);
            Log.notice("Serial to wifi:  %T\n", wifiEcho);
            break;
        case 'd':
            dataSrc = (dataSrc + 1) % 4;
            Log.notice("Current output data: %s\n", dataSrcList[dataSrc]);
            break;
        case 'm':
            logLevel = max((logLevel - 1), minLevel);
            Log.setLogLevel(logLevel);
            Log.fatal("Current log level: %s\n", logLevelList[logLevel]);
            break;
        case 'v':
            logLevel = min((logLevel + 1), maxLevel);
            Log.setLogLevel(logLevel);
            Log.fatal("Current log level: %s\n", logLevelList[logLevel]);
            break;
        case 'w':
            wifiEcho = !wifiEcho;
            Log.notice("Current serial-to-wifi redirection: %T\n", wifiEcho);
            break;
        case 'r':
            Log.notice("ADS first register value: %B\n", ads.init());
            break;
        case 'h':
            Log.notice("Supported commands:\n");
            Log.notice("\th - print this Help message\n");
            Log.notice("\tc - Clear spi fifo queue\n");
            Log.notice("\td - change esp output Data source\n");
            Log.notice("\ts - print Summary of current status\n");
            Log.notice("\tm - be less verbose (Mute)\n");
            Log.notice("\tv - be more Verbose\n");
            Log.notice("\tw - turn on/off serial-to-Wifi redirection\n");
            Log.notice("\tr - Read ads1299 id register (will reset ads!)\n");
            break;
    }
}

void handleSerial() {
    Log.verbose("Begin processing serial cmd\n");
    if (Serial.available()) {
        handleSerialCommand();
    }
    // if (wifiEcho && client.connected()) {
    //     while (Serial1.available()) {
    //         client.print(Serial1.readStringUntil('\n'));
    //     }
    //     while (client.available()) {
    //         Serial1.print(client.readStringUntil('\n'));
    //     }
    // }
    Log.verbose("End processing serial cmd\n");
}

void handleSpiCommand() {
    if(spibufrecv[0] == 0x00) {
        return;
    } else {
        Log.trace("SPI RECEIVED: ");
        for (int i = 0; i < 128; i++) {
            Log.trace("%x ", spibufrecv[i]);
        }
        Log.trace("\n");
    }
    if (spibufrecv[0] == 0x40) {
        Log.trace("INSTRUCTION: WREG\n");
        switch(spibufrecv[1]) {
            case 0x50:
                Log.trace("REGISTER: SAMPLE RATE: ");
                if (spibufrecv[2] <= 6) {
                    int samplerate = fsList[(uint8_t)spibufrecv[2]];
                    ads.setSampRate(samplerate);
                    Log.trace("SAMPLE RATE SET TO %d\n", samplerate);
                } else {
                    Log.trace("NOT IMPLEMENTED SAMPLERATE %d\n", spibufrecv[2]);
                }
                break;
            case 0x52:
                Log.trace("REGISTER: INPUT SOURCE: ");
                if (spibufrecv[2] == 0x05) {
                    ads.setTestSignal(true);
                    Log.trace("TEST SIGNAL ENABLED\n");
                } else if (spibufrecv[2] == 0x00) {
                    ads.setTestSignal(false);
                    Log.trace("NORMAL SIGNAL ENABLED\n");
                } else {
                    Log.trace("NOT IMPLEMENTED SIGNAL %d\n", spibufrecv[2]);
                }
                break;
            case 0x54:
                Log.trace("REGISTER: BIAS: ");
                if (spibufrecv[2] == 0x01) {
                    ads.setBias(true);
                    Log.trace("BIAS OUTPUT ENABLED\n");
                } else if (spibufrecv[2] == 0x00) {
                    ads.setBias(false);
                    Log.trace("BIAS OUTPUT DISABLED\n");
                } else {
                    Log.trace("NOT IMPLEMENTED BIAS CMD %d\n", spibufrecv[2]);
                }
                break;
            case 0x56:
                Log.trace("REGISTER: IMPEDANCE: ");
                if (spibufrecv[2] == 0x01) {
                    ads.setImpedance(true);
                    Log.trace("IMPEDANCE ENABLED\n");
                } else if (spibufrecv[2] == 0x00) {
                    ads.setImpedance(false);
                    Log.trace("IMPEDANCE DISABLED\n");
                } else {
                    Log.trace("NOT IMPLEMENTED IMPEDANCE CMD %d\n", spibufrecv[2]);
                }
                break;
        }
    } else {
        Log.trace("INSTRUCTION: NOT IMPLEMENTED\n");
    }
}

void handleSPI() {
    Log.verbose("Begin processing SPI\n");
    if (slaveStatus == idle) {
        // Prepare and put data into spi_slave_queue, waiting spi_master to read
        if (cq->len > PACKETSIZ) {
            // SPI slave satatus reset to poll
            slaveStatus = poll;
            // buffer data in queue
            digitalWrite(DRDY_PIN, LOW);
            drdypulsetime = 10;
            for (int i = 0; i < PACKETSIZ; i++) {
                cq->pop(&(spibuf[i]));
            }
            spibufrecv[0] = '\0';
            t->length = sizeof(datatyp) * PACKETSIZ * 8;
            t->trans_len = t->length;
            t->tx_buffer = (char*)spibuf;
            t->rx_buffer = (char*)spibufrecv;
            spi_slave_queue_trans(VSPI_HOST, t, portMAX_DELAY);
            Log.trace("BUFFER USED: %F\n", (float)(cq->len) / M_BUFFERSIZ);
            if (cq->overriden) {
                Log.verbose("BUFFER OVERFLOW\n");
                cq->overriden = false;
            }
            clkslavetimeout.reset();
        }
    } else if (slaveStatus == poll) {
        // Data has not been read by spi_master yet
        if (clkslavetimeout.getdiff() > SLAVESENDTIMEOUT) {
            clkslavetimeout.reset();
            digitalWrite(DRDY_PIN, LOW);
            drdypulsetime = 10;
            Log.trace("SPI TIMED OUT, RESENDING\n");
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
    }
    Log.verbose("End processing SPI\n");
}

void blinkTest() {
    Log.trace("Begin blink test\n");
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
    Log.trace("End blink test\n");
}

void setup() {
    Serial.begin(115200);
    Log.begin(logLevel, &Serial, false);
    Log.notice("ESP32 Firmware 2018.10-EmBCI\n");
    Log.notice("Board:  OrangePi Zero Plus 2\n");
    Log.notice("Shield: EmBCI Rev.A7 Oct 22 2018\n");
    Log.notice("Booting...\n");

    // In `uartSetBaudRate`:
    //     CLK_DIV = (UART_CLK_FREQ(80MHz) << 4) / baudrate
    //     therefore best baudrates:
    //         [100000, 200000, 400000, 500000, 800000...]
    Serial1.begin(500000);
    // WiFi.mode(WIFI_STA);

    pinMode(DRDY_PIN, OUTPUT);
    digitalWrite(DRDY_PIN, HIGH);
    pinMode(BLINK_PIN, OUTPUT);
    digitalWrite(BLINK_PIN, LOW);
    pinMode(ADS_DRDY_PIN, INPUT);

    Log.trace("Init SPI & ADS... ");
    vspi = new SPIClass(VSPI);
    vspi->begin();
    ads.begin();
    delay(10);
    ads.init();
    Log.trace("done\n");

    Log.trace("Begin setup\n");
    spibuf = (datatyp*) heap_caps_malloc(
        sizeof(datatyp) * M_BUFFERSIZSPI, MALLOC_CAP_DMA);
    spibufrecv = (char*) heap_caps_malloc(
        sizeof(datatyp) * M_BUFFERSIZSPI, MALLOC_CAP_DMA);
    t = (spi_slave_transaction_t*) malloc(sizeof(spi_slave_transaction_t*));
    cq = new CyclicQueue<datatyp>(cqbuf,M_BUFFERSIZ);
    for (int i = 0; i < M_BUFFERSIZ; i++) {
        cq->buf[i] = i;
    }
    clkgen.reset();
    clkts.reset();

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

    ret = spi_slave_initialize(VSPI_HOST, &buscfg, &slvcfg, 1);
    if (ret != ESP_OK) {
        Log.error("spi_slave_initialize FAILED!!!\n");
    }

    clkblink.reset();

    Log.trace("End setup\n");
    Log.notice("Press `h` for help message\n");
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
}
