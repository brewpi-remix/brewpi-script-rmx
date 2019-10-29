#!/usr/bin/python

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

# SG Polling script
# Greg Masem - ispindel@mas321.com
# 
# This processes the data coming from the iSpindel and averages/cleans it.
# It will store data as CSV.
#
# It will output the data to a location for BrewPi script to pull in when
# data points are saved.   

import sys
import datetime
import time
import os

import threading
import thread

import numpy
from numpy import genfromtxt
import csv
import functools
import ConfigParser


def getValue():
        """Returns the latest temperature, battery level & gravity values of the Hydrometer""" 

        ispindelreading = genfromtxt("/var/www/html/data/iSpindel/SpinData.csv", delimiter = ',')
        return ispindelreading
