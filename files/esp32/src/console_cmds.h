/*
 File: console_cmds.h
 Authors: Hank <hankso1106@gmail.com>
 Create: 2019-04-19 16:53:48

 ESP32 console to support command line interface.
 
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

#ifndef CONSOLE_CMDS_H
#define CONSOLE_CMDS_H

/*
 *  Currently registered commands:
 *      ADS1299
 *        - sample_rate
 *        - input_source
 *        - bias_output
 *        - impedance
 *      SPI Buffer
 *        - clear
 *        - reset
 *        - output
 *      WiFi
 *        - connect
 *        - disconnect
 *        - echoing
 *      Power management
 *        - sleep
 *        - reboot
 *        - shutdown
 *        - battery
 *      Utilities
 *        - verbose
 *        - quiet
 *        - summary
 *        - version
 *        - tasks
 */
void register_commands();

/*
 * Config and init console. register_commands is called at the end.
 */
void initialize_console();

/*
 * (R) Read from console stream (wait until command input).
 * (E) parse and Execute the command. 
 * (P) then Print the result.
 */
void handle_console();

/*
 * (L) endless Loop of handle_console.
 */
void console_loop(void*);

#endif // CONSOLE_CMDS_H
