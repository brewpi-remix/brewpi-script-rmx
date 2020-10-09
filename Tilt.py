#!/usr/bin/python3

import sys
from os.path import dirname, abspath, exists, isfile, getmtime
from csv import reader
from time import time, sleep
from configparser import ConfigParser
import subprocess
import asyncio
import argparse
import re
import datetime
import threading
import aioblescan as aiobs
from struct import unpack
import json
import numpy

import sentry_sdk
sentry_sdk.init("https://5644cfdc9bd24dfbaadea6bc867a8f5b@sentry.io/1803681")

# Tilt format based on iBeacon format and filter includes Apple iBeacon
# identifier portion (4c000215) as well as Tilt specific uuid preamble
# (a495)
TILT = '4c000215a495'
TILT_COLORS = [
    'Red', 'Green', 'Black', 'Purple', 'Orange', 'Blue', 'Yellow', 'Pink'
]
opts = None


class TiltManager:
    """
    Manages the monitoring of all Tilts and storing the read values
    """
    threads = []

    def __init__(self, color=None, averagingPeriod=0, medianWindow=0, dev_id=0):
        """
        Initializes TiltManager class with default values

        :param color: Tilt color to be managed
        :param averagingPeriod: Time period in seconds for noise smoothing
        :param medianWindow: Median filter setting in number of  entries
        :param dev_id: Device ID of the local Bluetooth device to use
        """
        self.tilt = None
        self.color = color
        self.dev_id = dev_id
        self.averagingPeriod = averagingPeriod
        self.medianWindow = medianWindow
        if color == None:
            self.tilt = [None] * len(TILT_COLORS)
            for i in range(len(TILT_COLORS)):
                self.tilt[i] = Tilt(TILT_COLORS[i], averagingPeriod, medianWindow)
        else:
            self.tilt = Tilt(color, averagingPeriod, medianWindow)
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

    def storeValue(self, color, temperature, gravity, battery):
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
                    self.tilt[i].setValues(
                        color, temperature, gravity, battery)
        else:
            self.tilt.setValues(color, temperature, gravity, battery)

    def getValue(self, color):
        """
        Retrieve Tilt value

        :return: Tilt value
        """
        if isinstance(self.tilt, list):
            for i in range(len(TILT_COLORS)):
                if TILT_COLORS[i] == color:
                    returnValue = self.tilt[i].getValues(color)
        else:
            returnValue = self.tilt.getValues(color)
        return returnValue

    def decode(self, packet):
        # Tilt format based on iBeacon format and filter includes Apple iBeacon
        # identifier portion (4c000215) as well as Tilt specific uuid preamble (a495)

        global TILT
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
                data['major'] = unpack('>H', pckt[20:22])[0]
                data['minor'] = unpack('>H', pckt[22:24])[0]
                data['tx_power'] = unpack('>b', pckt[24:25])[0]
                data['rssi'] = rssi[-1].val
                data['mac'] = mac[-1].val
                return json.dumps(data).encode('utf-8')

    def blecallback(self, data):
        """
        Callback method for the Bluetooth process

        :return: None
        """
        packet = aiobs.HCI_Event()
        packet.decode(data)
        response = self.decode(packet)
        if response:
            tiltdata = json.loads(response.decode('utf-8', 'ignore'))
            color = self.tiltName(tiltdata['uuid'])
            gravity = int(tiltdata['minor']) / 1000
            temperature = int(tiltdata['major'])
            battery = int(tiltdata['tx_power'])
            self.storeValue(color, temperature, gravity, battery)

    def start(self):
        """
        Starts the BLE scanning thread

        :return: None
        """

        self.event_loop = asyncio.get_event_loop()
        # First create and configure a raw socket
        self.mysocket = aiobs.create_bt_socket(self.dev_id)

        # Create a connection with the STREAM socket
        self.fac = self.event_loop._create_connection_transport(
            self.mysocket, aiobs.BLEScanRequester, None, None)
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
        command = aiobs.HCI_Cmd_LE_Advertise(enable=False)
        self.btctrl.send_command(command)

        asyncio.gather(*asyncio.Task.all_tasks()).cancel()
        for thread in self.threads:
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)
            thread.join()

        self.event_loop.close()
        return


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

    def setValues(self, color, temperature, gravity, battery):
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
        self.values.append(TiltValue(color, calTemp, calGrav, battery))

    def getValues(self, color):
        """
        Returns the temperature, gravity & battery values of a given Tilt

        This will be the latest read value unless averaging / median has
        been enabled
        """
        colorValues = []
        returnValue = None

        if len(self.values) > 0:
            for i in range(len(self.values)):
                if self.values[i].color == color:
                    temperature = self.values[i].temperature
                    gravity = self.values[i].gravity
                    battery = self.values[i].battery
                    colorValues.append(
                        TiltValue(color, temperature, gravity, battery))
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

        :return:  Averaged values
        """
        returnValue = None
        if len(values) > 0:
            returnValue = TiltValue('', 0, 0, 0)
            for value in values:
                returnValue.temperature += value.temperature
                returnValue.gravity += value.gravity

            # Average values
            returnValue.temperature /= len(values)
            returnValue.gravity /= len(values)

            # Round values
            returnValue.temperature = returnValue.temperature
            returnValue.gravity = returnValue.gravity

            # Make sure battery returns only real values (> 0)
            returnValue.battery = getBatteryValue(values, color)

        return returnValue

    def medianValues(self, color, values, window=3):
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
        if len(values) < window:
            window = len(values)

        returnValue = TiltValue('', 0, 0, 0)

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

        # Average values
        returnValue.temperature /= medianValueCount
        returnValue.gravity /= medianValueCount

        # Round values
        returnValue.temperature = returnValue.temperature
        returnValue.gravity = returnValue.gravity

        # Now just get the max of battery to filter out 0's
        returnValue.battery = self.getBatteryValue(values, color)

        return returnValue

    def getBatteryValue(self, values, color):
        batteryValues = []
        if len(values) > 0:
            for i in range(len(values)):
                if values[i].color == color:
                    batteryValues.append(values[i].battery)
            return max(batteryValues)
        else:
            return 0

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
                        originalValues.append(float(row[0]))
                        actualValues.append(float(row[1]))
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
        "-m",
        "--mac",
        type=check_mac,
        action='append',
        help="filter Tilts by this/these MAC address(es)")
    parser.add_argument(
        "-d",
        "--hci",
        type=int,
        default=0,
        help="select the hci device to use (default 0, i.e. hci0)")
    parser.add_argument(
        "-c",
        "--color",
        type=str,
        default=None,
        help="filter by this Tilt color")
    parser.add_argument(
        "-a",
        "--average",
        type=int,
        default=None,
        help="seconds window for averaging")
    parser.add_argument(
        "-n",
        "--median",
        type=int,
        default=None,
        help="number of entries in median window")
    try:
        opts = parser.parse_args()
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
    global opts
    opts = parseArgs()
    tiltColorName = None
    averaging = 300
    median = 10000
    device_id = 0

    # Check that Python has the correct capabilities set
    hasCaps, pythonPath, getCapValues = checkSetcap()
    if not hasCaps:
        print("\nERROR: Missing cap flags on python executable.\nExecutable:\t{}\nCap Values:\t{}\n".format(
            pythonPath, getCapValues))
        return

    if opts.color:
        tiltColor = opts.color.title()
        tiltColorName = opts.color.title()
    else:
        tiltColor = None
        tiltColorName = "All"

    if opts.median:
        median = opts.median

    if opts.average:
        average = opts.average

    if opts.hci:
        device_id = opts.hci

    tilt = TiltManager(tiltColor, averaging, median, device_id)
    tilt.loadSettings()
    tilt.start()

    try:
        print(
            "\nReporting {} Tilt values every 5 seconds. Ctrl-C to stop.".format(tiltColor))
        while 1:
            # If we are running Tilt, get current values
            if tilt:
                sleep(5)
                # Check each of the Tilt colors
                for color in TILT_COLORS:
                    if color == tiltColor or tiltColor == None:
                        tiltValue = tilt.getValue(color)
                        if tiltValue is not None:
                            temperature = round(tiltValue.temperature, 2)
                            gravity = round(tiltValue.gravity, 3)
                            battery = tiltValue.battery
                            print("{0}: Temp = {1}°F, Gravity = {2}, Battery = {3} weeks old.".format(
                                color, temperature, gravity, battery))
                        else:
                            print(
                                "Color {0} report: No results returned.".format(color))

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
