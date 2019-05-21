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

// local headers
#include "ESP32_Sandbox.h"
#include "ADS1299_ESP32.h"
#include "console_cmds.h"

int drdypulsetime = 10;
long wavei = 0;
char *spibufrecv;
bool blinkstat = false;

SPIClass *vspi;
WiFiClient client;

bufftype cqbuf[M_BUFFERSIZE];
bufftype *spibuf;

spi_slave_transaction_t *t;


void read_from_ads1299() {
    float res[8];
    ads.readData(res);
    counter.count(0);
    if ((ads.statusBit & 0xF00000) != 0xC00000) return;
    counter.count(1);
    for (int i = 0; i < 8; i++) {
        switch (data_source) {
        case ADS_RAW:
            cq->push(res[i]); break;
        case ESP_SQUARE:
            cq->push((float)((wavei / 100) % 2));
            wavei++; break;
        case ESP_SINE:
            cq->push(sin(wavei / 10));
            wavei++; break;
        case ESP_CONST:
            cq->push(1.0); break;
        }
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
        switch(spibufrecv[1]) {
        case 0x50:
            ESP_LOGD(NAME, "REGISTER: SAMPLE RATE: ");
            if (spibufrecv[2] <= 6) {
                int samplerate = sample_rate_list[6 - spibufrecv[2]];
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
}

void handle_spi() {
    switch (slave_status) {
        case IDLE:
            // Put data into spi_slave_queue, waiting spi_master to read
            if (cq->len <= PACKETSIZE) break;
            // SPI slave satatus reset to poll
            slave_status = POLL;
            digitalWrite(DRDY_PIN, LOW);
            drdypulsetime = 10;
            for (int i = 0; i < PACKETSIZE; i++) {
                cq->pop(&(spibuf[i]));
            }
            spibufrecv[0] = '\0';
            t->length = sizeof(bufftype) * PACKETSIZE * 8;
            t->trans_len = t->length;
            t->tx_buffer = (char*)spibuf;
            t->rx_buffer = (char*)spibufrecv;
            spi_slave_queue_trans(VSPI_HOST, t, portMAX_DELAY);
            if (cq->overriden) {
                ESP_LOGD(NAME, "BUFFER OVERFLOW");
                cq->overriden = false;
            }
            clkslavetimeout.reset();
            break;
        case POLL:
            // Data has not been read by SPI master yet
            if (clkslavetimeout.getdiff() > SLAVESENDTIMEOUT) {
                clkslavetimeout.reset();
                digitalWrite(DRDY_PIN, LOW);
                drdypulsetime = 10;
                ESP_LOGV(NAME, "SPI TIMED OUT, RESENDING");
            }
            // SPI master has read data, set slave status back to idle
            if (spi_slave_get_trans_result(VSPI_HOST, &t, 0) != ESP_ERR_TIMEOUT) {
                slave_status = IDLE;
                handle_spi_command();
            }
            break;
    }
}

/*
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
*/


void setup() {
    ESP_LOGD(NAME, "ESP32 Firmware 2018.10-EmBCI");
    ESP_LOGD(NAME, "Board:  OrangePi Zero Plus 2");
    ESP_LOGD(NAME, "Shield: EmBCI Rev.A7 Oct 22 2018");
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

    spibuf = (bufftype*) heap_caps_malloc(
        sizeof(bufftype) * M_BUFFERSIZESPI, MALLOC_CAP_DMA);
    spibufrecv = (char*) heap_caps_malloc(
        sizeof(bufftype) * M_BUFFERSIZESPI, MALLOC_CAP_DMA);
    memset(t, 0, sizeof(spi_slave_transaction_t));
    cq = new CyclicQueue<bufftype>(cqbuf,M_BUFFERSIZE);
    for (int i = 0; i < M_BUFFERSIZE; i++) {
        cq->buf[i] = i;
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
        .spics_io_num = GPIO_CS,
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
    attachInterrupt(ADS_DRDY_PIN, read_from_ads1299, FALLING);
    ESP_LOGI(NAME, "Type `help` for commands message");
    xTaskCreatePinnedToCore(console_loop, "console", 3000, NULL, 2, NULL, 0);
    ESP_LOGD(NAME, "End setup");
}

void loop() {
    // blinkTest();
    // handle_usrt_message();
    handle_spi();

    if (drdypulsetime <= 0) {
        digitalWrite(DRDY_PIN, HIGH);
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
