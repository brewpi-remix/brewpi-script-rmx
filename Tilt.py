#!/usr/bin/env python3

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

# Imports sorted by isort
#
# System Imports
import argparse
import asyncio
import datetime
from decimal import *
import json
import re
import subprocess
import sys
import threading
from configparser import ConfigParser
from csv import reader
from os.path import abspath, dirname, exists, getmtime, isfile
from struct import unpack
from time import sleep, time
# Third Party Imports
import numpy
import aioblescan
# Local Imports
#

# Tilt colors
TILT_COLORS = ['Red', 'Green', 'Black', 'Purple', 'Orange', 'Blue', 'Yellow', 'Pink']
# Known Tilt hardware versions
TILT_VERSIONS = ['Unknown', 'v1', 'v2', 'v3', 'Pro', 'v2 or 3']


class TiltManager(object):
    """
    Class defining the content of a Tilt advertisement. Manages the monitoring
    of all Tilts and storing the read values
    """

    TILT = 'a495'
    threads = []

    def __init__(self, averagingPeriod=0, medianWindow=0, dev_id=0):
        """
        Initializes TiltManager class with default values

        :param color: Tilt color to be managed
        :param averagingPeriod: Time period in seconds for noise smoothing
        :param medianWindow: Median filter setting in number of  entries
        :param dev_id: Device ID of the local Bluetooth device to use
        """

        self.tilt = None
        self.opts = None
        self.debug = False
        self.dev_id = dev_id
        self.averagingPeriod = averagingPeriod
        self.medianWindow = medianWindow

        # Set up an array of Tilt objects, one for each color
        self.tilt = [None] * len(TILT_COLORS)
        for i in range(len(TILT_COLORS)):
            self.tilt[i] = Tilt(
                TILT_COLORS[i], averagingPeriod, medianWindow)

        self.conn = None
        self.btctrl = None
        self.event_loop = None
        self.mysocket = None
        self.fac = None

    def setDebug(self, debug):
        self.debug = debug

    def setOpts(self, opts):
        self.opts = opts

    def loadSettings(self):
        """
        Load Settings from config file

        Overrides values given at creation. This needs to be called before
        the start function is called.

        :return: None
        """

        myDir = dirname(abspath(__file__))
        filename = '{0}/settings/tiltsettings.ini'.format(myDir)

        if exists(filename) and isfile(filename):
            try:
                config = ConfigParser()
                config.read(filename)

                # BT Device ID
                try:
                    self.dev_id = config.getint("Manager", "DeviceID")
                except:
                    pass

                # Time period for noise smoothing
                try:
                    self.averagingPeriod = config.getint(
                        "Manager", "AvgWindow")
                except:
                    pass

                # Median filter setting
                try:
                    self.medianWindow = config.getint("Manager", "MedWindow")
                except:
                    pass

            except Exception as e:
                print('WARNING: Config file cannot be read: ({0}): {1}'.format(
                    filename, e.message))

        else:
            print('INFO: Config file does not exist: {0}'.format(filename))

    def tiltName(self, uuid):
        """
        Return Tilt color given UUID

        :param uuid: UUID from BLEacon
        :return: Tilt color
        """

        return {
            'a495bb10c5b14b44b5121370f02d74de': 'Red',
            'a495bb20c5b14b44b5121370f02d74de': 'Green',
            'a495bb30c5b14b44b5121370f02d74de': 'Black',
            'a495bb40c5b14b44b5121370f02d74de': 'Purple',
            'a495bb50c5b14b44b5121370f02d74de': 'Orange',
            'a495bb60c5b14b44b5121370f02d74de': 'Blue',
            'a495bb70c5b14b44b5121370f02d74de': 'Yellow',
            'a495bb80c5b14b44b5121370f02d74de': 'Pink'
        }.get(uuid)

    def storeValue(self, timestamp, mac, hwVersion, fwVersion, color, temperature, gravity, battery):
        """
        Store Tilt values

        :param temperature: Temperature value to be stored
        :param gravity: Gravity value to be stored
        :param battery: Battery age value to be stored
        :return: None
        """

        if isinstance(self.tilt, list):
            for i in range(len(TILT_COLORS)):
                if color == TILT_COLORS[i]:
                    self.tilt[i].setValues(timestamp, mac, hwVersion, fwVersion, color, temperature, gravity, battery)
        else:
            self.tilt.setValues(timestamp, mac, hwVersion, fwVersion, color, temperature, gravity, battery)

    def getValue(self, color):
        """
        Retrieve Tilt value

        :param color: Color of Tilt to be checked
        :return: Tilt value
        """

        returnValue = None
        if isinstance(self.tilt, list):
            # If there's an array of Tilt objects, loop through till we have a match
            for i in range(len(TILT_COLORS)):
                if TILT_COLORS[i] == color:
                    returnValue = self.tilt[i].getValues(color)
        else:
            # If there's a single Tilt object, return it's value
            returnValue = self.tilt.getValues(color)
        return returnValue

    def decode(self, ev):
        """
        Decode BLEacon to Tilt data

        :param ev: Pointer to aioblescan.HCI_Event()
        :return: Tilt values in JSON
        """

        data = {}
        manufacturer_data = ev.retrieve("Manufacturer Specific Data")
        if manufacturer_data:
            payload = manufacturer_data[0].payload
            payload = payload[1].val.hex()
            if payload[4:8] == self.TILT:
                data['mfg_id'] = payload[0:8]
                data['color'] = self.tiltName(payload[4:36])
                data['mac'] = ev.retrieve("peer")[0].val
                data['uuid'] = payload[0:-1]
                data['major'] = int.from_bytes(bytes.fromhex(payload[36:40]), byteorder='big')
                data['minor'] = int.from_bytes(bytes.fromhex(payload[40:44]), byteorder='big')
                # On the latest tilts, TX power is used for battery age in
                # weeks since battery change (0-152 when converted to unsigned
                # 8 bit integer) and other TBD operation codes
                data['tx_power'] = int.from_bytes(bytes.fromhex(payload[44:46]), byteorder='big', signed=False)
                data['rssi'] = ev.retrieve("rssi")[-1].val
                data['ev_type'] = int(ev.retrieve('ev type')[-1].val)

                return json.dumps(data)

    def blecallback(self, data):
        """
        Callback method for aioblescan. In turn calls self.decode() and
        then self.storeValue().

        :param data: Data from aioblescan.BLEScanRequester
        :return: None
        """

        fwVersion = 0
        temperature = 68
        gravity = 1

        ev = aioblescan.HCI_Event()
        ev.decode(data)
        tiltJson = self.decode(ev)

        display_raw = True
        if tiltJson:
            if self.opts:
                if self.opts.mac: # Limit to MAC in argument
                    goon = False
                    mac = ev.retrieve("peer")
                    for x in mac:
                        if x.val in self.opts.mac:
                            goon =True
                            break
                    if not goon:
                        return

                if self.opts.raw and self.debug: # Print Debug
                    display_raw = False
                    print("Raw data: {}".format(ev.raw_data))

                if self.opts.json and self.debug: # Print Debug
                    display_raw = False
                    print("Tilt JSON: {}".format(tiltJson))
      
        else: # Not a Tilt
            return

        if display_raw and self.debug: # Print Debug
            ev.show(0)

        # Prepare to store Tilt data
        tiltData = {}
        tiltdata = json.loads(tiltJson)

        mac = str(tiltdata['mac'])
        color = str(tiltdata['color'])

        if int(tiltdata['major']) == 999:
            # For the latest Tilts, this is now actually a special code indicating that
            # the gravity is the version info.
            fwVersion = int(tiltdata['minor'])
        else:
            if int(tiltdata['minor']) >= 5000:
                # Is a Tilt Pro
                # self.tilt_pro = True
                gravity = Decimal(tiltdata['minor']) / 10000
                temperature = Decimal(tiltdata['major']) / 10
            else:
                # Is not a Pro model
                gravity = Decimal(tiltdata['minor']) / 1000
                temperature = int(tiltdata['major'])

        battery = int(tiltdata['tx_power'])

        # Try to derive if we are v1, 2, or 3
        if int(tiltdata['ev_type']) == 0: # Only Tilt v1 shows as "generic adv"
            hwVersion = 1
        elif int(tiltdata['minor']) >= 5000:
            hwVersion = 4
        else: # TODO: 5 is "v2 or 3" until we can tell the difference between the two of them
            hwVersion = 5

        rssi = tiltdata['rssi']

        timestamp = datetime.datetime.now()

        # Store value
        timestamp = datetime.datetime.now()
        self.storeValue(timestamp, mac, hwVersion, fwVersion, color, temperature, gravity, battery)

    def start(self, debug = False):
        """
        Starts the BLE scanning thread

        :return: None
        """

        # Turn debug printing on or off
        self.setDebug(debug)

        self.event_loop = asyncio.get_event_loop()
        # First create and configure a raw socket
        self.mysocket = aioblescan.create_bt_socket(self.dev_id)

        # Create a connection with the STREAM socket
        self.fac = self.event_loop._create_connection_transport(
            self.mysocket, aioblescan.BLEScanRequester, None, None)
        # Start it
        self.conn, self.btctrl = self.event_loop.run_until_complete(self.fac)
        # Attach your processing
        self.btctrl.process = self.blecallback
        # Probe
        self.btctrl.send_scan_request()

        thread = threading.Thread(target=self.event_loop.run_forever)
        self.threads.append(thread)
        thread.start()

        return

    def stop(self):
        """
        Stop the BLE scanning thread

        :return: None
        """
        self.btctrl.stop_scan_request()
        command = aioblescan.HCI_Cmd_LE_Advertise(enable=False)
        self.btctrl.send_command(command)

        asyncio.gather(*asyncio.Task.all_tasks()).cancel()
        for thread in self.threads:
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
            thread.join()

        self.conn.close()
        self.event_loop.close()
        return


class TiltValue:
    """
    Holds all category values of an individual Tilt reading
    """

    def __init__(self, timestamp = 0, mac = "", hwVersion = 0, fwVersion = 0, color = None, temperature = 0, gravity = 0, battery = 0):
        self.timestamp = timestamp
        self.mac = mac
        self.hwVersion = hwVersion
        self.fwVersion = fwVersion
        self.color = color
        self.temperature = temperature
        self.gravity = gravity
        self.battery = battery

    def __str__(self):
        return "S: " + str(self.timestamp) + " M: " + str(self.mac) + "F: " + str(self.fwVersion) + "C: " + str(self.color) + "T: " + str(self.temperature) + " G: " + str(self.gravity) + " B: " + str(self.battery)


class Tilt:
    """
    Manages Tilt values

    Handles calibration, storing of values and smoothing of read values.
    """

    values = None
    lastMAC = ''
    lastBatt = 0
    lastHwVersion = 0
    lastFwVersion = 0
    averagingPeriod = 0
    medianWindow = 0
    calibrationDataTime = {}
    tempCal = None
    gravCal = None
    tempFunction = None
    gravityFunction = None

    def __init__(self, color, averagingPeriod=0, medianWindow=0):
        self.color = color
        self.averagingPeriod = averagingPeriod
        self.medianWindow = medianWindow
        self.values = []
        self.calibrate(color)
        self.calibrationDataTime = {
            'temperature': 0,
            'temperature_checked': 0,
            'gravity': 0,
            'gravity_checked': 0
        }

    def calibrate(self, color):
        """
        Load/reload calibration functions
        """

        # Check for temperature function. If none, then not changed since
        # last load.
        self.tempFunction = self.tiltCal("temperature", color)
        if self.tempFunction is not None:
            self.tempCal = self.tempFunction

        # Check for gravity function. If none, then not changed since last
        # load.
        self.gravityFunction = self.tiltCal("gravity", color)
        if self.gravityFunction is not None:
            self.gravCal = self.gravityFunction

    def setValues(self, timestamp, mac, hwVersion, fwVersion, color, temperature, gravity, battery):
        """
        Set/add the latest temperature & gravity readings to the store.

        These values will be calibrated before storing if calibration is
        enabled
        """

        self.cleanValues()
        self.calibrate(color)
        calTemp = self.tempCal(temperature)
        calGrav = self.gravCal(gravity)
        # tx_power will be -59 every 5 seconds in order to allow iOS
        # to compute RSSI correctly.  Only use 0 or real value.
        if battery < 0:
            battery = 0

        self.values.append(TiltValue(timestamp, mac, hwVersion, fwVersion, color, temperature, gravity, battery))

    def getValues(self, color):
        """
        Returns the values for a given Tilt

        This will be the latest read value unless averaging / median has
        been enabled
        """

        colorValues = []
        returnValue = None

        if len(self.values) > 0:
            for i in range(len(self.values)):
                if self.values[i].color == color:

                    timestamp = self.values[i].timestamp
                    mac = self.values[i].mac
                    hwVersion = self.values[i].hwVersion
                    fwVersion = self.values[i].fwVersion
                    temperature = self.values[i].temperature
                    gravity = self.values[i].gravity
                    battery = self.values[i].battery

                    colorValues.append(TiltValue(timestamp, mac, hwVersion, fwVersion, color, temperature, gravity, battery))

            if len(colorValues) > 0:
                if self.medianWindow == 0:
                    returnValue = self.averageValues(color, colorValues)
                else:
                    returnValue = self.medianValues(color, colorValues)

            self.cleanValues()

        return returnValue

    def averageValues(self, color, values):
        """
        Average all the stored values in the Tilt class (except battery)

        :param color:   Color of Tilt to check
        :param values:  Array containing values to check
        :return:        Averaged values
        """

        returnValue = None

        if len(values) > 0:
            returnValue = TiltValue()
            for value in values:
                returnValue.temperature += value.temperature
                returnValue.gravity += value.gravity

            # Get last timestamp from values (or 0)
            returnValue.timestamp = self.getTimestamp(color)

            # Get MAC out of array of values
            returnValue.mac = self.getMAC(color)

            # Get Hardware version out of array of values
            returnValue.hwVersion = self.getHwVersion(color)

            # Get Firmware version out of array of values
            returnValue.fwVersion = self.getFWVersion(color)

            # Average temp and gravity values
            returnValue.temperature /= len(values)
            returnValue.gravity /= len(values)

            # Make sure battery returns max of current values (or 0)
            returnValue.battery = self.getBatteryValue(color)

        return returnValue

    def medianValues(self, color, values, window=3):
        """
        Use a median method across the stored values to reduce noise

        :param color:   Color of Tilt to be checked
        :param values:  Array containing values to check
        :param window:  Smoothing window to apply across the data. If the
                        window is less than the dataset size, the window
                        will be moved across the dataset taking a median
                        value for each window, with the resultant set
                        averaged
        :return: Median value
        """

        # Ensure there are enough values to do a median filter, if not shrink
        # window temporarily
        if len(values) < window:
            window = len(values)

        returnValue = TiltValue()

        # sidebars = (window - 1) / 2
        medianValueCount = 0

        for i in range(len(values) - (window - 1)):
            # Work out range of values to do median. At start and end of
            # assessment, need to pad with start and end values.
            medianValues = values[i:i + window]

            medianValuesTemp = []
            medianValuesGravity = []

            # Separate out Temp and Gravity values
            for medianValue in medianValues:
                medianValuesTemp.append(medianValue.temperature)
                medianValuesGravity.append(medianValue.gravity)

            # Add the median value to the running total.
            returnValue.temperature += numpy.median(
                numpy.array(medianValuesTemp))
            returnValue.gravity += numpy.median(
                numpy.array(medianValuesGravity))

            # Increase count
            medianValueCount += 1

        # Get last timestamp from values (or 0)
        returnValue.timestamp = self.getTimestamp(color)

        # Get MAC out of array of values
        returnValue.mac = self.getMAC(color)

        # Get Hardware version out of array of values
        returnValue.hwVersion = self.getHwVersion(color)

        # Get Firmware version out of array of values
        returnValue.fwVersion = self.getFWVersion(color)

        # Average values
        returnValue.temperature /= medianValueCount
        returnValue.gravity /= medianValueCount

        # Make sure battery returns max of current values (or 0)
        returnValue.battery = self.getBatteryValue(color)

        return returnValue

    def getTimestamp(self, color):
        """
        Return timestamp of last report for a given color

        :param values:  Array of values to be checked
        :return: Timestamp of last report, or 0
        """

        timestamps = []
        for i in range(len(self.values)):
            value = self.values[i]
            timestamps.append(value.timestamp)

        return max(timestamps)

    def getBatteryValue(self, color):
        """
        Return battery age in weeks for a given color

        :param values:  An array of Tilt values
        :return: Integer of battery age in weeks, or 0
        """

        batteryValues = []
        for i in range(len(self.values)):
            value = self.values[i]
            if not value.battery == 197: # Skip -59 (197 unsigned)
                batteryValues.append(value.battery)

        # Since tx_power will be -59 every 5 seconds in order to allow iOS
        # to compute RSSI correctly, we cache the last good value and only
        # use the max of all on-hand values as the battery age to prevent
        # zeroes.  A zero value should only come from V1 (and maybe v2) Tilts.
        batteryValue = 0
        if len(batteryValues):
            batteryValue = max(batteryValues)
        self.lastBatt = max(batteryValue, self.lastBatt)
        return self.lastBatt

    def getHwVersion(self, color):
        """
        Return Hardware Version for a given color

        :param values:  An array of Tilt values
        :return: Int of TILT_VERSIONS or empty string
        """

        hwVersions = []
        for i in range(len(self.values)):
            value = self.values[i]
            hwVersions.append(value.hwVersion)

        hwVersion = max(hwVersions)
        self.lastHwVersion = max(hwVersion, self.lastHwVersion)
        return self.lastHwVersion

    def getFWVersion(self, color):
        """
        Return firmware version for a given color

        :param values:  An array of Tilt values
        :return: Integer of version or 0
        """

        fwVersions = []
        for i in range(len(self.values)):
            value = self.values[i]
            fwVersions.append(value.fwVersion)

        fwVersion = max(fwVersions)
        self.lastFwVersion = max(fwVersion, self.lastFwVersion)
        return self.lastFwVersion

    def getMAC(self, color):
        """
        Return MAC for a given color

        :param values:  An array of Tilt values
        :return: String of version or empty string
        """

        macs = []
        for i in range(len(self.values)):
            value = self.values[i]
            macs.append(value.mac)

        mac = max(macs)
        self.lastMAC = max(mac, self.lastMAC)
        return self.lastMAC

    def cleanValues(self):
        """
        Clean out stale values that are beyond the desired window

        :return: None, operates on values in class
        """

        nowTime = datetime.datetime.now()

        for value in self.values:
            if (nowTime - value.timestamp).seconds >= self.averagingPeriod:
                self.values.pop(0)
            else:
                # The list is sorted in chronological order, so once we've hit
                # this condition we can stop searching.
                break

    def tiltCal(self, which, color):
        """
        Loads settings from file and create the calibration functions

        :param which: Which value (gravity or temperature) is to be processed
        :return: The calibration function to be called
        """

        # Default time in seconds to wait before checking config files to see if
        # calibration data has changed.
        DATA_REFRESH_WINDOW = 60

        originalValues = []
        actualValues = []
        csvFile = None
        path = dirname(abspath(__file__))
        configDir = '{0}/settings/'.format(path)
        filename = '{0}{1}.{2}'.format(
            configDir, which.upper(), color.lower())

        lastChecked = self.calibrationDataTime.get(which + "_checked", 0)
        if (int(time()) - lastChecked) < DATA_REFRESH_WINDOW:
            # Only check every DATA_REFRESH_WINDOW seconds
            return None

        lastLoaded = self.calibrationDataTime.get(which, 0)
        self.calibrationDataTime[which + "_checked"] = int(time())

        try:
            if isfile(filename):
                fileModificationTime = getmtime(filename)
                if lastLoaded >= fileModificationTime:
                    # No need to load, no change
                    return None
                csvFile = open(filename, "rb")
                csvFileReader = reader(csvFile, skipinitialspace=True)
                self.calibrationDataTime[which] = fileModificationTime

                for row in csvFileReader:
                    # Skip any blank or comment rows
                    if row != [] and row[0][:1] != "#":
                        originalValues.append(Decimal(row[0]))
                        actualValues.append(Decimal(row[1]))
                # Close file
                csvFile.close()
        except IOError:
            print('Tilt ({0}): {1}: No calibration data ({2})'.format(
                color, which.capitalize(), filename))
        except Exception as e:
            print('ERROR: Tilt ({0}): Unable to initialise {1} calibration data ({2}) - {3}'.format(
                color, which.capitalize(), filename, e))
            # Attempt to close the file
            if csvFile is not None:
                # Close file
                csvFile.close()

        # If more than one values, use Polyfill
        if len(actualValues) >= 1:
            poly = numpy.poly1d(numpy.polyfit(
                originalValues, actualValues, deg=min(3, len(x)-1)))

            def returnFunction(x): return poly(x, color)
            print('Tilt ({0}): Initialized {1} Calibration: Polyfill'.format(
                color, which.capitalize()))

        else:
            def returnFunction(x): return x

        return returnFunction


def check_mac(mac):
    """
    Checks mac from command line arguments

    :param val: String representation of a valid mac address, e.g.:
        e8:ae:6b:42:cc:20
    """

    try:
        if re.match("[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$", mac.lower()):
            return mac.lower()
    except:
        pass
    raise argparse.ArgumentTypeError("{}} is not a MAC address".format(mac))

def parseArgs():
    """
    Parse any command line arguments

    :param: None
    :return: None
    """

    parser = argparse.ArgumentParser(
        description="Track Tilt BLEacon packets")
    parser.add_argument(
        "-r",
        "--raw",
        action='store_true',
        default=False,
        help="dump raw HCI packet data for Tilts")
    parser.add_argument(
        "-j",
        "--json",
        action='store_true',
        default=False,
        help="display Tilt data in JSON format")
    parser.add_argument(
        "-v",
        "--verbose",
        action='store_true',
        default=False,
        help="display debug data")
    parser.add_argument(
        "-m",
        "--mac",
        type=check_mac,
        action='append',
        help="filter Tilts by this/these MAC address(es)")
    parser.add_argument(
        "-d",
        "--dev",
        type=int,
        default=0,
        help="select the hci device to use (default 0, i.e. hci0)")
    parser.add_argument(
        "-c",
        "--col",
        type=str,
        default=None,
        help="filter by this Tilt color")
    parser.add_argument(
        "-a",
        "--avg",
        type=int,
        default=None,
        help="seconds window for averaging")
    parser.add_argument(
        "-n",
        "--med",
        type=int,
        default=None,
        help="number of entries in median window")
    try:
        opts = parser.parse_args()
        opts.col = opts.col.title() if opts.col else None
        if opts.col and opts.col not in TILT_COLORS:
            parser.error("Invalid color choice.")
        opts.dev = opts.dev if opts.dev else 0
        return opts
    except Exception as e:
        parser.error("Error: " + str(e))
        sys.exit()

def checkSetcap() -> (bool, str, str):
    """
    Checks setcap environment

    :return bool: Status of setcap environment
    :return str: Base executable
    :return str: getcap values
    """

    try:
        base_executable = subprocess.check_output(
            ["readlink", "-e", sys.executable]).strip().decode("utf-8")
    except FileNotFoundError:
        # readlink doesn't exist
        return False, "", ""
    except subprocess.CalledProcessError:
        # readlink failed
        return False, "", ""

    try:
        getcap_values = subprocess.check_output(
            ["getcap", base_executable]).strip().decode("utf-8")
        getcap_values = getcap_values.split(' = ')[1]
    except IndexError:
        # No capabilities exist
        return False, base_executable, ""
    except FileNotFoundError:
        # getcap doesn't exist on this system (e.g. MacOS)
        return False, base_executable, ""
    except subprocess.CalledProcessError:
        # setcap -v failed
        return False, base_executable, ""

    # We have to check for three things:
    #   1. That the executable has cap_net_admin
    #   2. That the executable has cap_net_raw
    #   3. That the executable has +eip (inheritable permissions)
    #
    # The output of getcap should look like this:
    #       b'/usr/bin/python3.6 = cap_net_admin,cap_net_raw+eip\n'
    #
    # I think we only need cap_net_raw+eip
    #
    # sudo setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/python3.7

    cap_net_admin_missing = True
    cap_net_raw_missing = True
    cap_eip_unset = True

    # if getcap_values.find("cap_net_admin") != -1:
    #     cap_net_admin_missing = False
    if getcap_values.find("cap_net_raw") != -1:
        cap_net_raw_missing = False
    if getcap_values.find("+eip") != -1:
        cap_eip_unset = False

    if cap_net_raw_missing or cap_eip_unset:
        return False, base_executable, getcap_values
    return True, base_executable, getcap_values

def main():
    """
    Test function executed when this file is run as a discrete script

    :return: None
    """

    print("\nTilt BLEacon test.")
    opts = parseArgs()
    tiltColorName = None
    averaging = 0
    median = 0
    device_id = 0

    # Check that Python has the correct capabilities set
    hasCaps, pythonPath, getCapValues = checkSetcap()
    if not hasCaps:
        commandLine = "sudo setcap cap_net_raw+eip $(eval readlink -f `which python3`)"
        print("\nERROR: Missing cap flags on python executable.\nExecutable:\t{}\nCap Values:\t{}\nSuggested command:\t{}".format(pythonPath, getCapValues, commandLine))
        return

    # Select color
    if opts.col:
        tiltColor = opts.col.title()
        tiltColorName = opts.col.title()
    else:
        tiltColor = None
        tiltColorName = "all"

    # Set options
    if opts.med:
        median = opts.med
    if opts.avg:
        average = opts.avg
    if opts.dev:
        device_id = opts.dev

    tilt = TiltManager(averaging, median, device_id)
    tilt.setOpts(opts)
    tilt.loadSettings()
    tilt.start(opts.verbose)

    try:
        print("\nReporting {} Tilt values every 5 seconds. Ctrl-C to stop.".format(tiltColorName))
        while 1:
            # If we are running Tilt, get current values
            if tilt:
                sleep(5)

                # Check each of the Tilt colors
                for color in TILT_COLORS:
                    if color == tiltColor or tiltColor == None:
                        tiltValue = tilt.getValue(color)
                        if tiltValue is not None:
                            timestamp = tiltValue.timestamp
                            hwVersion = tiltValue.hwVersion
                            fwVersion = tiltValue.fwVersion
                            if (hwVersion == 4): # If we are using a Pro, take advantage of it
                                temperature = round(tiltValue.temperature, 1)
                                gravity = round(tiltValue.gravity, 4)
                            else:
                                temperature = round(tiltValue.temperature)
                                gravity = round(tiltValue.gravity, 3)
                            battery = tiltValue.battery
                            mac = tiltValue.mac
                            print("{}:\tLast Report: {}\n\tMAC: {}, Version: {}, Firmware: {}\n\tTemp: {}°F, Gravity: {}, Battery: {} weeks old".format(color, timestamp, mac.upper(), TILT_VERSIONS[hwVersion], fwVersion, temperature, gravity, battery))
                        else:
                            print("{}:\tNo results returned.".format(color))

    except KeyboardInterrupt:
        print('\nKeyboard interrupt.')
    finally:
        print('Closing event loop.')
        if tilt:
            tilt.stop()
    return

if __name__ == "__main__":
    main()
    exit(0)
