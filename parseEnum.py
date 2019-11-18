#!/usr/bin/python

# Copyright (C) 2018  Lee C. Bussy (@LBussy)

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

import re

def parseEnumInFile(hFilePath, enumName):
    messageDict = {}
    hFile = open(hFilePath)
    regex = re.compile("[A-Z]+\(([A-Za-z][A-Z0-9a-z_]*),\s*\"([^\"]*)\"((?:\s*,\s*[A-Za-z][A-Z0-9a-z_\.]*\s*)*)\)\s*,?")
    for line in hFile:
        if 'enum ' + enumName in line:
            break  # skip lines until enum open is encountered

    count = 0
    for line in hFile:
        if 'MSG(' in line:
            # print line
            # print regex
            # r = regex.search(str(line))
            groups = regex.findall(line)
            logKey = groups[0][0]
            logString = groups[0][1]
            paramNames = groups[0][2].replace(",", " ").split()
            messageDict[count] = {'logKey': logKey, 'logString': logString,'paramNames': paramNames}
            count += 1

        if 'END enum ' + enumName in line:
            break

    hFile.close()
    return messageDict
