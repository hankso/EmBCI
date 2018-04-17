/*
  Software serial multple serial test
 
 Receives from the hardware serial, sends to software serial.
 Receives from software serial, sends to hardware serial.
 
 The circuit: 
 * RX is digital pin 10 (connect to TX of other device)
 * TX is digital pin 11 (connect to RX of other device)
 
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
#include <SoftwareSerial.h>

SoftwareSerial mySerial(10, 11); // RX, TX

void setup()  
{
  mySerial.begin(115200);
  delay(800);
  mySerial.println("RESET;\r\n");
  delay(300);
  mySerial.println("DIR(1);\r\n");
  delay(500);
  mySerial.println("CLR(0);\r\n");
  delay(500); 
  
  mySerial.println("DCV16(0,24,spotpear,0);\r\n");
  delay(300);
  mySerial.println("DCV32(0,0,spotpear,0);\r\n");
  delay(300);
  mySerial.println("CIRF(40,80,20,3);\r\n");
  delay(300);
  mySerial.println("CIR(70,150,20,1);\r\n");
  delay(300);
  mySerial.println("BOXF(70,150,90,170,3);\r\n");
  delay(300);
  mySerial.println("BOX(40,80,70,110,3);\r\n");
  delay(300);
  mySerial.println("PL(0,0,220,176,6);\r\n");
  delay(300);
  mySerial.println("PS(110,110,4);\r\n");
  delay(300);
}

void loop() // run over and over
{
  delay(1000);  
}

