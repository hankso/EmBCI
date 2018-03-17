/*
  Software serial multple serial test

  Receives from the hardware serial, sends to software serial.
  Receives from software serial, sends to hardware serial.

  The circuit:
   RX is digital pin 10 (connect to TX of other device)
   TX is digital pin 11 (connect to RX of other device)

  Note:
  Not all pins on the Mega and Mega 2560 support change interrupts,
  so only the following can be used for RX:
  10, 11, 12, 13, 50, 51, 52, 53, 62, 63, 64, 65, 66, 67, 68, 69

  Not all pins on the Leonardo support change interrupts,
  so only the following can be used for RX:
  8, 9, 10, 11, 14 (MISO), 15 (SCK), 16 (MOSI).

  created back in the mists of time
  modified 25 May 2012
  by Tom Igoe
  based on Mikal Hart's example

  This example code is in the public domain.

*/
//#include <SoftwareSerial.h>
//
//SoftwareSerial TGAM(3, 4); // RX, TX

void setup()
{
    Serial.begin(115200);
//    Serial.begin(57600);
//    TGAM.begin(115200);
//    TGAM.begin(57600);

//    pinMode(13, OUTPUT);
//    pinMode(1, OUTPUT);
//    pinMode(A0, INPUT);

//    TGAM.println("Displaying...");
//    TGAM.println("testing thydsrweqghoewjfpewjoweqguhrkd;lsfejwfaesfee");
//    String s = "hank1234567890";
//    TGAM.println("test - " + s);
    // Serial.println(F("connected"));
}

void loop()
{
//    TGAM.write('H');
//    digitalWrite(1, HIGH);
//    delay(100);
//    TGAM.write('L');
//    digitalWrite(1, LOW);
//    delay(100);

//    Serial.write('H');
//    digitalWrite(13, HIGH);
//    delay(100);
//    Serial.write('L');
//    digitalWrite(13, LOW);
//    delay(100);

//   while (Serial.available()) {
//       char temp = Serial.read();
//       if (temp == 'H'){
//           digitalWrite(13, HIGH);
//       }
//       if (temp == 'L'){
//           digitalWrite(13, LOW);
//       }
//       Serial.write(temp);
//   }
//    delay(10);
//    Serial.println(analogRead(A0));
//    while (TGAM.available()) {
//        char temp = TGAM.read();
//        if (temp == 'H'){
//            digitalWrite(1, HIGH);
//        }
//        if (temp == 'L'){
//            digitalWrite(1, LOW);
//        }
//    }

//  while (TGAM.available()) {
//    char temp = TGAM.read();
//   Serial.write(temp);
    // Serial.print(temp);
//    String msg = TGAM.readStringUntil('\n');
//    TGAM.println("You sent " + msg);
//  }
}
