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


import sys
import os
import termios
import fcntl
import select
import subprocess
import simplejson as json

# import sentry_sdk
# sentry_sdk.init("https://5644cfdc9bd24dfbaadea6bc867a8f5b@sentry.io/1803681")

# Append parent directory to be able to import files
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import expandLogMessage
import BrewPiUtil as util

# Read in command line arguments
if len(sys.argv) < 2:
    print("\nUsing default config path ./settings/config.cfg, to override use:", file=sys.stderr)
    print("%s <config file full path>" % sys.argv[0], file=sys.stderr)
    configFile = util.addSlash(sys.path[0]) + '../settings/config.cfg'
else:
    configFile = sys.argv[1]

if not os.path.exists(configFile):
    sys.exit('ERROR: Config file "%s" was not found.' % configFile)

config = util.readCfgWithDefaults(configFile)

print("\n        ********     BrewPi Terminal     *******")
print("This simple Python script lets you send commands to the controller. It")
print("also echoes everything the controller returns. On known debug ID's in")
print("JSON format, it expands the messages to the full message.\n")
print("Press 's' to send a string to the controller, press 'q' to quit")

# open serial port
ser = util.setupSerial(config)

if not ser:
    print("Unable to open serial port; is script still running?")
    exit(1)

try:
    fd = sys.stdin.fileno()

    oldterm = termios.tcgetattr(fd)
    oldflags = fcntl.fcntl(fd, fcntl.F_GETFL)

    newattr = termios.tcgetattr(fd)
    newattr[3] = newattr[3] & ~termios.ICANON
    newattr[3] = newattr[3] & ~termios.ECHO

    while True:
        termios.tcsetattr(fd, termios.TCSANOW, newattr)
        fcntl.fcntl(fd, fcntl.F_SETFL, oldflags | os.O_NONBLOCK)
        inp, outp, err = select.select([sys.stdin], [], [])
        received = sys.stdin.read()
        if received == 'q':
            ser.close()
            break
        elif received == 's':
            termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
            fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
            userInput = input("Type the string you want to send to the controller: ")
            print("Sending: " + userInput)
            ser.write(userInput.encode(encoding="cp437"))

        line = ser.readline()
        line = util.asciiToUnicode(line)
        line = line.decode(encoding="cp437")
        if line:
            if(line[0]=='D'):
                try:
                    decoded = json.loads(line[2:])
                    print("Debug message received: " + expandLogMessage.expandLogMessage(line[2:]))
                except json.JSONDecodeError:
                    # Print line normally, is not json
                    print("Debug message received: " + line[2:])

            else:
                print(line)


finally:
    # Reset the terminal:
    termios.tcsetattr(fd, termios.TCSAFLUSH, oldterm)
    fcntl.fcntl(fd, fcntl.F_SETFL, oldflags)
