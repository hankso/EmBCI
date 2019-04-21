/*
 File: ADS1299_ESP32.h
 Author: Song Tian Cheng, September 2018
 Webpage: http://github.com/rotom407
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
    private:
        SPIClass *spi = NULL;
        SPISettings *spiSetting = NULL;
        bool bias = false, imped = false;
        int gain = 24, fs = 250;
        uint8_t SSPin;
        const char *source = "normal";

        inline uint32_t sign_extend_24_32(uint32_t x) {
            const int bits = 24;
            uint32_t m = 1u << (bits - 1);
            return (x ^ m) - m;
        }

        inline byte spiSend(const byte dat) {
            byte recv;
            digitalWrite(SSPin, LOW);
            spi->beginTransaction(*spiSetting);
            recv = spi->transfer(dat);
            spi->endTransaction();
            digitalWrite(SSPin, HIGH);
            return recv;
        }

        inline void spiSend(const byte dat[], const uint8_t num, byte recv[]) {
            digitalWrite(SSPin, LOW);
            spi->beginTransaction(*spiSetting);
            for(int i = 0; i < num; i++) {
                recv[i] = spi->transfer(dat[i]);
            }
            spi->endTransaction();
            digitalWrite(SSPin, HIGH);
        }

        byte rreg(byte addr) {
            byte tobesent[3] = {0x00, 0x00, 0x00};
            byte received[3];
            tobesent[0] = ADS_RREG | addr;
            spiSend(tobesent, 3, received);
            return received[2];
        }

        void wreg(byte addr, byte data) {
            byte tobesent[3] = {0x00, 0x00, 0x00};
            byte received[3];
            tobesent[0] = ADS_WREG | addr;
            tobesent[2] = data;
            spiSend(tobesent, 3, received);
        }

    public:
        uint32_t statusBit = 0;

        //initialization with spi type
        ADS1299(int spitype, int sspin) {
            spi = new SPIClass(spitype);
            SSPin = sspin;
        }

        //initialization with spi class pointer
        ADS1299(SPIClass* spiclass, int sspin) {
            spi = spiclass;
            SSPin = sspin;
        }

        byte init() {
            byte id;
            reset();
            sdatac();
            id = rreg(ADS_ID);
            wreg(ADS_CONFIG2, 0xD0);
            wreg(ADS_CONFIG3, 0xE0);
            wreg(ADS_MISC1, 0x20);
            for (int i = 0; i < 8; i++) {
                wreg(ADS_CH1SET + i, 0x60);
            }
            start();
            rdatac();
            return id;
        }

        void begin() {
            pinMode(SSPin, OUTPUT);
            digitalWrite(SSPin, HIGH);
            spi->begin();
            spiSetting = new SPISettings(1000000, MSBFIRST, SPI_MODE2);
        }

        void reset() {
            spiSend(ADS_RESET);
            delay(1000);
            gain = 24;
            fs = 250;
            bias = false;
            imped = false;
        }

        void wakeup() {
            spiSend(ADS_WAKEUP);
            delay(10);
        }

        void standby() {
            spiSend(ADS_STANDBY);
        }

        void start() {
            spiSend(ADS_START);
            delay(100);
        }

        void stop() {
            spiSend(ADS_STOP);
            delay(10);
        }

        void rdatac() {
            spiSend(ADS_RDATAC);
            delay(1);
        }

        void sdatac() {
            spiSend(ADS_SDATAC);
            delay(1);
        }

        bool setSPISpeed(uint32_t spd) {
            delete(spiSetting);
            spiSetting = new SPISettings(spd, MSBFIRST, SPI_MODE2);
            return true;
        }

        bool setDataSource(uint8_t src) {
            if (src > 7) return false;
            const char *srcName = ads1299_data_source[src];
            if (!strcmp(source, srcName)) return true;
            source = srcName;
            sdatac();
            for (int i = 0; i < 8; i++) {
                byte v = rreg(ADS_CH1SET + i);
                wreg(ADS_CH1SET + i, (v & ~0x07) | src);
            }
            rdatac();
            return true;
        }

        bool setDataSource(uint8_t src, int ch) {
            if (ch < 0) return setDataSource(src);
            if (ch > 7 || src > 7) return false;
            const char *srcName = ads1299_data_source[src];
            if (!strcmp(source, srcName)) return true;
            source = srcName;
            sdatac();
            byte v = rreg(ADS_CH1SET + ch);
            wreg(ADS_CH1SET + ch, (v & ~0x07) | src);
            rdatac();
            return true;
        }

        bool setGain(uint8_t idx) {
            if (idx > 7) return false;
            int idxAmp = gain_list[idx];
            if (gain == idxAmp) return true;
            gain = idxAmp;
            sdatac();
            for (int i = 0; i < 8; i++) {
                byte v = rreg(ADS_CH1SET + i);
                wreg(ADS_CH1SET + i, (v & ~0x70) | (idx << 4));
            }
            rdatac();
            return true;
        }

        bool setGain(uint8_t idx, int ch) {
            if (ch < 0) return setGain(idx);
            if (ch > 7 || idx > 7) return false;
            int idxAmp = gain_list[idx];
            if (gain == idxAmp) return true;
            gain = idxAmp;
            sdatac();
            byte v = rreg(ADS_CH1SET + ch);
            wreg(ADS_CH1SET + ch, (v & ~0x70) | (idx << 4));
            rdatac();
            return true;
        }

        bool setImpedance(bool en) {
            if (imped == en) return true;
            imped = en;
            setGain(en ? 0 : 6); // TODO: is this really necessary?
            setDataSource(0);
            sdatac();
            wreg(ADS_LOFF_SENSP, en ? 0xFF : 0x00);
            rdatac();
            return true;
        }

        bool setImpedance(bool en, int ch) {
            if (ch < 0) setImpedance(en);
            if (imped == en) return true;
            imped = en;
            setGain(en ? 0 : 6, ch); // TODO: is this really necessary?
            setDataSource(0, ch);
            sdatac();
            byte v = rreg(ADS_LOFF_SENSP);
            wreg(ADS_LOFF_SENSP, (v & ~(1 << ch)) | ((en ? 1 : 0) << ch) );
            rdatac();
            return true;
        }

        bool setBias(bool en) {
            if (bias == en) return true;
            bias = en;
            sdatac();
            wreg(ADS_BIAS_SENSP, en ? 0xFF : 0x00);
            wreg(ADS_BIAS_SENSN, en ? 0xFF : 0x00);
            wreg(ADS_CONFIG3,    en ? 0xEC : 0xE0);
            rdatac();
            return true;
        }

        bool setSampleRate(uint16_t rate) {
            byte lowbyte;
            switch (rate) {
            case 250:
                lowbyte = 0x06;
                break;
            case 500:
                lowbyte = 0x05;
                break;
            case 1000:
                lowbyte = 0x04;
                break;
            case 2000:
                lowbyte = 0x03;
                break;
            case 4000:
                lowbyte = 0x02;
                break;
            case 8000:
                lowbyte = 0x01;
                break;
            case 16000:
                lowbyte = 0x00;
                break;
            default:
                return false;
            }
            fs = rate;
            sdatac();
            wreg(ADS_CONFIG1, 0x90 | lowbyte);
            rdatac();
            return true;
        }

        const char* getDataSource(int ch = 0) { return source; }

        bool getImpedance(int ch = 0) { return imped; }

        bool getBias() { return bias; }

        int getSampleRate() { return fs; }

        void readData(float res[]) {
            byte tobesent[27];
            byte received[27];
            int32_t data[8];
            for (int i = 0; i < 27; i++) {
                tobesent[i] = 0x00;
            }
            spiSend(tobesent, 27, received);
            for (int i = 0; i < 8; i++) {
                data[i] = sign_extend_24_32(
                        (received[3 + 3*i] << 16) | \
                        (received[4 + 3*i] << 8) | \
                        (received[5 + 3*i])
                );
            }
            for(int i = 0; i < 8; i++) {
                //res[i]=((float)data[i])*2.0*4.5/gain/16777216.0;
                res[i]=*((float*)(data+i));
            }
            statusBit = (received[0] << 16) | \
                        (received[1] << 8) | \
                        (received[2]);
        }

        ~ADS1299() {}
};

#endif // ADS1299_ESP32_h
