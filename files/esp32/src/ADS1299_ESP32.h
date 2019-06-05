/*
 File: ADS1299_ESP32.h
 Author: SONG Tian-Cheng, September 2018
 Webpage: http://github.com/rotom407
 Time: Tue 19 Mar 2019 17:59:58 CST

 Rewritten for EmBCI by Hankso and Song TC 2019.
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

#ifndef ADS1299_ESP32_h
#define ADS1299_ESP32_h


#include <SPI.h>
#include "Arduino.h"

/* Commands */
#define ADS_WAKEUP      0x02
#define ADS_STANDBY     0x04
#define ADS_RESET       0x06
#define ADS_START       0x08
#define ADS_STOP        0x0A
#define ADS_RDATAC      0x10
#define ADS_SDATAC      0x11
#define ADS_RDATA       0x12
#define ADS_RREG        0x20
#define ADS_WREG        0x40

/* Registers */
#define ADS_ID          0x00
#define ADS_CONFIG1     0x01
#define ADS_CONFIG2     0x02
#define ADS_CONFIG3     0x03
#define ADS_CONFIG4     0x04
#define ADS_CH1SET      0x05
#define ADS_CH2SET      0x06
#define ADS_CH3SET      0x07
#define ADS_CH4SET      0x08
#define ADS_CH5SET      0x09
#define ADS_CH6SET      0x0A
#define ADS_CH7SET      0x0B
#define ADS_CH8SET      0x0C
#define ADS_BIAS_SENSP  0x0D
#define ADS_BIAS_SENSN  0x0E
#define ADS_LOFF_SENSP  0x0F
#define ADS_LOFF_SENSN  0x10
#define ADS_LOFF_FLIP   0x11
#define ADS_LOFF_STATP  0x12
#define ADS_LOFF_STATN  0x13
#define ADS_GPIO        0x14
#define ADS_MISC1       0x15
#define ADS_MISC2       0x16

const char* const ads1299_data_source[] = {
    "Normal", "BIAS", "Shorted", "MVDD", "Temprature", "Test",
};

const int gain_list[] = {
    1, 2, 4, 6, 8, 12, 24, 0,
};


class ADS1299 {
    public:
        uint32_t statusBit = 0;

        //initialization with spi type
        ADS1299(int spitype, int sspin) {
            _spi = new SPIClass(spitype);
            SSPin = sspin;
        }

        //initialization with spi class pointer
        ADS1299(SPIClass* spiclass, int sspin) {
            _spi = spiclass;
            SSPin = sspin;
        }

        ~ADS1299() {}

        byte init();
        void begin();
        void reset();
        void readData(float res[]);

        void wakeup()   { _spiSend(ADS_WAKEUP);  delay(10); }
        void standby()  { _spiSend(ADS_STANDBY); delay(1); }
        void start()    { _spiSend(ADS_START);   delay(100); }
        void stop()     { _spiSend(ADS_STOP);    delay(10); }
        void rdatac()   { _spiSend(ADS_RDATAC);  delay(1); }
        void sdatac()   { _spiSend(ADS_SDATAC);  delay(1); }

        void setSPISpeed(uint32_t sp) {
            delete(_spiSetting);
            _spiSetting = new SPISettings(sp, MSBFIRST, SPI_MODE2);
        }

        /* 
         *  Enable or disable channel
         */
        bool setChannel(bool en);
        bool setChannel(uint8_t ch, bool en);
        bool getChannel(uint8_t ch = 0) {
            return (bool)(rreg(ADS_CH1SET + ch) & 0x80);
        }

        /* 
         *  Set and get data source (test/temp/normal/...)
         */
        bool setDataSource(uint8_t src);
        bool setDataSource(uint8_t ch, uint8_t src);
        const char* getDataSource(uint8_t ch = 0) { return _source[ch]; }

        /* 
         *  Set and get gain (default 24x)
         */
        bool setGain(uint8_t idx);
        bool setGain(uint8_t ch, uint8_t idx);
        int getGain(uint8_t ch = 0) { return _gain[ch]; }

        /* 
         *  Enable or disable impedance measurement
         */
        bool setImpedance(bool en);
        bool setImpedance(uint8_t ch, bool en);
        bool getImpedance(uint8_t ch = 0) { return _imped[ch]; }

        /* 
         *  Enable or disable BIAS output
         */
        bool setBias(bool en);
        bool getBias() { return _bias; }

        /* 
         *  Enable or disable ADS1299 sample rate
         */
        bool setSampleRate(uint16_t rate);
        int getSampleRate() { return _fs; }

    private:
        SPIClass* _spi = NULL;
        SPISettings* _spiSetting = NULL;
        uint8_t SSPin;
        bool _bias, _imped[8];
        int _fs, _gain[8];
        const char * _source[8];

        byte rreg(byte addr);
        void wreg(byte addr, byte data);

        inline byte _spiSend(const byte dat) {
            byte recv;
            digitalWrite(SSPin, LOW);
            _spi->beginTransaction(*_spiSetting);
            recv = _spi->transfer(dat);
            _spi->endTransaction();
            digitalWrite(SSPin, HIGH);
            return recv;
        }

        inline void _spiSend(const byte dat[], const uint8_t num, byte recv[]) {
            digitalWrite(SSPin, LOW);
            _spi->beginTransaction(*_spiSetting);
            for(int i = 0; i < num; i++) {
                recv[i] = _spi->transfer(dat[i]);
            }
            _spi->endTransaction();
            digitalWrite(SSPin, HIGH);
        }

        inline uint32_t _sign_extend_24_32(uint32_t x) {
            const int bits = 24;
            uint32_t m = 1u << (bits - 1);
            return (x ^ m) - m;
        }
};

#endif // ADS1299_ESP32_h
