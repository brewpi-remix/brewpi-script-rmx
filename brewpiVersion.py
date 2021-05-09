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


import simplejson as json
import sys
import time
from packaging import version
from BrewPiUtil import asciiToUnicode
from serial import SerialException

def getVersionFromSerial(ser):
    version = None
    retries = 0
    oldTimeOut = ser.timeout
    startTime = time.time()
    if not ser.isOpen():
        print("\nCannot get version from serial port that is not open.")

    ser.timeout = 1
    ser.write('n'.encode(encoding="cp437"))  # Request version info
    while retries < 10:
        retry = True
        while 1: # Read all lines from serial
            loopTime = time.time()
            line = None
            try:
                line = ser.readline()
                if hasattr(line, 'decode'):
                    line = line.decode(encoding="cp437")
            except SerialException as e:
                pass
            if line:
                line = asciiToUnicode(line)
                if line[0] == 'N':
                    data = line.strip('\n')[2:]
                    version = AvrInfo(data)
                    if version and version.version != "0.0.0":
                        retry = False
                        break
            if time.time() - loopTime >= ser.timeout:
                # Have read entire buffer, now just reading data as it comes in. Break to prevent an endless loop
                break
            if time.time() - startTime >= 10:
                # Try max 10 seconds
                retry = False
                break

        if retry:
            ser.write('n'.encode(encoding="cp437"))  # request version info
            retries += 1
        else:
            break
    ser.timeout = oldTimeOut # Restore previous serial timeout value
    return version

class AvrInfo:
    """ Parses and stores the version and other compile-time details reported by the controller. """

    version = "v"
    build = "n"
    simulator = "y"
    board = "b"
    shield = "s"
    log = "l"
    commit = "c"

    shield_diy = "DIY"
    shield_revA = "revA"
    shield_revC = "revC"
    spark_shield_v1 = "V1"
    spark_shield_v2 = "V2"
    shield_i2c = "I2C"
    shield_glycol = "Glycol"

    shields = {
            0: shield_diy,
            1: shield_revA,
            2: shield_revC,
            3: spark_shield_v1,
            4: spark_shield_v2,
            5: shield_i2c,
            6: shield_glycol
    }

    board_leonardo = "leonardo"
    board_standard = "uno"
    board_mega = "mega"
    board_spark_core = "core"
    board_photon = "photon"
    board_esp8266 = "esp8266"

    boards = {'l': board_leonardo, 's': board_standard, 'm': board_mega, 'x': board_spark_core, 'y': board_photon, 'e': board_esp8266}

    family_arduino = "Arduino"
    family_spark = "Particle"
    family_esp8266 = "ESP8266"

    families = { board_leonardo: family_arduino,
                board_standard: family_arduino,
                board_mega: family_arduino,
                board_spark_core: family_spark,
                board_photon: family_spark,
                board_esp8266: family_esp8266}

    board_names = { board_leonardo: "Leonardo",
                board_standard: "Uno",
                board_mega: "Mega",
                board_spark_core: "Core",
                board_photon: "Photon",
                board_esp8266: "ESP8266"}

    def __init__(self, s=None):
        self.version = version.parse("0.0.0")
        self.build = 0
        self.commit = None
        self.simulator = False
        self.board = None
        self.shield = None
        self.log = 0
        self.parse(s)

    def parse(self, s):
        if s is None or len(s) == 0:
            pass
        else:
            s = s.strip()
            if s[0] == '{':
                self.parseJsonVersion(s)
            else:
                self.parseStringVersion(s)

    def parseJsonVersion(self, s):
        j = None
        try:
            j = json.loads(s)
        except json.decoder.JSONDecodeError as e:
            print("JSON decode error: %s" % str(e), file=sys.stderr)
            print("Could not parse version number: " + s, file=sys.stderr)
        except UnicodeDecodeError as e:
            print("Unicode decode error: %s" % str(e), file=sys.stderr)
            print("Could not parse version number: " + s, file=sys.stderr)
        except TypeError as e:
            print("TypeError: %s" % str(e), file=sys.stderr)
            print("Could not parse version number: " + s, file=sys.stderr)

        self.family = None
        self.board_name = None
        if not j:
            return
        if AvrInfo.version in j:
            self.parseStringVersion(j[AvrInfo.version])
        if AvrInfo.simulator in j:
            self.simulator = j[AvrInfo.simulator] == 1
        if AvrInfo.board in j:
            self.board = AvrInfo.boards.get(j[AvrInfo.board])
            self.family = AvrInfo.families.get(self.board)
            self.board_name = AvrInfo.board_names.get(self.board)
        if AvrInfo.shield in j:
            self.shield = AvrInfo.shields.get(j[AvrInfo.shield])
        if AvrInfo.log in j:
            self.log = j[AvrInfo.log]
        if AvrInfo.build in j:
            self.build = j[AvrInfo.build]
        if AvrInfo.commit in j:
            self.commit = j[AvrInfo.commit]

    def parseStringVersion(self, s):
        self.version = version.parse(s)

    def toString(self):
        if self.version:
            return str(self.version)
        else:
            return "0.0.0"

    def article(self, word):
        if not word:
            return "a" # in case word is not valid
        firstLetter = word[0]
        if firstLetter.lower() in 'aeiou':
            return "an"
        else:
            return "a"

    def toExtendedString(self):
        string = "BrewPi v" + self.toString()
        if self.build:
            string += " build " + str(self.build)
        if self.board:
            string += ", running on "+ self.articleFullName()
        if self.shield:
            string += " with " + self.article(str(self.shield)) + " "
            string += str(self.shield) + " shield"
        if(self.simulator):
            string += ", running as simulator."
        return string

    def isNewer(self, versionString):
        return self.version < version.parse(versionString)

    def isEqual(self, versionString):
        return self.version == version.parse(versionString)

    def familyName(self):
        family = AvrInfo.families.get(self.board)
        if family == None:
            family = "????"
        return family

    def boardName(self):
        board = AvrInfo.board_names.get(self.board)
        if board == None:
            board = "????"
        return board

    def fullName(self):
        return self.familyName() + " " + self.boardName()

    def articleFullName(self):
        return self.article(self.family) + " " + self.fullName()
