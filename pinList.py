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

def getPinList(boardType, shieldType):
    if boardType == "leonardo" and shieldType == "revC":
        pinList = [{'val': 6, 'text': ' 6 (Act 1)', 'type': 'act'},
                   {'val': 5, 'text': ' 5 (Act 2)', 'type': 'act'},
                   {'val': 2, 'text': ' 2 (Act 3)', 'type': 'act'},
                   {'val': 23, 'text': 'A5 (Act 4)', 'type': 'act'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 22, 'text': 'A4 (OneWire)', 'type': 'onewire'},
                   {'val': 3, 'text': ' 3', 'type': 'beep'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, ' text': '10', 'type': 'spi'},
                   {'val': 0, 'text': ' 0', 'type': 'free'},
                   {'val': 1, 'text': ' 1', 'type': 'free'},
                   {'val': 11, ' text': '11', 'type': 'free'},
                   {'val': 12, ' text': '12', 'type': 'free'},
                   {'val': 13, ' text': '13', 'type': 'free'},
                   {'val': 18, 'text': 'A0', 'type': 'free'},
                   {'val': 19, 'text': 'A1', 'type': 'free'},
                   {'val': 20, 'text': 'A2', 'type': 'free'},
                   {'val': 21, 'text': 'A3', 'type': 'free'}]
    elif boardType == "uno" and shieldType == "revC":
        pinList = [{'val': 0, 'text': ' 0', 'type': 'serial'},
                   {'val': 1, 'text': ' 1', 'type': 'serial'},
                   {'val': 2, 'text': ' 2 (Act 3)', 'type': 'act'},
                   {'val': 3, 'text': ' 3', 'type': 'beep'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 5, 'text': ' 5 (Act 2)', 'type': 'act'},
                   {'val': 6, 'text': ' 6 (Act 1)', 'type': 'act'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, ' text': '10', 'type': 'spi'},
                   {'val': 11, ' text': '11', 'type': 'spi'},
                   {'val': 12, ' text': '12', 'type': 'spi'},
                   {'val': 13, ' text': '13', 'type': 'spi'},
                   {'val': 14, 'text': 'A0', 'type': 'free'},
                   {'val': 15, 'text': 'A1', 'type': 'free'},
                   {'val': 16, 'text': 'A2', 'type': 'free'},
                   {'val': 17, 'text': 'A3', 'type': 'free'},
                   {'val': 18, 'text': 'A4 (OneWire)', 'type': 'onewire'},
                   {'val': 19, 'text': 'A5 (Act 4)', 'type': 'act'}]
    elif boardType == "uno" and shieldType == "I2C":
        pinList = [{'val': 0, 'text': ' 0', 'type': 'serial'},
                   {'val': 1, 'text': ' 1', 'type': 'serial'},
                   {'val': 2, 'text': ' 2 (Act 3)', 'type': 'act'},
                   {'val': 3, 'text': ' 3 (Alarm)', 'type': 'beep'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 5, 'text': ' 5 (Act 1)', 'type': 'act'},
                   {'val': 6, 'text': ' 6 (Act 2)', 'type': 'act'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, 'text': '10 (Act 4)', 'type': 'act'},
                   {'val': 11, 'text': '11', 'type': 'free'},
                   {'val': 12, 'text': '12', 'type': 'free'},
                   {'val': 13, 'text': '13', 'type': 'free'},
                   {'val': 14, 'text': 'A0 (OneWire)', 'type': 'onewire'},
                   {'val': 15, 'text': 'A1 (OneWire)', 'type': 'free'},
                   {'val': 16, 'text': 'A2 (OneWire)', 'type': 'free'},
                   {'val': 17, 'text': 'A3 (Act 4)', 'type': 'act'},
                   {'val': 18, 'text': 'A4 (SDA)', 'type': 'i2c'},
                   {'val': 19, 'text': 'A5 (SCL)', 'type': 'i2c'}]
    elif boardType == "uno" and shieldType == "Glycol":
        pinList = [{'val': 0, 'text': ' 0', 'type': 'serial'},
                   {'val': 1, 'text': ' 1', 'type': 'serial'},
                   {'val': 2, 'text': ' 2 (Act 3)', 'type': 'act'},
                   {'val': 3, 'text': ' 3 (Alarm)', 'type': 'beep'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 5, 'text': ' 5 (Act 1)', 'type': 'act'},
                   {'val': 6, 'text': ' 6 (Act 2)', 'type': 'act'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, 'text': '10 (Act 4)', 'type': 'act'},
                   {'val': 11, 'text': '11', 'type': 'free'},
                   {'val': 12, 'text': '12', 'type': 'free'},
                   {'val': 13, 'text': '13', 'type': 'free'},
                   {'val': 14, 'text': 'A0 (OneWire)', 'type': 'onewire'},
                   {'val': 15, 'text': 'A1 (OneWire)', 'type': 'free'},
                   {'val': 16, 'text': 'A2 (OneWire)', 'type': 'free'},
                   {'val': 17, 'text': 'A3 (Act 4)', 'type': 'act'},
                   {'val': 18, 'text': 'A4 (SDA)', 'type': 'i2c'},
                   {'val': 19, 'text': 'A5 (SCL)', 'type': 'i2c'}]
    elif boardType == "leonardo" and shieldType == "revA":
        pinList = [{'val': 6, 'text': '  6 (Cool)', 'type': 'act'},
                   {'val': 5, 'text': '  5 (Heat)', 'type': 'act'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 22, 'text': 'A4 (OneWire)', 'type': 'onewire'},
                   {'val': 23, 'text': 'A5 (OneWire1)', 'type': 'onewire'},
                   {'val': 3, 'text': ' 3', 'type': 'beep'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, ' text': '10', 'type': 'spi'},
                   {'val': 0, 'text': ' 0', 'type': 'free'},
                   {'val': 1, 'text': ' 1', 'type': 'free'},
                   {'val': 2, 'text': '  2', 'type': 'free'},
                   {'val': 11, ' text': '11', 'type': 'free'},
                   {'val': 12, ' text': '12', 'type': 'free'},
                   {'val': 13, ' text': '13', 'type': 'free'},
                   {'val': 18, 'text': 'A0', 'type': 'free'},
                   {'val': 19, 'text': 'A1', 'type': 'free'},
                   {'val': 20, 'text': 'A2', 'type': 'free'},
                   {'val': 21, 'text': 'A3', 'type': 'free'}]
    elif boardType == "uno" and shieldType == "revA":
        pinList = [{'val': 6, 'text': '  6 (Cool)', 'type': 'act'},
                   {'val': 5, 'text': '  5 (Heat)', 'type': 'act'},
                   {'val': 4, 'text': ' 4 (Door)', 'type': 'door'},
                   {'val': 18, 'text': 'A4 (OneWire)', 'type': 'onewire'},
                   {'val': 19, 'text': 'A5 (OneWire1)', 'type': 'onewire'},
                   {'val': 3, 'text': ' 3', 'type': 'beep'},
                   {'val': 7, 'text': ' 7', 'type': 'rotary'},
                   {'val': 8, 'text': ' 8', 'type': 'rotary'},
                   {'val': 9, 'text': ' 9', 'type': 'rotary'},
                   {'val': 10, ' text': '10', 'type': 'spi'},
                   {'val': 11, ' text': '11', 'type': 'spi'},
                   {'val': 12, ' text': '12', 'type': 'spi'},
                   {'val': 13, ' text': '13', 'type': 'spi'},
                   {'val': 0, 'text': ' 0', 'type': 'serial'},
                   {'val': 1, 'text': ' 1', 'type': 'serial'},
                   {'val': 2, 'text': '  2', 'type': 'free'},
                   {'val': 14, 'text': 'A0', 'type': 'free'},
                   {'val': 15, 'text': 'A1', 'type': 'free'},
                   {'val': 16, 'text': 'A2', 'type': 'free'},
                   {'val': 17, 'text': 'A3', 'type': 'free'}]
    elif boardType == "leonardo" and shieldType == "diy":
        pinList = [{'val': 12, 'text': '  12 (Cool)', 'type': 'act'},
                   {'val': 13, 'text': '  13 (Heat)', 'type': 'act'},
                   {'val': 23, 'text': ' A5 (Door)', 'type': 'door'},
                   {'val': 10, 'text': '10 (OneWire)', 'type': 'onewire'},
                   {'val': 11, 'text': '11 (OneWire1)', 'type': 'onewire'},
                   {'val': 0, 'text': ' 0', 'type': 'rotary'},
                   {'val': 1, 'text': ' 1', 'type': 'rotary'},
                   {'val': 2, 'text': ' 2', 'type': 'rotary'},
                   {'val': 3, 'text': ' 3', 'type': 'display'},
                   {'val': 4, ' text': '4', 'type': 'display'},
                   {'val': 5, ' text': '5', 'type': 'display'},
                   {'val': 6, ' text': '6', 'type': 'display'},
                   {'val': 7, ' text': '7', 'type': 'display'},
                   {'val': 8, ' text': '8', 'type': 'display'},
                   {'val': 9, ' text': '9', 'type': 'display'},
                   {'val': 18, 'text': 'A0', 'type': 'free'},
                   {'val': 19, 'text': 'A1', 'type': 'free'},
                   {'val': 20, 'text': 'A2', 'type': 'free'},
                   {'val': 21, 'text': 'A3', 'type': 'free'},
                   {'val': 22, 'text': 'A4', 'type': 'free'}]
    elif (boardType == "core" or boardType =="photon") \
        and (shieldType == "V1" or shieldType == "V2"):
        pinList = [{'val': 17, 'text': 'Output 0 (A7)', 'type': 'act'},
                   {'val': 16, 'text': 'Output 1 (A6)', 'type': 'act'},
                   {'val': 11, 'text': 'Output 2 (A1)', 'type': 'act'},
                   {'val': 10, 'text': 'Output 3 (A0)', 'type': 'act'},
                   {'val': 0, 'text': 'OneWire', 'type': 'onewire'}]
    elif (boardType == "esp8266"):  # Note - Excluding shield definition for now
        pinList = [{'val': 16, 'text': '  D0 (Heat)', 'type': 'act'},
                   {'val': 14, 'text': '  D5 (Cool)', 'type': 'act'},
                   {'val': 13, 'text': '  D7 (Door)', 'type': 'door'},
                   {'val': 12, 'text': 'D6 (OneWire)', 'type': 'onewire'},
                   {'val': 0, 'text': 'D3 (Buzzer)', 'type': 'beep'},]
    elif (boardType == "esp32"):  # Note - Excluding shield definition for now
        pinList = [{'val': 25, 'text': '  25 (Heat)', 'type': 'act'},
                   {'val': 26, 'text': '  26 (Cool)', 'type': 'act'},
                   {'val': 13, 'text': '  34 (Door)', 'type': 'door'},
                   {'val': 13, 'text': '13 (OneWire)', 'type': 'onewire'}, ]

    else:
        print('Unknown controller or board type')
        pinList = {}
    return pinList

def getPinListJson(boardType, shieldType):
    try:
        pinList = getPinList(boardType, shieldType)
        return json.dumps(pinList)
    except json.JSONDecodeError:
        print("Cannot process pin list JSON")
        return 0

def pinListTest():
    print(getPinListJson("leonardo", "revC"))
    print(getPinListJson("uno", "revC"))
    print(getPinListJson("uno", "I2C"))
    print(getPinListJson("leonardo", "revA"))
    print(getPinListJson("uno", "revA"))
    print(getPinListJson("leonardo", "diy"))
    print(getPinListJson("core", "V1"))
    print(getPinListJson("core", "V2"))
    print(getPinListJson("photon", "V1"))
    print(getPinListJson("photon", "V2"))
    print(getPinListJson("esp8266", ""))
    print(getPinListJson("esp32", ""))

if __name__ == "__main__":
    pinListTest()
