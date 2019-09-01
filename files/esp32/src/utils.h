/*
 File: utils.h
 Authors: Tian-Cheng SONG <github.com/rotom407>
 Create: 2019-04-20 01:37:08
 
 Provide some useful classes.

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

#ifndef UTILS_H
#define UTILS_H

#include "Arduino.h"

template<typename T>
class CyclicQueue {
    public:
        T *buf;
        uint32_t buffersiz;
        bool overriden = false;
        uint32_t sp, ep;
        int32_t len = 0;
        CyclicQueue() {}
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
            memcpy(freezers, counters, length * sizeof(uint32_t));
        }
        uint32_t value(uint16_t index) {
            if (index < length) {
                return freezers[index];
            }
            return 0;
        }
};

/* 2nd order IIR filter
 * a0 * y[n] + a1 * y[n-1] + a2 * y[n-2] = b0 * x[n] + b1 * x[n-1] + b2 * x[n-2]
 */
template<typename T>
class Filter2 {
    private:
        T X[2], Y[2]; // x[n-1], x[n-2], y[n-1], y[n-2];
        double b0, b1, b2, a0 = 1, a1, a2;
    public:
        Filter2(): b0(0), b1(0), b2(0), a0(0), a1(0), a2(0) {};
        Filter2(double b[], double a[]){
            b0 = b[0]/a[0]; b1 = b[1]/a[0]; b2 = b[2]/a[0];
            a0 = 1;         a1 = a[1]/a[0], a2 = a[1]/a[0];
        }
        T process(T x) {
            T y = b0 * x + b1 * X[0] + b2 * X[1] - a1 * Y[0] - a2 * Y[1];
            Y[1] = Y[0]; Y[0] = y;
            X[1] = X[0]; X[0] = x;
            return y;
        }
};

#endif // UTILS_H
