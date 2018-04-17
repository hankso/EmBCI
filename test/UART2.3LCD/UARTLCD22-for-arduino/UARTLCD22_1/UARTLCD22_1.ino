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
  delay(100);
  mySerial.println("BPS(115200);\r\n");
  delay(100);
  mySerial.println("CLR(1);\r\n");
  delay(500);
  mySerial.println("CLR(15);\r\n");
  delay(500);
  mySerial.println("DIR(0);\r\n");
  delay(100);
  mySerial.println("DCV24(0,0,spotpear,0);\r\n");
  delay(100);
  mySerial.println("SBC(1);\r\n");
  delay(100);
  mySerial.println("DCV24(0,24,spotpear,0);\r\n");
  delay(300);
  mySerial.println("DCV24(0,24,spotpear,3);\r\n");
  delay(300);
  mySerial.println("CLR(0);\r\n");
  delay(300);

  mySerial.println("FSIMG(2097152,0,0,176,220,0);\r\n");
  delay(300);  
  mySerial.println("FSIMG(2174592,0,0,176,220,0);\r\n");
  delay(300);  
  mySerial.println("FSIMG(2252032,0,0,176,220,0);\r\n");
  delay(300);  
  mySerial.println("BL(1023);\r\n");
  delay(1000); 
  mySerial.println("BL(0);\r\n");
  delay(1000);

}

void loop() // run over and over
{
  delay(300);
}

