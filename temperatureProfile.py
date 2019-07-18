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

from __future__ import print_function
import time
import csv
import sys
import BrewPiUtil as util

def getNewTemp(scriptPath):
    with open(util.addSlash(scriptPath) + 'settings/tempProfile.csv', 'rU') as csvfile:
        dialect = csv.Sniffer().sniff(csvfile.readline())
        csvfile.seek(0)
        temperatureReader = csv.reader(csvfile, dialect)
        # temperatureReader = csv.reader(     open(util.addSlash(scriptPath) + 'settings/tempProfile.csv', 'rb'),
        #                                 delimiter=',', quoting=csv.QUOTE_ALL)
        next(temperatureReader)  # discard the first row, which is the table header
        prevTemp = None
        nextTemp = None
        interpolatedTemp = -99
        prevDate = None
        nextDate = None

        now = time.mktime(time.localtime())  # get current time in seconds since epoch

        for row in temperatureReader:
            dateString = row[0]
            try:
                date = time.mktime(time.strptime(dateString, "%Y-%m-%dT%H:%M:%S"))
            except ValueError:
                continue  # skip dates that cannot be parsed

            try:
                temperature = float(row[1])
            except ValueError:
                if row[1].strip() == '':
                    # cell is left empty, this is allowed to disable temperature control in part of the profile
                    temperature = None
                else:
                    # invalid number string, skip this row
                    continue

            prevTemp = nextTemp
            nextTemp = temperature
            prevDate = nextDate
            nextDate = date
            timeDiff = now - nextDate
            if timeDiff < 0:
                if prevDate is None:
                    interpolatedTemp = nextTemp  # first set point is in the future
                    break
                else:
                    if prevTemp is None or nextTemp is None:
                        # When the previous or next temperature is an empty cell, disable temperature control.
                        # This is useful to stop temperature control after a while or to not start right away.
                        interpolatedTemp = None
                    else:
                        interpolatedTemp = ((now - prevDate) / (nextDate - prevDate) * (nextTemp - prevTemp) + prevTemp)
                        interpolatedTemp = round(interpolatedTemp, 2)
                    break

        if interpolatedTemp == -99:  # all set points in the past
            interpolatedTemp = nextTemp

        return interpolatedTemp
