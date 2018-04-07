//#include <Servo.h>

//Servo hand;
/*
Read analog value from myo module on arduino. Sat, Feb 24 2018 17:25
*/

#define myoRaw A7
#define myoSig A6
#define sample_rate 512

uint32_t stamp = micros();

void setup() {
    pinMode(myoRaw, INPUT);
    pinMode(myoSig, INPUT);
//    hand.attach(2);
    Serial.begin(115200);
    Serial.println("started");
}

void loop() {
    while ((micros() - stamp) < 1000000.0/sample_rate) {;}
//    Serial.write(analogRead(myoRaw)/4);
//    Serial.write(analogRead(myoSig)/4);
//    Serial.printf("%d,%d\n", analogRead(myoRaw),analogRead(myoSig));
    Serial.println(analogRead(myoRaw));
    stamp = micros();

//    if (Serial.available()) {
//      char degree = Serial.parseInt();
//      if (degree < 180 && degree > 0)
//        hand.write(degree);
//    }
//    Serial.write(" ");
}
