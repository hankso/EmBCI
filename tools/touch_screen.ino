#include <Arduino.h>

#define FS 20

#define X0 A0
#define X1 A1
#define Y0 A2
#define Y1 A3

#define Width 220
#define Height 176

uint16_t x=0, y=0;
bool p=false;

void setup()
{
    Serial.begin(115200);
    // Serial.println("start!");
}

void loop()
{
    delay(1000/FS);
    read_position(&x, &y, &p);
    if (p)
    {
        // Serial.printf("PS(%d,%d,1);\n", x, y);
        Serial.printf("%d,%d\n", x, y);
    }
    if (Serial.available() >= 3)
    {
        if (Serial.read() == 170 &&
            Serial.read() == 170 &&
            Serial.read() == 170)
        {
            Serial.println("0,0,0");
        }
    }
}

void read_position(uint16_t *x, uint16_t *y, bool *P)
{
    /* check if screen been touched */
    pinMode(X0, OUTPUT);
    pinMode(X1, INPUT);
    pinMode(Y0, OUTPUT);
    pinMode(Y1, INPUT);
    digitalWrite(X0, LOW);
    digitalWrite(Y0, HIGH);
    *P = (analogRead(X1) != LOW) && (analogRead(Y1) != HIGH);
    if (*P)
    {
        // read y position
        pinMode(X0, OUTPUT);
        pinMode(X1, OUTPUT);
        pinMode(Y0, INPUT);
        pinMode(Y1, INPUT);
        digitalWrite(X0, LOW);
        digitalWrite(X1, HIGH);
        *y = (analogRead(Y0) + analogRead(Y1)) / 2;
        *y = (uint16_t)((float)*y * Height / 1024);

        // read x position
        pinMode(Y0, OUTPUT);
        pinMode(Y1, OUTPUT);
        pinMode(X0, INPUT);
        pinMode(X1, INPUT);
        digitalWrite(Y0, LOW);
        digitalWrite(Y1, HIGH);
        *x = (analogRead(X0) + analogRead(X1)) / 2;
        *x = (uint16_t)((float)*x * Width / 1024);
    }
}
