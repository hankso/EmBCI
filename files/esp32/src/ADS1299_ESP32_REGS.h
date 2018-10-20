#ifndef _ADS1299_ESP32_REGS_H_INCLUDED
#define _ADS1299_ESP32_REGS_H_INCLUDED

//Commands
#define ADS_WAKEUP    0x02
#define ADS_STANDBY   0x04
#define ADS_RESET     0x06
#define ADS_START     0x08
#define ADS_STOP      0x0A
#define ADS_RDATAC    0x10
#define ADS_SDATAC    0x11
#define ADS_RDATA     0x12
#define ADS_RREG      0x20
#define ADS_WREG      0x40

//Registers
#define ADS_ID        0x00
#define ADS_CONFIG1   0x01
#define ADS_CONFIG2   0x02
#define ADS_CONFIG3   0x03
#define ADS_CONFIG4   0x04
#define ADS_CH1SET    0x05
#define ADS_CH2SET    0x06
#define ADS_CH3SET    0x07
#define ADS_CH4SET    0x08
#define ADS_CH5SET    0x09
#define ADS_CH6SET    0x0A
#define ADS_CH7SET    0x0B
#define ADS_CH8SET    0x0C
#define ADS_BIAS_SENSP  0x0D
#define ADS_BIAS_SENSN  0x0E
#define ADS_LOFF_SENSP  0x0F
#define ADS_LOFF_SENSN  0x10
#define ADS_LOFF_FLIP   0x11
#define ADS_LOFF_STATP  0x12
#define ADS_LOFF_STATN  0x13
#define ADS_GPIO      0x14
#define ADS_MISC1     0x15
#define ADS_MISC2     0x16
//#define ADS_CONFIG4   0x17

#endif
