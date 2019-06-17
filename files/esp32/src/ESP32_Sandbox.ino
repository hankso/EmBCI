/*
 File: ESP32_Sandbox.ino

 This file is ESP32 firmware source code used in EmBCI.

 Created by Song Tian Cheng, September 2018
 Page @ http://github.com/rotom407

 Modified by Gao Han Lin, October 2018
 Page @ http://github.com/hankso

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

#include "ESP32_Sandbox.h"
#define FILTERARRAY8(fc, array, b, a) fc array[8] = {\
    fc(b, a), fc(b, a), fc(b, a), fc(b, a),\
    fc(b, a), fc(b, a), fc(b, a), fc(b, a),\
}

int drdypulsetime = 10;
char *spibufrecv;
bool blinkstat = false;

SPIClass *vspi;
WiFiClient client;

bufftype cqbuf[M_BUFFERSIZE];
bufftype *spibuf;

double cb[] = {0.99843167, -1.89912988, 0.99843167};
double ca[] = {1.0, -1.89912988, 0.99686333};
FILTERARRAY8(Filter2<bufftype>, filters, cb, ca);

spi_slave_transaction_t t;
spi_slave_transaction_t *p = &t;


void read_from_ads1299() {
    static long wavei;
    int32_t res[8];
    uint32_t statusBit = ads.readData(res);
    counter.count(0);
    if ((statusBit & 0xF00000) != 0xC00000) return;
    counter.count(1);
    switch (output_data) {
    case ADS_RAW:
        for (int i = 0; i < 8; i++) { cq.push(res[i]); }
        break;
    case ADS_NOTCH:
        for (int i = 0; i < 8; i++) {
            cq.push(filters[i].process(res[i]));
            cq.push(res[i]);
        }
        break;
    case ESP_SQUARE:
        for (int i = 0; i < 8; i++, wavei++) {
            cq.push(wavei >> 7 & 1);
        }
        break;
    case ESP_SINE:
        wavei++;
        int32_t value = sin(2 * PI * sinc_freq * wavei / ads.sampleRate);
        for (int i = 0; i < 8; i++) { cq.push(value); }
        break;
    }
}

/*
void handle_uart_message() {
    if (wifi_echo && client.connected()) {
        ESP_LOGI(NAME, "Redirecting Serial1 to WiFi client.");
        ESP_LOGE(NAME, "Not implemented yet!");
        return;
        while (Serial1.available()) {
            client.print(Serial1.readStringUntil('\n'));
        }
        while (client.available()) {
            Serial1.print(client.readStringUntil('\n'));
        }
    }
}
*/

void handle_spi_command() {
    if (spibufrecv[0] == 0x00) {
        return;
    } else {
        char tmp[3*128 + 1];
        tmp[3*128] = '\0';
        for (int i = 0; i < 128; i++) {
            snprintf(tmp + 3*i, 4, "%02X ", spibufrecv[i]);
        }
        ESP_LOGD(NAME, "SPI RECEIVED: %s", tmp);
    }
    if (spibufrecv[0] == 0x40) {
        ESP_LOGD(NAME, "INSTRUCTION: WREG");
        uint8_t reg = spibufrecv[1], cmd = spibufrecv[2], param = spibufrecv[3];
        switch (reg) {
        case 0x50:
            ESP_LOGD(NAME, "REGISTER: SAMPLE RATE");
            if (cmd > 6) {
                ESP_LOGE(NAME, "UNSUPPORTED SAMPLE RATE: %d", cmd);
            } else {
                ads.setSampleRate(ads1299_sample_rate[cmd]);
                ESP_LOGD(NAME, "SAMPLE RATE SET TO: %dHZ", ads.getSampleRate());
            }
            break;
        case 0x52:
            ESP_LOGD(NAME, "REGISTER: INPUT SOURCE");
            if (cmd > 7) {
                ESP_LOGE(NAME, "NOT IMPLEMENTED SOURCE %d", cmd);
            } else {
                ads.setDataSource(cmd);
                ESP_LOGD(NAME, "SOURCE %s ENABLED", ads.getDataSource());
            }
            break;
        case 0x54:
            ESP_LOGD(NAME, "REGISTER: BIAS OUTPUT");
            if (cmd > 1) {
                ESP_LOGE(NAME, "NOT IMPLEMENTED BIAS CMD %d", cmd);
            } else {
                ads.setBias((bool)cmd);
                ESP_LOGD(NAME, "BIAS OUTPUT %s",
                    ads.getBias() ? "ENABLED" : "DISABLED");
            }
            break;
        case 0x56:
            ESP_LOGD(NAME, "REGISTER: IMPEDANCE");
            if (cmd > 1) {
                ESP_LOGE(NAME, "NOT IMPLEMENTED IMPEDANCE CMD %d", cmd);
            } else {
                ads.setImpedance((bool)cmd);
                ESP_LOGD(NAME, "IMPEDANCE %s",
                    ads.getImpedance() ? "ENABLED" : "DISABLED");
            }
            break;
        case 0x58:
            ESP_LOGD(NAME, "REGISTER: CHANNEL");
            if (cmd > 7) {
                ESP_LOGE(NAME, "UNSUPPORTED CHANNEL %d", cmd);
            } else {
                ads.setChannel(cmd, (bool)param);
                ESP_LOGD(NAME, "CHANNEL %d %s",
                    cmd, ads.getChannel(cmd) ? "ON" : "OFF");
            }
            break;
        default:
            ESP_LOGE(NAME, "REGISTER: NOT IMPLEMENTED");
        }
    } else {
        ESP_LOGD(NAME, "INSTRUCTION: NOT IMPLEMENTED");
    }
}

void handle_spi() {
    switch (slave_status) {
    case IDLE:
        // Put data into spi_slave_queue, waiting spi_master to read
        if (cq.len <= PACKETSIZE) break;
        // SPI slave satatus reset to poll
        slave_status = POLL;
        digitalWrite(PIN_DRDY, LOW);
        drdypulsetime = 10;
        for (int i = 0; i < PACKETSIZE; i++) {
            cq.pop(&(spibuf[i]));
        }
        spibufrecv[0] = '\0';
        t.length = sizeof(bufftype) * PACKETSIZE * 8;
        t.trans_len = t.length;
        t.tx_buffer = (char*)spibuf;
        t.rx_buffer = (char*)spibufrecv;
        spi_slave_queue_trans(VSPI_HOST, &t, portMAX_DELAY);
        if (cq.overriden) {
            ESP_LOGD(NAME, "BUFFER OVERFLOW");
            cq.overriden = false;
        }
        clkslavetimeout.reset();
        break;
    case POLL:
        // Data has not been read by SPI master yet
        if (clkslavetimeout.getdiff() > SLAVESENDTIMEOUT) {
            clkslavetimeout.reset();
            digitalWrite(PIN_DRDY, LOW);
            drdypulsetime = 10;
            ESP_LOGV(NAME, "SPI TIMED OUT, RESENDING");
        }
        // SPI master has read data, set slave status back to idle
        if (spi_slave_get_trans_result(VSPI_HOST, &p, 0) != ESP_ERR_TIMEOUT) {
            slave_status = IDLE;
            handle_spi_command();
        }
        break;
    }
}

void blinkTest() {
    if (clkblink.getdiff() < 1000) return;
    if (digitalRead(PIN_BLINK) == LOW) {
        digitalWrite(PIN_BLINK, HIGH);
    } else {
        digitalWrite(PIN_BLINK, LOW);
    }
    clkblink.reset();
}

void setup() {
    ESP_LOGD(NAME, "Booting...");

#ifdef CONFIG_TASK_WDT
    if (esp_task_wdt_add(NULL) == ESP_OK && \
        esp_task_wdt_status(NULL) == ESP_OK) {
        ESP_LOGD(NAME, "Task loopTask @ CPU0 subscribed to TWDT");
    }
    if (esp_task_wdt_delete(xTaskGetIdleTaskHandleForCPU(1)) == ESP_OK) {
        ESP_LOGD(NAME, "Task IDLE1 @ CPU1 unsubscribed from TWDT");
    }
#endif

    ESP_LOGD(NAME, "Init Serial... ");
    uart_config_t uart_config = {
        .baud_rate = 115200,
        // .baud_rate = 500000,
        .data_bits = UART_DATA_8_BITS,
        .parity = UART_PARITY_DISABLE,
        .stop_bits = UART_STOP_BITS_1,
        .flow_ctrl = UART_HW_FLOWCTRL_DISABLE,
        .rx_flow_ctrl_thresh = 0,
        .use_ref_tick = true
    };
    ESP_ERROR_CHECK( uart_param_config(UART_CONSOLE, &uart_config) );
    ESP_ERROR_CHECK( uart_driver_install(UART_CONSOLE, 256, 0, 0, NULL, 0) );
    esp_vfs_dev_uart_use_driver(UART_CONSOLE);
    setvbuf(stdin, NULL, _IONBF, 0);
    setvbuf(stdout, NULL, _IONBF, 0);
    // Serial1.begin(500000);
    version_info();
    ESP_LOGD(NAME, "done");

    ESP_LOGD(NAME, "Init GPIO... ");
    pinMode(PIN_DRDY, OUTPUT);
    digitalWrite(PIN_DRDY, HIGH);
    pinMode(PIN_BLINK, OUTPUT);
    digitalWrite(PIN_BLINK, LOW);
    pinMode(GPIO_DRDY, INPUT);
    adc1_config_width(ADC_WIDTH_BIT_12);
    adc1_config_channel_atten(ADC1_CHANNEL_5, ADC_ATTEN_DB_6);
    ESP_LOGD(NAME, "done");

    ESP_LOGD(NAME, "Init SPI... ");
    vspi = new SPIClass(VSPI);
    vspi->begin();

    spibuf = (bufftype*) heap_caps_malloc(
        sizeof(bufftype) * M_BUFFERSIZESPI, MALLOC_CAP_DMA);
    spibufrecv = (char*) heap_caps_malloc(
        sizeof(bufftype) * M_BUFFERSIZESPI, MALLOC_CAP_DMA);
    memset(&t, 0, sizeof(spi_slave_transaction_t));
    cq = CyclicQueue<bufftype>(cqbuf, M_BUFFERSIZE);
    for (int i = 0; i < M_BUFFERSIZE; i++) {
        cq.buf[i] = i;
    }

    spi_bus_config_t buscfg = {
        .mosi_io_num = GPIO_MOSI,
        .miso_io_num = GPIO_MISO,
        .sclk_io_num = GPIO_SCLK,
        .quadwp_io_num = -1,
        .quadhd_io_num = -1,
        .max_transfer_sz = 0,
        .flags = 0
    };
    spi_slave_interface_config_t slvcfg = {
        .spics_io_num = PIN_CS,
        .flags = 0,
        .queue_size = 3,
        .mode = 0,
        .post_setup_cb = NULL,
        .post_trans_cb = NULL,
    };
    if (spi_slave_initialize(VSPI_HOST, &buscfg, &slvcfg, 1) != ESP_OK) {
        ESP_LOGE(NAME, "spi_slave_initialize FAILED!!!");
    }
    ESP_LOGD(NAME, "done");

    /*
    ESP_LOGD(NAME, "Init WiFi... ");
    WiFi.mode(WIFI_STA);
    ESP_LOGD(NAME, "done");
    */

    ESP_LOGD(NAME, "Init ADS... ");
    ads.begin();
    delay(10);
    ads.init();
    ESP_LOGD(NAME, "done");

    ESP_LOGD(NAME, "Init Console... ");
    initialize_console();
    // compatiable for `minicom`, `screen` those who send CR
    esp_vfs_dev_uart_set_rx_line_endings(ESP_LINE_ENDINGS_CR);
    esp_vfs_dev_uart_set_tx_line_endings(ESP_LINE_ENDINGS_CRLF);
    ESP_LOGD(NAME, "done");

    ESP_LOGD(NAME, "Begin setup");
    clkgen.reset();
    clkts.reset();
    // clkblink.reset();
    attachInterrupt(GPIO_DRDY, read_from_ads1299, FALLING);
    xTaskCreatePinnedToCore(console_loop, "console", 3000, NULL, 2, NULL, 1);
    ESP_LOGD(NAME, "End setup");
    ESP_LOGI(NAME, "Type `help` for commands message");
}

void loop() {
    // blinkTest();
    // handle_usrt_message();
    handle_spi();

    if (drdypulsetime <= 0) {
        digitalWrite(PIN_DRDY, HIGH);
    } else {
        drdypulsetime--;
    }

    if (clkgen.getdiff() > 1000) {
        counter.freeze();
        counter.reset();
        clkgen.reset();
    }

#ifdef CONFIG_TASK_WDT
    esp_task_wdt_reset();
#endif
}
