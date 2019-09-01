/*
 File: ADS1299_ESP32.cpp
 Authors: Tian-Cheng SONG <github.com/rotom407>, September 2018
          Hank <hankso1106@gmail.com>
 Create: 2019-03-19 20:44:52

 Rewritten for EmBCI by Hank and Song.

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
    wreg(ADS_CONFIG2, 0xD5);
    wreg(ADS_CONFIG3, 0xE0);
    wreg(ADS_MISC1, 0x20);
    for (int ch = 0; ch < 8; ch++) {
        wreg(ADS_CH1SET + ch, 0x60);
    }
    sampleRate = getSampleRate(); // update variable sampleRate
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
    for (int ch = 0; ch < 8; ch++) {
        _imped[ch] = false;
        _gain[ch] = 24;
        _source[ch] = "normal";
    }
}

uint32_t ADS1299::readData(int32_t res[]) {
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
    for (int i = 0; i < 8; i++) {
        res[i] = *(data+i);
    }
    statusBit = (received[0] << 16) | (received[1] << 8) | (received[2]);
    return statusBit;
}

bool ADS1299::setChannel(bool en) {
    sdatac();
    for (int ch = 0; ch < 8; ch++) {
        byte reg = rreg(ADS_CH1SET + ch);
        wreg(ADS_CH1SET + ch, en ? (reg & 0x7F) : (reg | 0x80));
    }
    rdatac();
    return true;
}

bool ADS1299::setChannel(int ch, bool en) {
    if (ch < 0) return setChannel(en);
    if (ch > 7) return false;
    sdatac();
    byte reg = rreg(ADS_CH1SET + ch);
    wreg(ADS_CH1SET + ch, en ? (reg & 0x7F) : (reg | 0x80));
    rdatac();
    return true;
}

uint8_t ADS1299::getChannel(int ch) {
    if (ch > 7) return 0;
    uint8_t state = 0;
    sdatac();
    for (uint8_t i = 0; i < 8; i++) {
        if (rreg(ADS_CH1SET + i) & 0x80) continue;
        state |= 1 << i;
    }
    rdatac();
    if (ch < 0) return state;
    return state & (1 << ch);
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

bool ADS1299::setDataSource(int ch, uint8_t src) {
    if (ch < 0) return setDataSource(src);
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

const char* ADS1299::getDataSource(int ch) {
    if (ch < 0) ch = 0; // TODO: all channel
    return _source[ch];
}

bool ADS1299::setGain(uint8_t idx) {
    if (idx > 7) return false;
    int idxAmp = ads1299_gain_list[idx];
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

bool ADS1299::setGain(int ch, uint8_t idx) {
    if (ch < 0) return setGain(idx);
    if (ch > 7 || idx > 7) return false;
    int idxAmp = ads1299_gain_list[idx];
    if (_gain[ch] == idxAmp) return true;
    _gain[ch] = idxAmp;
    sdatac();
    byte reg = rreg(ADS_CH1SET + ch);
    wreg(ADS_CH1SET + ch, (reg & ~0x70) | (idx << 4));
    rdatac();
    return true;
}

int ADS1299::getGain(int ch) {
    if (ch < 0) ch = 0; // TODO: all channel
    return _gain[ch];
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

bool ADS1299::setImpedance(int ch, bool en) {
    if (ch < 0) return setImpedance(en);
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

uint8_t ADS1299::getImpedance(int ch) {
    if (ch > 7) return 0;
    sdatac();
    uint8_t state = rreg(ADS_LOFF_SENSP);
    rdatac();
    if (ch < 0) return state;
    return state & (1 << ch);
}

bool ADS1299::setBias(bool en) {
    wreg(ADS_BIAS_SENSP, en ? 0xFF : 0x00);
    wreg(ADS_BIAS_SENSN, en ? 0xFF : 0x00);
    wreg(ADS_CONFIG3,    en ? 0xEC : 0xE0);
    return getBias() == en;
}

bool ADS1299::getBias() {
    sdatac();
    byte reg = rreg(ADS_CONFIG3) & 0x0C;
    rdatac();
    return (bool)reg;
}

bool ADS1299::setSampleRate(uint16_t rate) {
    byte lowbyte = 255;
    for (int i = 0; i < 7; i++) {
        if (ads1299_sample_rate[i] == rate) {
            lowbyte = i; break;
        }
    }
    if (lowbyte > 7) return false;
    sdatac();
    byte reg = rreg(ADS_CONFIG1) & ~0x07;
    wreg(ADS_CONFIG1, reg | lowbyte);
    rdatac();
    return getSampleRate() == rate;
}

uint16_t ADS1299::getSampleRate() {
    sdatac();
    byte reg = rreg(ADS_CONFIG1) & 0x07;
    rdatac();
    sampleRate = reg < 7 ? ads1299_sample_rate[reg] : 0;
    return sampleRate;
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

void ADS1299::rregs(byte addr, uint8_t num, byte received[]) {
    byte tobesent[2 + num];
    tobesent[0] = ADS_RREG | addr;
    tobesent[1] = num - 1;
    _spiSend(tobesent, 2 + num, received);
}

void ADS1299::wreg(byte addr, byte data) {
    // byte array[] = {data};
    // wregs(addr, 1, array);
    byte tobesent[3] = {0x00, 0x00, 0x00};
    byte received[3];
    tobesent[0] = ADS_WREG | addr;
    tobesent[2] = data;
    _spiSend(tobesent, 3, received);
}

void ADS1299::wregs(byte addr, uint8_t num, byte data[]) {
    byte tobesent[2 + num];
    tobesent[0] = ADS_WREG | addr;
    tobesent[1] = num - 1;
    for (int i = 0; i < num; i++) {
        tobesent[2 + i] = data[i];
    }
    byte received[2 + num];
    _spiSend(tobesent, 2 + num, received);
}
