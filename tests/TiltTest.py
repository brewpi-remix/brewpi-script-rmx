#!/usr/bin/python

# Copyright (C) 2019 Lee C. Bussy (@LBussy)

# This file is part of LBussy's BrewPi Tilt Remix (BrewPi-Tilt-RMX).
#
# BrewPi Tilt RMX is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# BrewPi Tilt RMX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BrewPi Tilt RMX. If not, see <https://www.gnu.org/licenses/>.

# These scripts were originally a part of brewpi-brewometer, which provided
# support in BrewPi for the Tilt Electronic Hydrometer (formerly Brewometer.)

# Credit for the original brewpi-brewometer goes to @sibowler. @supercow
# then forked that work and released a more "Legacy"-capable version for
# the BrewPi Legacy users. This was an obvious jumping-off point for
# brewpi-tilt-rmx.

# Neither @sibowler's scripts nor @supercow's fork had a license attached
# to the repository. As a derivative work of BrewPi, a project released
# under the GNU General Public License v3.0, this license is attached here
# giving precedence for prior work by the BrewPi team.

# Simple utility to test if the Tilt has been connected properly to
# the Raspberry Pi.

import sys
import os
# Append parent directory to be able to import files
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..")
import time
import threading
import Tilt

threads = []
tilt = Tilt.TiltManager(False, 60, 40)
tilt.loadSettings()
tilt.start()


def toString(value):
    returnValue = value
    if value is None:
        returnValue = ''
    return str(returnValue)


print "Scanning - 20 Secs (Control+C to exit early)"
for _ in range(4):
    time.sleep(5)
    for color in Tilt.TILT_COLORS:
        print color + ": " + str(tilt.getValue(color))


tilt.stop()

for thread in threads:
    thread.join()

exit(0)
