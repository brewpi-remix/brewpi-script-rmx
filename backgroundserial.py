#!/usr/bin/python3

# Copyright (C) 2018, 2019 Lee C. Bussy (@LBussy)

# This file is part of LBussy's BrewPi Script Remix (BrewPi-Script-RMX).
#
# BrewPi Script RMX is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# BrewPi Script RMX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BrewPi Script RMX. If not, see <https://www.gnu.org/licenses/>.

# These scripts were originally a part of brewpi-script, a part of
# the BrewPi project. Legacy support (for the very popular Arduino
# controller) seems to have been discontinued in favor of new hardware.

# All credit for the original brewpi-script goes to @elcojacobs,
# @m-mcgowan, @rbrady, @steersbob, @glibersat, @Niels-R and I'm sure
# many more contributors around the world. My apologies if I have
# missed anyone; those were the names listed as contributors on the
# Legacy branch.

# See: 'original-license.md' for notes about the original project's
# license and credits.


import threading
import queue
import sys
import time
from BrewPiUtil import printStdErr
from BrewPiUtil import logMessage
from serial import SerialException
from expandLogMessage import filterOutLogMessages

import BrewPiUtil

class BackGroundSerial():
    def __init__(self, serial_port):
        self.buffer = ''
        self.ser = serial_port
        self.queue = queue.Queue()
        self.messages = queue.Queue()
        self.thread = None
        self.error = False
        self.fatal_error = None
        self.run = False

    # public interface only has 4 functions: start/stop/read_line/write
    def start(self):
        # write timeout will occur when there are problems with the serial port.
        # without the timeout loosing the serial port goes undetected.
        self.ser.write_timeout = 2
        self.run = True
        if not self.thread:
            self.thread = threading.Thread(target=self.__listenThread)
            self.thread.setDaemon(True)
            self.thread.start()

    def stop(self):
        self.run = False
        if self.thread:
            self.thread.join() # wait for background thread to terminate
            self.thread = None

    def read_line(self):
        self.exit_on_fatal_error()
        try:
            return self.queue.get_nowait()
        except queue.Empty:
            return None

    def read_message(self):
        self.exit_on_fatal_error()
        try:
            return self.messages.get_nowait()
        except queue.Empty:
            return None

    def write(self, data):
        self.exit_on_fatal_error()
        # prevent writing to a port in error state. This will leave unclosed handles to serial on the system
        if not self.error:
            try:
                if hasattr(data, 'encode'):
                    # Encode if it's not already done
                    self.ser.write(data.encode(encoding='cp437'))
                else:
                    self.ser.write(data)
            except (IOError, OSError, SerialException) as e:
                logMessage('Serial Error: {0})'.format(str(e)))
                self.error = True

    def exit_on_fatal_error(self):
        if self.fatal_error is not None:
            self.stop()
            logMessage(self.fatal_error)
            if self.ser is not None:
                self.ser.close()
            del self.ser # this helps to fully release the port to the OS
            raise Exception("Terminating due to fatal serial error")

    def __listenThread(self):
        lastReceive = time.time()
        while self.run :
            in_waiting = None
            new_data = None
            if not self.error:
                try:
                    #in_waiting = self.ser.inWaiting() # WiFi Change
                    in_waiting = self.ser.readline()
                    if in_waiting:
                        #new_data = self.ser.read(in_waiting) # WiFi Change
                        new_data = in_waiting
                        lastReceive = time.time()
                except (IOError, OSError, SerialException) as e:
                    logMessage('Serial Error: {0})'.format(str(e)))
                    self.error = True

            if new_data:
                self.buffer = self.buffer + new_data.decode(encoding="cp437")
                line = self.__get_line_from_buffer()
                if line:
                    self.queue.put(line)

            if self.error:
                try:
                    # try to restore serial by closing and opening again
                    self.ser.close()
                    self.ser.open()
                    self.error = False
                except (ValueError, OSError, SerialException) as e:
                    if self.ser.isOpen():
                        self.ser.flushInput() # will help to close open handles
                        self.ser.flushOutput() # will help to close open handles
                    self.ser.close()
                    self.fatal_error = 'Lost serial connection. Error: {0})'.format(str(e))
                    self.run = False

            # max 10 ms delay. At baud 57600, max 576 characters are received while waiting
            time.sleep(0.01)

    def __get_line_from_buffer(self):
        while '\n' in self.buffer:
            stripped_buffer, messages = filterOutLogMessages(self.buffer)
            if len(messages) > 0:
                for message in messages:
                    self.messages.put(message[2:]) # remove D: and add to queue
                self.buffer = stripped_buffer
                continue
            lines = self.buffer.partition('\n') # returns 3-tuple with line, separator, rest
            if(lines[1] == ''):
                # '\n' not found, first element is incomplete line
                self.buffer = lines[0]
                return None
            else:
                # complete line received, [0] is complete line [1] is separator [2] is the rest
                self.buffer = lines[2]
                return self.__asciiToUnicode(lines[0])

    # remove extended ascii characters from string, because they can raise UnicodeDecodeError later
    def __asciiToUnicode(self, s):
        return BrewPiUtil.asciiToUnicode(s)

if __name__ == '__main__':
    # some test code that requests data from serial and processes the response json
    import simplejson
    import time
    import BrewPiUtil as util

    config_file = util.addSlash(sys.path[0]) + 'settings/config.cfg'
    config = util.readCfgWithDefaults(config_file)
    ser = util.setupSerial(config)
    if not ser:
        printStdErr("Could not open Serial Port")
        exit()

    bg_ser = BackGroundSerial(ser)
    bg_ser.start()

    success = 0
    fail = 0
    for i in range(1, 5):
        # request control variables 4 times. This would overrun buffer if it was not read in a background thread
        # the json decode will then fail, because the message is clipped
        bg_ser.write('v')
        bg_ser.write('v')
        bg_ser.write('v')
        bg_ser.write('v')
        bg_ser.write('v')
        line = True
        while(line):
            line = bg_ser.read_line()
            if line:
                if line[0] == 'V':
                    try:
                        decoded = simplejson.loads(line[2:])
                        print("Success")
                        success += 1
                    except simplejson.JSONDecodeError:
                        logMessage("Error: invalid JSON parameter string received: " + line)
                        fail += 1
                else:
                    print(line)
        time.sleep(5)

    print("Successes: {0}, Fails: {1}".format(success,fail))
