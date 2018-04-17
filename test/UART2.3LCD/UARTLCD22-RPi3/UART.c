#include <stdio.h>
#include <wiringPi.h>
#include <wiringSerial.h>

int main()
{
	int fd;
	if(wiringPiSetup() < 0)return 1;
//	if((fd = serialOpen("/dev/ttyAMA0",115200)) < 0)return 1;
	if((fd = serialOpen("/dev/ttyS0",115200)) < 0)return 1;

	printf("serial test start ...\n");
	delay(800);
        serialPrintf(fd,"RESET;\r\n");//reset the LCD
	delay(100);
        serialPrintf(fd,"BPS(115200);\r\n");//Set Baud rate
        delay(100);
	serialPrintf(fd,"CLR(0);\r\n");//Clean LCD with black color
        delay(100);
        serialPrintf(fd,"CLR(1);\r\n");//Clean LCD with red color
        delay(100);
        serialPrintf(fd,"CLR(15);\r\n");//Clean LCD with white color
        delay(100);
        serialPrintf(fd,"DIR(0);\r\n");//Vertical display 
        delay(100);
	serialPrintf(fd,"DCV24(0,0,spotpear,0);\r\n");
//display "spotpear" at coordinate（0.0），Font color ：0-black；background color ：default black
        delay(100);
        serialPrintf(fd,"SBC(1);\r\n");//set  background color red
        delay(100);
        serialPrintf(fd,"DCV24(0,24,spotpear,0);\r\n");
//display "spotpear" at coordinate（X-0.Y-24）
        delay(500);
        serialPrintf(fd,"DCV24(0,24,spotpear,3);\r\n");//，Font color ：3-;
        delay(500);
	serialPrintf(fd,"CLR(0);\r\n");//Clean LCD with black color
	delay(500);
	serialPrintf(fd,"DIR(1);\r\n");//Horizontal display
        delay(500);
	serialPrintf(fd,"DCV16(0,24,spotpear,0);\r\n");
        delay(500);
        serialPrintf(fd,"DCV32(0,0,spotpear,0);\r\n");
        delay(500);
        serialPrintf(fd,"CIRF(40,80,20,3);\r\n");//filling circle coordinate（X-40.Y-80,r-20,color-3）
        delay(100);
        serialPrintf(fd,"CIR(70,150,20,1);\r\n");//circle coordinate（X-70.Y-150,r-20,color-1）
        delay(500);
        serialPrintf(fd,"BOXF(70,150,90,170,3);\r\n");//rectangle  coordinate
        delay(500);
        serialPrintf(fd,"BOX(40,80,70,110,3);\r\n");//rectangle  coordinate
        delay(500);
        serialPrintf(fd,"PL(0,0,220,176,6);\r\n");//line: color-6,
        delay(500);
        serialPrintf(fd,"PS(110,110,4);\r\n");//line: color-6,
        delay(1000);
        serialPrintf(fd,"DIR(0);\r\n");//Vertical display
        delay(100);
        serialPrintf(fd,"FSIMG(2097152,0,0,176,220,0);\r\n");
//load picture-1 from LCD（picture loaded by computer UART software in advance）
        delay(500);
        serialPrintf(fd,"FSIMG(2174592,0,0,176,220,0);\r\n");//load picture-2 from LCD
        delay(500);
        serialPrintf(fd,"FSIMG(2252032,0,0,176,220,0);\r\n");
        delay(500);
        serialPrintf(fd,"BL(1023);\r\n");////Backlight ightness:1024-open display
        delay(1000);
        serialPrintf(fd,"BL(0);\r\n");//Backlight ightness:0-stop display
        delay(300);
//        serialPrintf(fd,"RESET;\r\n");//reset*/
//        delay(300);
        serialPrintf(fd,"DCV24(0,0,spotpear,0);\r\n");
        delay(300);
	//while(1)
	//{
	//	serialPutchar(fd,serialGetchar(fd));
	//}
	serialClose(fd);
	return 0;
}
