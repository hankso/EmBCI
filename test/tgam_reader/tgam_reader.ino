/*
# TGAM_Reader by hank
Date: 2018.1.2

Implemented on Attiny 85
After compiled:
    1962/8192 bytes (23%) Flash
    157/512 bytes (30%) RAM

Full on Nano
After compiled:
    5984/30720 (19%) Flash
    317/2048 (15%) RAM
*/
//#define ATTINY_85

#include <SoftwareSerial.h>
#define SYNC 0xAA       // flag of data
// #define DEBUG           // output debug info
#define RAW             // parse raw data(512Hz)
#define PACKAGE         // parse package data(1Hz)

#if defined(ATTINY_85)
    SoftwareSerial myport(0, 2); //RX, TX
    #define Serial myport // on attiny85 there is no hardware Serial
    #define ledPin 1
#else
    #define ledPin 13
#endif

SoftwareSerial TGAM(3, 4); // RX, TX

void setup()
{
    pinMode(ledPin, OUTPUT);
    Serial.begin(115200);
    TGAM.begin(57600);
}

void loop()
{
    get_TGAM_info();

/*
    Serial.println(micros());
    Serial.printf("%ld %d\n", micros(), 32767);
    Serial.println(micros());
    delay(1000);

    uint32_t h = 0xf0;
    uint16_t m = 0xaa;
    uint8_t  l = 0x0f;
    Serial.println( (uint32_t)(h<<16|m<<8|l) );

    if (TGAM.available()) {
        uint32_t time = micros();
        TGAM.write(TGAM.read());
        time = micros() - time;
        Serial.println(time);
        uint32_t time = micros();
        TGAM.read();
        time = micros() - time;
        Serial.println(time);
    }
*/
}

void get_TGAM_info() {
    /*
    compared to data transfering rate from TGAM chip (approximately
    512*8 = 4096 byte/s = 4kbps), SoftwareSerial.read() is much
    faster (4us per byte --> 244kbps). And SoftwareSerial.write() is
    raletively compatible to TGAM (approximately 300us per byte -->
    3.26kbps)
    Considering we cannot freely set read timeout and it will return
    -1 if no data available, it's better to wait until enough data
    stay in buffer(default 64 bytes), let's set threshold to
    36(length of package).
    */

    uint8_t length;
    String result = "";

    while (TGAM.available() < 36) ;
    while (TGAM.read() != SYNC) ; // wait until 1st 0xaa
    while (TGAM.read() != SYNC) ; // wait until 2nd 0xaa
    while (TGAM.available() < 36) ;
    while ( (length = TGAM.read()) == SYNC ) ; // loop until not 0xaa

    #ifdef RAW
        // e.g. aa aa|04|80 02|f8 00|85
        if (length == 4) {
            #ifdef DEBUG
                uint8_t H, L, checksum;
                TGAM.read();TGAM.read();
                Serial.write(H = TGAM.read());
                Serial.write(L = TGAM.read());
                Serial.write(checksum = TGAM.read());
                Serial.write(~(130+H+L)&0xff == checksum);
                return;
            #endif

            TGAM.read(); TGAM.read(); // skip 80 and 02
            uint16_t HD = TGAM.read();
            uint8_t  LD = TGAM.read();
            if ( ~(0x80+0x02+HD+LD) & 0xff != TGAM.read() ) {
                #ifdef DEBUG
                    Serial.println(F("Throw raw"));
                #endif
                return;
            }
            result += "," + String( (int)(HD << 8 | LD) );
            Serial.println(String(millis()) + result);
        }
    #endif

    #ifdef PACKAGE
        // e.g. aa aa|20|02 c8|83 18
        //      0c 32 82|0b 61 76|01 06 a9|00 7b 4a
        //      02 86 b3|03 2f 52|01 e7 e1|12 11 c2
        //      04 00|05 00|0d
        if (length == 32) {
            uint8_t data, checksum = 0x02+0x83+0x18+0x04+0x05;
            uint32_t h;
            uint16_t m;
            uint8_t  l;

            // signal
            TGAM.read(); // skip 02
            checksum += (data = TGAM.read());
            result += "," + String(data);

            // spectrum
            TGAM.read(); TGAM.read(); // skip 83 and 18
            for (uint8_t i=0; i<8; i++) {
                h = TGAM.read(); m = TGAM.read(); l = TGAM.read();
                result += "," + String( (int)(h << 16 | m << 8 | l) );
                checksum += h + m + l;
            }

            // attention
            TGAM.read(); // skip 04
            checksum += (data = TGAM.read());
            result += "," + String(data);

            // meditation
            TGAM.read(); // skip 05
            checksum += (data = TGAM.read());
            result += "," + String(data);

            if ( (~checksum & 0xff) != TGAM.read() ) {
                #ifdef DEBUG
                    Serial.println(F("Throw package"));
                #endif
                return;
            }
            Serial.println(String(millis()) + result);
        }
    #endif
}
