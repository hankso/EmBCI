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

#include <SPI.h>
#include "Arduino.h"
#include "ADS1299_ESP32.h"
#include "HardwareSerial.h"
#include "esp_heap_alloc_caps.h"
#include "driver/spi_slave.h"
#include "driver/adc.h"
#include "driver/gpio.h"
#include "driver/rtc_io.h"

#define DEBUGVERBOSE
#define WAIT_SERIAL while(!Serial.available())

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

#define GPIO_BIT_MASK_XR (1ULL<<GPIO_NUM_32)
#define GPIO_BIT_MASK_YD (1ULL<<GPIO_NUM_33)

#define datatyp float

// FIXME 0: Logging level macros added, change conresponding number to name
#define FATAL 4
#define ERROR 3
#define WARN 2
#define INFO 1
#define DEBUG 0

static const int spiClk = 1000000; // 1 MHz

ADS1299 ads(HSPI, HSPI_SS);

SPIClass * vspi = NULL;

#ifdef DEBUGVERBOSE
    // FIXME 1: change DebugLogger level number and println logic.
    class DebugLogger {
        public:
            int level;
            DebugLogger() {
                level = 0;
            }
            ~DebugLogger() {}
            void println(const char* str, int plevel) {
                if (level >= plevel) {
                    Serial.println(str);
                }
            }
    };
    DebugLogger logger;
#endif


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

char* spibufrecv;

datatyp cqbuf[M_BUFFERSIZ];
datatyp* spibuf;
CyclicQueue<datatyp> *cq;

MillisClock clkgen;
MillisClock clkslavetimeout;
MillisClock clkblink;
MillisClock clkts;

int drdypulsetime = 10;
bool blinkstat = false;

uint32_t timeacc;
uint32_t adsstatusbit;
uint32_t sampfps = 0;
uint32_t sampfpsvi = 0;
uint32_t sampfpsi = 0;
uint32_t sampfpsv = 0;

int tsx, tsy, tsp;

int fakedata = 0;

SpiSlaveStatus spislavestatus = idle;

void my_post_setup_cb (spi_slave_transaction_t *trans) {}

void my_post_trans_cb (spi_slave_transaction_t *trans) {}

spi_slave_transaction_t* t;
esp_err_t ret;

float lastreading;
int transits = 0;
int transitsps = 0;
long wavei = 0;

void getFakeData() {
    //cq->push(sin(millis()/500.));
    //cq->push((float)(millis()%1000));
    //cq->push(0xAC);
    if (digitalRead(ADS_DRDY_PIN) == LOW) {
        float res[8];
        // byte bar[4] = {0x81, 0xAA, 0xAC, 0x02};
        adsstatusbit = ads.readData(res);
        if ((adsstatusbit & 0xF00000) == 0xC00000) {
            wavei++;
            for (int i = 0; i < 8; i++) {
                if (fakedata == 1) {
                    cq->push((float)((wavei / 10) % 100));
                } else if (fakedata == 2) {
                    cq->push(sin(wavei / 10));
                } else if(fakedata == 3) {
                    cq->push(1.0);
                } else {
                    cq->push(res[i]);
                }
                //cq->push(*((float*)bar));
            }
            sampfpsvi++;
            if (fabs(lastreading - res[0]) > 10000.) {
                transits++;
            }
            lastreading = res[0];
        }
    }
}

void handleSerialCommand() {
    if (!Serial.available()) return;
    #ifdef DEBUGVERBOSE
        logger.println("Begin processing serial port", 3);
    #endif
    char inchar = Serial.read();
    if (inchar < 'a' || inchar > 'z') return;
    switch(inchar) {
        case 'c':
            cq->clear();
            Serial.println("Queue empty now.");
            break;
        case 's':
            Serial.print("ADS1299 Status Bit: ");
            Serial.println(adsstatusbit, BIN);
            Serial.print("ADS1299 packet header: ");
            Serial.println(ads.init(), BIN);
            Serial.print("Valid packets: ");
            Serial.print(sampfps);
            Serial.print("/");
            Serial.println(sampfpsv);
            break;
        case 't':
            // TODO 1: add more output info here
            fakedata = (fakedata - 1) % 4;
            break;
        case 'o':
            // TODO 2: and here
            Serial.println(transitsps);
            break;
        #ifdef DEBUGVERBOSE
            case 'v':
                logger.level = (logger.level + 1) % 4;
                break;
        #endif
        case 'h':
            Serial.println("Supported commands:");
            Serial.println("\tc - clear FIFO queue");
            Serial.println("\th - print this help message");
            Serial.println("\ts - print summary of current status");
            Serial.println("\tt - change esp output data source [ads, square, sine, constant]");
            Serial.println("\to - ???");
            Serial.println("\tv - change verbose level [DEBUG, INFO, WARN, ERROR, FATAL, CRITICAL]");
    }
    #ifdef DEBUGVERBOSE
        logger.println("End processing serial port", 3);
    #endif
}

void handleSpiCommand() {
    switch (spibufrecv[0]) {
        case 0x40: // Write Register
            #ifdef DEBUGVERBOSE
                logger.println("INSTRUCTION: WREG", 1);
            #endif
            switch(spibufrecv[1]) {
                case 0x50: // WREG sample rate
                    #ifdef DEBUGVERBOSE
                        logger.println("REGISTER: SAMPLE RATE", 1);
                    #endif
                    switch(spibufrecv[2]) {
                        case 0x06:
                            ads.setSampRate(250);
                            #ifdef DEBUGVERBOSE
                                logger.println("SAMPLE RATE SET TO 250",1);
                            #endif
                            break;
                        case 0x05:
                            ads.setSampRate(500);
                            #ifdef DEBUGVERBOSE
                                logger.println("SAMPLE RATE SET TO 500",1);
                            #endif
                            break;
                        case 0x04:
                            ads.setSampRate(1000);
                            #ifdef DEBUGVERBOSE
                            logger.println("SAMPLE RATE SET TO 1000",1);
                            #endif
                            break;
                        case 0x03:
                            ads.setSampRate(2000);
                            #ifdef DEBUGVERBOSE
                            logger.println("SAMPLE RATE SET TO 2000",1);
                            #endif
                            break;
                        case 0x02:
                            ads.setSampRate(4000);
                            #ifdef DEBUGVERBOSE
                            logger.println("SAMPLE RATE SET TO 4000",1);
                            #endif
                            break;
                        case 0x01:
                            ads.setSampRate(8000);
                            #ifdef DEBUGVERBOSE
                            logger.println("SAMPLE RATE SET TO 8000",1);
                            #endif
                            break;
                        case 0x00:
                            ads.setSampRate(16000);
                            #ifdef DEBUGVERBOSE
                            logger.println("SAMPLE RATE SET TO 16000",1);
                            #endif
                            break;
                        default:
                            #ifdef DEBUGVERBOSE
                            logger.println("NOT IMPLEMENTED",1);
                            #endif
                            break;
                    }
                    break;
                case 0x52: // WREG input source
                    #ifdef DEBUGVERBOSE
                        logger.println("REGISTER: INPUT SOURCE",1);
                    #endif
                    switch (spibufrecv[2]) {
                        case 0x05: // input source: test signal
                            ads.setTestSignal(true);
                            #ifdef DEBUGVERBOSE
                                logger.println("TEST SIGNAL ENABLED",1);
                            #endif
                            break;
                        case 0x00: // input source: normal signal
                            ads.setTestSignal(false);
                            #ifdef DEBUGVERBOSE
                                logger.println("NORMAL SIGNAL ENABLED",1);
                            #endif
                            break;
                        default:
                            #ifdef DEBUGVERBOSE
                                logger.println("NOT IMPLEMENTED",1);
                            #endif
                    }
                    break;
                case 0x54: // WREG bias
                    #ifdef DEBUGVERBOSE
                        logger.println("REGISTER: BIAS",1);
                    #endif
                    switch(spibufrecv[2]) {
                        case 0x01:
                            ads.setBias(true);
                            #ifdef DEBUGVERBOSE
                                logger.println("BIAS ENABLED",1);
                            #endif
                            break;
                        case 0x00:
                            ads.setBias(false);
                            #ifdef DEBUGVERBOSE
                                logger.println("BIAS DISABLED",1);
                            #endif
                            break;
                        default:
                            #ifdef DEBUGVERBOSE
                                logger.println("NOT IMPLEMENTED",1);
                            #endif
                    }
                    break;
                case 0x56: // WREG impedance
                    #ifdef DEBUGVERBOSE
                        logger.println("REGISTER: IMPEDANCE",1);
                    #endif
                    switch(spibufrecv[2]) {
                        case 0x01:
                            ads.setImpedance(true);
                            #ifdef DEBUGVERBOSE
                                logger.println("IMPEDANCE ENABLED",1);
                            #endif
                            break;
                        case 0x00:
                            ads.setImpedance(false);
                            #ifdef DEBUGVERBOSE
                                logger.println("IMPEDANCE DISABLED",1);
                            #endif
                            break;
                        default:
                            #ifdef DEBUGVERBOSE
                                logger.println("NOT IMPLEMENTED",1);
                            #endif
                    }
                    break;
            }
            break;
        default:
            #ifdef DEBUGVERBOSE
                if (spibufrecv[0] != 0x00) {
                    logger.println("INSTRUCTION: NOT IMPLEMENTED", 1);
                }
            #endif
            break;
    }
}

void handleSpiIdle() {
    if (cq->len <= PACKETSIZ) return;

    // SPI slave satatus reset to poll
    spislavestatus = poll;

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
    spi_slave_queue_trans(VSPI_HOST,t,portMAX_DELAY);
    #ifdef DEBUGVERBOSE
        if (logger.level >= 1) {
            Serial.print("BUFFER USED: ");
            Serial.println((float)((float)(cq->len)) / M_BUFFERSIZ);
        }
        if (cq->overriden) {
            logger.println("BUFFER OVERFLOW", 1);
            cq->overriden = false;
        }
    #endif
    clkslavetimeout.reset();
}

void handleSpiPoll() {
    // test timeout
    if (clkslavetimeout.getdiff() > SLAVESENDTIMEOUT) {
        clkslavetimeout.reset();
        digitalWrite(DRDY_PIN, LOW);
        drdypulsetime = 10;
        #ifdef DEBUGVERBOSE
            logger.println("SPI TIMED OUT, RESENDING", 1);
        #endif
    }

    if (spi_slave_get_trans_result(VSPI_HOST, &t, 0) == ESP_ERR_TIMEOUT) {
        return;
    }
    // SPI slave status set back to idle
    spislavestatus = idle;

    for (int i = 0; i < 128; i++) {
        spibufrecv[i] /= 2;
    }
    #ifdef DEBUGVERBOSE
        if(spibufrecv[0] != 0x00){
            logger.println("SPI RECEIVED (first 3 bytes)", 1);
            if (logger.level >= 1) {
                for (int i = 0; i < 128; i++) {
                    Serial.print((int)spibufrecv[i]);
                    Serial.print(" ");
                }
                Serial.println(" ");
            }
        }
        /*
        logger.println("SPI RECEIVED", 1);
        if (logger.level >= 1) {
            Serial.println(spibufrecv);
        }
        */
    #endif
}

void handleSPI() {
    #ifdef DEBUGVERBOSE
        logger.println("Begin processing SPI", 3);
    #endif
    if (spislavestatus == idle) {
        handleSpiIdle();
    } else if (spislavestatus == poll) {
        handleSpiPoll();
        handleSpiCommand();
    }
    #ifdef DEBUGVERBOSE
        logger.println("End processing SPI", 3);
    #endif
}

void blinkTest() {
    #ifdef DEBUGVERBOSE
        logger.println("Begin blink test", 3);
    #endif
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
    #ifdef DEBUGVERBOSE
        logger.println("End blink test", 3);
    #endif
}

void setup() {
    Serial.begin(115200);
    Serial.println("ESP32 Firmware 2018.10-EmBCI");
    Serial.println("Board:\tOrangePi Zero Plus 2");
    Serial.println("Shield:\tEmBCI Rev.A7 Oct 22 2018");
    Serial.println("Booting...");
    pinMode(DRDY_PIN, OUTPUT);
    digitalWrite(DRDY_PIN, HIGH);
    pinMode(BLINK_PIN, OUTPUT);
    digitalWrite(BLINK_PIN, LOW);
    pinMode(ADS_DRDY_PIN, INPUT);
    vspi = new SPIClass(VSPI);
    vspi->begin();
    ads.begin();
    delay(10);
    #ifdef DEBUGVERBOSE
        logger.println("Begin setup", 3);
    #endif
    // FIXME 2: warning: 'void* pvPortMallocCaps(size_t, uint32_t)' is deprecated
    spibuf = (datatyp*) pvPortMallocCaps(sizeof(datatyp) * M_BUFFERSIZSPI, MALLOC_CAP_DMA);
    spibufrecv = (char*) pvPortMallocCaps(sizeof(datatyp) * M_BUFFERSIZSPI, MALLOC_CAP_DMA);
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
    //assert(ret==ESP_OK);
    if (ret != ESP_OK) {
        Serial.println("ERROR: spi_slave_initialize FAILED!!!");
    }

    clkblink.reset();
    #ifdef DEBUGVERBOSE
        logger.println("End setup", 3);
    #endif
}

void loop() {
    // blinkTest();

    handleSerialCommand();

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
        transitsps = transits;
        transits = 0;
        clkgen.reset();
    }

    getFakeData();

    sampfpsi++;
}

// #ifdef DEBUGVERBOSE
//   logger.println("Begin data generation",3);
// #endif
//   //generate fake data
//   const int32_t sampdelta=4;
//   timeacc+=clkgen.update();
//   while(timeacc>=sampdelta){
//     getFakeData();
//     timeacc-=sampdelta;
//   }
// #ifdef DEBUGVERBOSE
//   logger.println("End data generation",3);
// #endif
