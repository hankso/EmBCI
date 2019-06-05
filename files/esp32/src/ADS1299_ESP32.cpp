/*
 File: ADS1299_ESP32.cpp
 Author: SONG Tian-Cheng, September 2018
 Webpage: http://github.com/rotom407
 Time: Tue 19 Mar 2019 20:44:52 CST

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

#include "ADS1299_ESP32.h"


byte ADS1299::init() {
    reset();
    sdatac();
    byte id = rreg(ADS_ID);
    wreg(ADS_CONFIG2, 0xD0);
    wreg(ADS_CONFIG3, 0xE0);
    wreg(ADS_MISC1, 0x20);
    for (int ch = 0; ch < 8; ch++) {
        wreg(ADS_CH1SET + ch, 0x60);
    }
    start();
    rdatac();
    return id;
}

void ADS1299::begin() {
    pinMode(SSPin, OUTPUT);
    digitalWrite(SSPin, HIGH);
    _spi->begin();
    _spiSetting = new SPISettings(1000000, MSBFIRST, SPI_MODE2);
}

void ADS1299::reset() {
    _spiSend(ADS_RESET);
    delay(1000);
    _bias = false;
    _fs = 250;
    for (int ch = 0; ch < 8; ch++) {
        _imped[ch] = false;
        _gain[ch] = 24;
        _source[ch] = "normal";
    }
}

void ADS1299::readData(float res[]) {
    byte tobesent[27];
    byte received[27];
    int32_t data[8];
    for (int i = 0; i < 27; i++) {
        tobesent[i] = 0x00;
    }
    _spiSend(tobesent, 27, received);
    for (int i = 0; i < 8; i++) {
        data[i] = _sign_extend_24_32(
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

bool ADS1299::setChannel(bool en) {
    sdatac();
    for (int ch = 0; ch < 8; ch++) {
        byte reg = rreg(ADS_CH1SET + ch);
        wreg(ADS_CH1SET + ch, en ? (reg | 0x80) : (reg & 0x7F));
    }
    rdatac();
    return true;
}

bool ADS1299::setChannel(uint8_t ch, bool en) {
    if (ch > 7) return false;
    sdatac();
    byte reg = rreg(ADS_CH1SET + ch);
    wreg(ADS_CH1SET + ch, en ? (reg | 0x80) : (reg & 0x7F));
    rdatac();
    return true;
}

bool ADS1299::setDataSource(uint8_t src) {
    if (src > 7) return false;
    const char *srcName = ads1299_data_source[src];
    sdatac();
    for (uint8_t ch = 0; ch < 8; ch++) {
        if (!strcmp(_source[ch], srcName)) continue;
        _source[ch] = srcName;
        byte reg = rreg(ADS_CH1SET + ch);
        wreg(ADS_CH1SET + ch, (reg & ~0x07) | src);
    }
    rdatac();
    return true;
}

bool ADS1299::setDataSource(uint8_t ch, uint8_t src) {
    if (ch > 7 || src > 7) return false;
    const char *srcName = ads1299_data_source[src];
    if (!strcmp(_source[ch], srcName)) return true;
    _source[ch] = srcName;
    sdatac();
    byte reg = rreg(ADS_CH1SET + ch);
    wreg(ADS_CH1SET + ch, (reg & ~0x07) | src);
    rdatac();
    return true;
}

bool ADS1299::setGain(uint8_t idx) {
    if (idx > 7) return false;
    int idxAmp = gain_list[idx];
    sdatac();
    for (uint8_t ch = 0; ch < 8; ch++) {
        if (_gain[ch] == idxAmp) continue;
        _gain[ch] = idxAmp;
        byte reg = rreg(ADS_CH1SET + ch);
        wreg(ADS_CH1SET + ch, (reg & ~0x70) | (idx << 4));
    }
    rdatac();
    return true;
}

bool ADS1299::setGain(uint8_t ch, uint8_t idx) {
    if (ch > 7 || idx > 7) return false;
    int idxAmp = gain_list[idx];
    if (_gain[ch] == idxAmp) return true;
    _gain[ch] = idxAmp;
    sdatac();
    byte reg = rreg(ADS_CH1SET + ch);
    wreg(ADS_CH1SET + ch, (reg & ~0x70) | (idx << 4));
    rdatac();
    return true;
}

bool ADS1299::setImpedance(bool en) {
    for (uint8_t ch = 0; ch < 8; ch++) {
        if (_imped[ch] == en) continue;
        _imped[ch] = en;
        setDataSource(ch, 0);
        setGain(ch, en ? 0 : 6);
    }
    sdatac();
    wreg(ADS_LOFF_SENSP, en ? 0xFF : 0x00);
    rdatac();
    return true;
}

bool ADS1299::setImpedance(uint8_t ch, bool en) {
    if (ch > 7) return false;
    if (_imped[ch] == en) return true;
    _imped[ch] = en;
    setDataSource(ch, 0);
    setGain(ch, en ? 0 : 6);
    sdatac();
    byte reg = rreg(ADS_LOFF_SENSP) & ~(0x01 << (ch - 1));
    wreg(ADS_LOFF_SENSP, reg | ((en ? 1 : 0) << (ch - 1)));
    rdatac();
    return true;
}

bool ADS1299::setBias(bool en) {
    if (_bias == en) return true;
    _bias = en;
    sdatac();
    wreg(ADS_BIAS_SENSP, en ? 0xFF : 0x00);
    wreg(ADS_BIAS_SENSN, en ? 0xFF : 0x00);
    wreg(ADS_CONFIG3,    en ? 0xEC : 0xE0);
    rdatac();
    return true;
}

bool ADS1299::setSampleRate(uint16_t rate) {
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
    _fs = rate;
    sdatac();
    wreg(ADS_CONFIG1, 0x90 | lowbyte);
    rdatac();
    return true;
}

/******************************************************************
 * private
 */

byte ADS1299::rreg(byte addr) {
    byte tobesent[3] = {0x00, 0x00, 0x00};
    byte received[3];
    tobesent[0] = ADS_RREG | addr;
    _spiSend(tobesent, 3, received);
    return received[2];
}

void ADS1299::wreg(byte addr, byte data) {
    byte tobesent[3] = {0x00, 0x00, 0x00};
    byte received[3];
    tobesent[0] = ADS_WREG | addr;
    tobesent[2] = data;
    _spiSend(tobesent, 3, received);
    }
