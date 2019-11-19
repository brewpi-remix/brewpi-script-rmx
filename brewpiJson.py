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

from datetime import datetime
import time
import os
import re
import Tilt


def fixJson(j):
    j = re.sub(r"'{\s*?(|\w)", r'{"\1', j)
    j = re.sub(r"',\s*?(|\w)", r',"\1', j)
    j = re.sub(r"'(|\w)?\s*:", r'\1":', j)
    j = re.sub(r"':\s*(|\w*)\s*(|[,}])", r':"\1"\2', j)
    return j


def addRow(jsonFileName, row, tiltColor = None, iSpindel = None):
    jsonFile = open(jsonFileName, "r+")
    # jsonFile.seek(-3, 2)  # Go insert point to add the last row
    jsonFile.seek(0, os.SEEK_END)
    jsonFile.seek(jsonFile.tell() - 3, os.SEEK_SET)
    ch = jsonFile.read(1)
    jsonFile.seek(0, os.SEEK_CUR)
    # When alternating between reads and writes, the file contents should be flushed, see
    # http://bugs.python.org/issue3207. This prevents IOError, Errno 0
    if ch != '[':
        # not the first item
        jsonFile.write(',')
    newRow = {}
    newRow['Time'] = datetime.today()

    # Insert a new JSON row
    # {"c":[{"v":"Date(2012,8,26,0,1,0)"},{"v":18.96},{"v":19.0},null,{"v":19.94},{"v":19.6},null]},
    jsonFile.write(os.linesep)
    jsonFile.write("{\"c\":[")
    now = datetime.now()
    jsonFile.write("{{\"v\":\"Date({y},{M},{d},{h},{m},{s})\"}},".format(
        y=now.year, M=(now.month - 1), d=now.day, h=now.hour, m=now.minute, s=now.second))
    if row['BeerTemp'] is None:
        jsonFile.write("null,")
    else:
        jsonFile.write("{\"v\":" + str(row['BeerTemp']) + "},")

    if row['BeerSet'] is None:
        jsonFile.write("null,")
    else:
        jsonFile.write("{\"v\":" + str(row['BeerSet']) + "},")

    if row['BeerAnn'] is None:
        jsonFile.write("null,")
    else:
        jsonFile.write("{\"v\":\"" + str(row['BeerAnn']) + "\"},")

    if row['FridgeTemp'] is None:
        jsonFile.write("null,")
    else:
        jsonFile.write("{\"v\":" + str(row['FridgeTemp']) + "},")

    if row['FridgeSet'] is None:
        jsonFile.write("null,")
    else:
        jsonFile.write("{\"v\":" + str(row['FridgeSet']) + "},")

    if row['FridgeAnn'] is None:
        jsonFile.write("null,")
    else:
        jsonFile.write("{\"v\":\"" + str(row['FridgeAnn']) + "\"},")

    if row['RoomTemp'] is None:
        jsonFile.write("null,")
    else:
        jsonFile.write("{\"v\":" + str(row['RoomTemp']) + "},")

    if row['State'] is None:
        jsonFile.write("null")
    else:
        jsonFile.write("{\"v\":" + str(row['State']) + "}")

    # Write Tilt values
    if tiltColor:
        for color in Tilt.TILT_COLORS:
            # Only log the Tilt if the color matches the config
            if color == tiltColor:
                jsonFile.write(",")

                # Log Tilt SG
                if row.get(color + 'SG', None) is None:
                    jsonFile.write("null")
                else:
                    jsonFile.write("{\"v\":" + str(row[color + 'SG']) + "}")

    # Write iSpindel values
    elif iSpindel:
        jsonFile.write(",")

        if row['spinTemp'] is None:
            jsonFile.write("null,")
        else:
            jsonFile.write("{\"v\":" + str(row['spinTemp']) + "},")

    # rewrite end of json file
    jsonFile.write("]}]}")
    jsonFile.close()


def newEmptyFile(jsonFileName, tiltColor = None, iSpindel = None):
    # Munge together standard column headers
    standardCols = ('"cols":[' +
                '{"type":"datetime","id":"Time","label":"Time"},' +
                '{"type":"number","id":"BeerTemp","label":"Beer Temp."},' +
                '{"type":"number","id":"BeerSet","label":"Beer Setting"},' +
                '{"type":"string","id":"BeerAnn","label":"Beer Annot."},' +
                '{"type":"number","id":"FridgeTemp","label":"Chamber Temp."},' +
                '{"type":"number","id":"FridgeSet","label":"Chamber Setting"},' +
                '{"type":"string","id":"FridgeAnn","label":"Chamber Annot."},' +
                '{"type":"number","id":"RoomTemp","label":"Room Temp."},' +
                '{"type":"number","id":"State","label":"State"}')

    # Now get Tilt data if we are using it
    if tiltColor:
        tiltCols = (',{"type":"number","id":"' + tiltColor + 'SG","label":"' + tiltColor + ' Tilt Gravity"}')
        jsonCols = ('{' + standardCols + tiltCols + '],"rows":[]}')

    # Or get iSpindel data if we are using that
    elif iSpindel:
        iSpindelCols = (',{"type":"number","id":"spinSG","label":"iSpindel SG"}')
        jsonCols = ('{' + standardCols + iSpindelCols + '],"rows":[]}')

    # No Tilt or iSpindel
    else:
        jsonCols = ('{' + standardCols + '],"rows":[]}')

    jsonFile = open(jsonFileName, 'w')
    jsonFile.write(jsonCols)
    jsonFile.close()
