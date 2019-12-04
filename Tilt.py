#!/usr/bin/python3

# Copyright (C) 2019 Lee C. Bussy (@LBussy)

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
# along with BrewPi Tilt RMX. If not, see <https://www.gnu.org/licenses/>.

from sys import exit
import asyncio
import aioblescan as aios
import datetime
from time import time, sleep
from os.path import dirname, abspath, isfile, getmtime, exists
import threading
import numpy
from csv import reader
from configparser import ConfigParser
from struct import unpack
import json


TILT_COLORS = ['Red', 'Green', 'Black', 'Purple', 'Orange', 'Blue', 'Yellow', 'Pink']


class TiltValue:
    """
    Holds all category values of an individual Tilt reading
    """

    color = None
    temperature = 0
    gravity = 0
    timestamp = 0
    battery = 0

    def __init__(self, color, temperature, gravity, battery):
        self.color = color
        self.temperature = temperature
        self.gravity = gravity
        self.timestamp = datetime.datetime.now()
        self.battery = battery

    def __str__(self):
        return "C: " + str(self.color) + "T: " + str(self.temperature) + " G: " + str(self.gravity) + " B: " + str(self.battery)


class Tilt:
    """
    Manages Tilt values

    Handles calibration, storing of values and smoothing of read values.
    """

    color = None
    values = None
    lock = None
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
        self.calibrate()
        self.calibrationDataTime = {
            'temperature': 0,
            'temperature_checked': 0,
            'gravity': 0,
            'gravity_checked': 0
        }

    def calibrate(self):
        """
        Load/reload calibration functions
        """

        # Check for temperature function. If none, then not changed since
        # last load.
        self.tempFunction = self.tiltCal("temperature")
        if self.tempFunction is not None:
            self.tempCal = self.tempFunction

        # Check for gravity function. If none, then not changed since last
        # load.
        self.gravityFunction = self.tiltCal("gravity")
        if self.gravityFunction is not None:
            self.gravCal = self.gravityFunction

    def setValues(self, color, temperature, gravity, battery):
        """
        Set/add the latest temperature & gravity readings to the store.

        These values will be calibrated before storing if calibration is
        enabled
        """
        #print("DEBUG:  Tilt name: {}, temp = {}, grav = {}, batt = {}.".format(color, temperature, gravity, battery))
        self.cleanValues()
        self.calibrate()
        calTemp = self.tempCal(temperature)
        calGrav = self.gravCal(gravity)
        # tx_power will be -59 every 5 seconds in order to allow iOS
        # to compute RSSI correctly.  Only use 0 or real value.
        if battery < 0:
            battery = 0
        self.values.append(TiltValue(color, calTemp, calGrav, battery))

    def getValues(self):
        """
        Returns the temperature, gravity & battery values of the Tilt

        This will be the latest read value unless averaging / median has
        been enabled
        """
        returnValue = None
        if len(self.values) > 0:
            if self.medianWindow == 0:
                returnValue = self.averageValues()
            else:
                returnValue = self.medianValues(self.medianWindow)

            self.cleanValues()
        return returnValue

    def averageValues(self):
        """
        Average all the stored values in the Tilt class (except battery)

        :return:  Averaged values
        """

        returnValue = None
        if len(self.values) > 0:
            returnValue = TiltValue('', 0, 0, 0)
            for value in self.values:
                returnValue.temperature += value.temperature
                returnValue.gravity += value.gravity

            # Average values
            returnValue.temperature /= len(self.values)
            returnValue.gravity /= len(self.values)

            # Round values
            returnValue.temperature = returnValue.temperature
            returnValue.gravity = returnValue.gravity

            # Make sure battery returns only real values (> 0)
            returnValue.battery = self.getBatteryValue()

        return returnValue

    def getBatteryValue(self):
        batteryValues = []
        for i in range(len(self.values)):
            values = self.values[i]
            batteryValues.append(values.battery)

        #from pprint import pprint as pp
        #print('DEBUG:  Battery Values:')
        #pp(batteryValues)
        return max(batteryValues)

    def medianValues(self, window=3):
        """
        Use a median method across the stored values to reduce noise

        :param window:  Smoothing window to apply across the data. If the
                        window is less than the dataset size, the window
                        will be moved across the dataset taking a median
                        value for each window, with the resultant set
                        averaged
        :return: Median value
        """

        # Ensure there are enough values to do a median filter, if not shrink
        # window temporarily
        if len(self.values) < window:
            window = len(self.values)

        returnValue = TiltValue('', 0, 0, 0)

        # sidebars = (window - 1) / 2
        medianValueCount = 0

        for i in range(len(self.values) - (window - 1)):
            # Work out range of values to do median. At start and end of
            # assessment, need to pad with start and end values.
            medianValues = self.values[i:i + window]

            medianValuesTemp = []
            medianValuesGravity = []

            # Separate out Temp and Gravity values
            for medianValue in medianValues:
                medianValuesTemp.append(medianValue.temperature)
                medianValuesGravity.append(medianValue.gravity)

            # Add the median value to the running total.
            returnValue.temperature += numpy.median(numpy.array(medianValuesTemp))
            returnValue.gravity += numpy.median(numpy.array(medianValuesGravity))

            # Increase count
            medianValueCount += 1

        # Average values
        returnValue.temperature /= medianValueCount
        returnValue.gravity /= medianValueCount

        # Round values
        returnValue.temperature = returnValue.temperature
        returnValue.gravity = returnValue.gravity

        # Now just get the max of battery to filter out 0's
        returnValue.battery = self.getBatteryValue()

        return returnValue

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

    def tiltCal(self, which):
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
        filename = '{0}{1}.{2}'.format(configDir, which.upper(), self.color.lower())

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
                        originalValues.append(float(row[0]))
                        actualValues.append(float(row[1]))
                # Close file
                csvFile.close()
        except IOError:
            print('Tilt ({0}): {1}: No calibration data ({2})'.format(
                self.color, which.capitalize(), filename))
        except Exception as e:
            print('ERROR: Tilt ({0}): Unable to initialise {1} calibration data ({2}) - {3}'.format(
                self.color, which.capitalize(), filename, e.message))
            # Attempt to close the file
            if csvFile is not None:
                # Close file
                csvFile.close()

        # If more than one values, use Polyfill
        if len(actualValues) >= 1:
            poly = numpy.poly1d(numpy.polyfit(originalValues, actualValues, deg=min(3, len(x)-1)))
            returnFunction = lambda x: poly(x)
            print('Tilt ({0}): Initialized {1} Calibration: Polyfill'.format(self.color, which.capitalize()))

        else:
            returnFunction = lambda x: x

        return returnFunction


class TiltManager:
    """
    Manages the monitoring of all Tilts and storing the read values
    """
    threads = []

    def __init__(self, color, averagingPeriod = 0, medianWindow = 0, dev_id = 0):
        """
        Initializes TiltManager class with default values

        :param color: Tilt color to be managed
        :param averagingPeriod: Time period in seconds for noise smoothing
        :param medianWindow: Median filter setting in number of  entries
        :param dev_id: Device ID of the local Bluetooth device to use
        """

        self.color = color
        self.dev_id = dev_id
        self.averagingPeriod = averagingPeriod
        self.medianWindow = medianWindow
        self.tilt = Tilt(color, self.averagingPeriod, self.medianWindow)
        self.conn = None
        self.btctrl = None
        self.event_loop = None
        self.mysocket = None
        self.fac = None

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
                print(filename)

                # BT Device ID
                try:
                    self.dev_id = config.getint("Manager", "DeviceID")
                except:
                    pass

                # Time period for noise smoothing
                try:
                    self.averagingPeriod = config.getint("Manager", "AvgWindow")
                except:
                    pass

                # Median filter setting
                try:
                    self.medianWindow = config.getint("Manager", "MedWindow")
                except:
                    pass

            except Exception as e:
                print('\nWARNING: Config file does not exist or cannot be read: ({0}): {1}\n'.format(filename, e.message))

        else:
            print('\nWARNING: Config file does not exist: {0}\n'.format(filename))

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

    def storeValue(self, color, temperature, gravity, battery):
        """
        Store Tilt values

        :param temperature: Temperature value to be stored
        :param gravity: Gravity value to be stored
        :param battery: Battery age value to be stored
        :return: None
        """

        self.tilt.setValues(color, temperature, gravity, battery)

    def getValue(self):
        """
        Retrieve Tilt value

        :return: Tilt value
        """

        returnValue = self.tilt.getValues()
        return returnValue

    def decode(self, packet):
        # Tilt format based on iBeacon format and filter includes Apple iBeacon
        # identifier portion (4c000215) as well as Tilt specific uuid preamble (a495)

        TILT = '4c000215a495'

        data = {}

        raw_data = packet.retrieve('Payload for mfg_specific_data')
        if raw_data:
            pckt = raw_data[0].val
            payload = raw_data[0].val.hex()
            mfg_id = payload[0:12]
            rssi = packet.retrieve('rssi')
            mac = packet.retrieve("peer")
            if mfg_id == TILT:
                data['uuid'] = payload[8:40]
                data['major'] = unpack('>H', pckt[20:22])[0]  # Temperature in degrees F
                data['minor'] = unpack('>H', pckt[22:24])[0]  # Specific gravity x1000
                # tx_power is weeks since battery change (0-152 when converted
                # to unsigned 8 bit integer) and other TBD operation codes
                data['tx_power'] = unpack('>b', pckt[24:25])[0]
                data['rssi'] = rssi[-1].val
                data['mac'] = mac[-1].val

                return json.dumps(data).encode('utf-8')

    def blecallback(self, data):
        packet = aios.HCI_Event()
        packet.decode(data)
        response = self.decode(packet)
        if response:
            #print("{}".format(response)) # TODO DEBUG
            tiltdata = json.loads(response.decode('utf-8', 'ignore'))
            color = self.tiltName(tiltdata['uuid'])
            gravity = int(tiltdata['minor']) / 1000  # Specific gravity
            temperature = int(tiltdata['major'] ) # Temperature in degrees F
            battery = int(tiltdata['tx_power']) # Battery age
            self.storeValue(color, temperature, gravity, battery)

    def stop(self):
        """
        Stop the BLE scanning thread

        :return: None
        """

        self.btctrl.stop_scan_request()
        command = aios.HCI_Cmd_LE_Advertise(enable=False)
        self.btctrl.send_command(command)

        asyncio.gather(*asyncio.Task.all_tasks()).cancel()
        for thread in self.threads:
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
            thread.join()

        self.event_loop.close()
        return

    def start(self):
        """
        Starts the BLE scanning thread

        :return: None
        """

        self.event_loop = asyncio.get_event_loop()
        # First create and configure a raw socket
        self.mysocket = aios.create_bt_socket(self.dev_id)

        # Create a connection with the STREAM socket
        self.fac = self.event_loop._create_connection_transport(self.mysocket, aios.BLEScanRequester, None, None)
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


def main():
    """
    Test function executed when this file is run as a discrete script

    :return: None
    """

    tiltColor = 'Purple'

    #tilt = TiltManager(tiltColor, 300, 10000, 0)
    tilt = TiltManager(tiltColor, 300, 10000, 0)
    tilt.loadSettings()
    tilt.start()

    try:
        print("Reporting Tilt values every 5 seconds. Ctrl-C to stop.")
        while 1:
            # If we are running Tilt, get current values
            if tilt:
                sleep(5)
                # Check each of the Tilt colors
                for color in TILT_COLORS:
                    if color == tiltColor:
                        tiltValue = tilt.getValue()
                        if tiltValue is not None:
                            temperature = round(tiltValue.temperature, 2)
                            gravity = round(tiltValue.gravity, 3)
                            battery = tiltValue.battery
                            print("{0}: Temp = {1}°F, Gravity = {2}, Battery = {3} weeks old.".format(
                                color, temperature, gravity, battery))
                        else:
                            print("\nColor {0} report: No results returned.".format(color))

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
