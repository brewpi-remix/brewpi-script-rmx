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
import subprocess as sub
import time
import simplejson as json
import os
import brewpiVersion
import expandLogMessage
from MigrateSettings import MigrateSettings
from sys import stderr
import BrewPiUtil as util
import subprocess
import platform
import sys


msg_map = {"a": "Arduino"}


def printStdErr(*objs):
    # Log to stderr.txt
    print(*objs, file=sys.stderr)
    sys.stderr.flush()


def printStdOut(*objs):
    # Log to stdout.txt
    print(*objs, file=sys.stdout)
    sys.stderr.flush()


def asbyte(v):
    return chr(v & 0xFF)


class LightYModem:
    """
    Receive_Packet
    - first byte SOH/STX (for 128/1024 byte size packets)
    - EOT (end)
    - CA CA abort
    - ABORT1 or ABORT2 is abort

    Then 2 bytes for seqno (although the sequence number isn't checked)

    Then the packet data

    Then CRC16?

    First packet sent is a filename packet:
    - zero-terminated filename
    - file size (ascii) followed by space?
    """

    packet_len = 1024
    stx = 2
    eot = 4
    ack = 6
    nak = 0x15
    ca = 0x18
    crc16 = 0x43
    abort1 = 0x41
    abort2 = 0x61

    def __init__(self):
        self.seq = None
        self.ymodem = None

    def _read_response(self):
        ch1 = ''
        while not ch1:
            ch1 = self.ymodem.read(1)
        ch1 = ord(ch1)
        if ch1 == LightYModem.ack and self.seq == 0:    # may send also a crc16
            ch2 = self.ymodem.read(1)
        elif ch1 == LightYModem.ca:                   # cancel, always sent in pairs
            ch2 = self.ymodem.read(1)
        return ch1

    def _send_ymodem_packet(self, data):
        # pad string to 1024 chars
        data = data.ljust(LightYModem.packet_len)
        seqchr = asbyte(self.seq & 0xFF)
        seqchr_neg = asbyte((-self.seq-1) & 0xFF)
        crc16 = '\x00\x00'
        packet = asbyte(LightYModem.stx) + seqchr + seqchr_neg + data + crc16
        if len(packet) != 1029:
            raise Exception("packet length is wrong!")

        self.ymodem.write(packet)
        self.ymodem.flush()
        response = self._read_response()
        if response == LightYModem.ack:
            printStdErr("Sent packet nr %d " % (self.seq))
            self.seq += 1
        return response

    def _send_close(self):
        self.ymodem.write(asbyte(LightYModem.eot))
        self.ymodem.flush()
        response = self._read_response()
        if response == LightYModem.ack:
            self.send_filename_header("", 0)
            self.ymodem.close()

    def send_packet(self, file, output):
        response = LightYModem.eot
        data = file.read(LightYModem.packet_len)
        if len(data):
            response = self._send_ymodem_packet(data)
        return response

    def send_filename_header(self, name, size):
        self.seq = 0
        packet = name + asbyte(0) + str(size) + ' '
        return self._send_ymodem_packet(packet)

    def transfer(self, file, ymodem, output):
        self.ymodem = ymodem
        # file: the file to transfer via ymodem
        # ymodem: the ymodem endpoint (a file-like object supporting write)
        # output: a stream for output messages
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0, os.SEEK_SET)
        response = self.send_filename_header("binary", size)
        while response == LightYModem.ack:
            response = self.send_packet(file, output)

        file.close()
        if response == LightYModem.eot:
            self._send_close()

        return response


def fetchBoardSettings(boardsFile, boardType):
    boardSettings = {}
    for line in boardsFile:
        if line.startswith(boardType):
            # strip board name, period and \n
            setting = line.replace(boardType + '.', '', 1).strip()
            [key, sign, val] = setting.rpartition('=')
            boardSettings[key] = val
    return boardSettings


def loadBoardsFile(arduinohome):
    boardsFileContent = None
    try:
        boardsFileContent = open(
            arduinohome + 'hardware/arduino/boards.txt', 'rb').readlines()
    except IOError:
        printStdErr(
            "Could not read boards.txt from Arduino, probably because Arduino has not been installed.")
        printStdErr("Please install it with: 'sudo apt install arduino-core'")
    return boardsFileContent


def programController(config, boardType, hexFile, restoreWhat):
    programmer = SerialProgrammer.create(config, boardType)
    return programmer.program(hexFile, restoreWhat)


def json_decode_response(line):
    try:
        return json.loads(line[2:])
    except json.decoder.JSONDecodeError, e:
        printStdErr("\nJSON decode error: {0}".format(str(e)))
        printStdErr("\nLine received was: {0}".format(line))


class SerialProgrammer:
    @staticmethod
    def create(config, boardType):
        if boardType == 'arduino':
            msg_map["a"] = "Arduino"
            programmer = ArduinoProgrammer(config, boardType)
        if boardType == 'uno':
            msg_map["a"] = "Arduino"
            programmer = ArduinoProgrammer(config, boardType)
        else:
            msg_map["a"] = "Arduino"
            programmer = ArduinoProgrammer(config, boardType)
        return programmer

    def __init__(self, config):
        self.config = config
        self.restoreSettings = False
        self.restoreDevices = False
        self.ser = None
        self.versionNew = None
        self.versionOld = None
        self.oldSettings = {}

    def program(self, hexFile, restoreWhat):
        printStdErr("\n%(a)s program script started." % msg_map)

        self.parse_restore_settings(restoreWhat)

        if self.restoreSettings or self.restoreDevices:
            printStdErr("\nChecking old version before programming.")
            if not self.open_serial(self.config, 57600, 0.2):
                return 0
            self.delay_serial_open()
            # request all settings from board before programming
            if self.fetch_current_version():
                self.retrieve_settings_from_serial()
                self.save_settings_to_file()

        if not self.ser:
            if not self.open_serial(self.config, 57600, 0.2):
                return 0
        self.delay_serial_open()

        if(hexFile):
            if not self.flash_file(hexFile):
                return 0

        self.fetch_new_version()
        self.reset_settings()
        if self.restoreSettings or self.restoreDevices:
            printStdErr(
                "\nChecking which settings and devices may be restored.")
        if self.versionNew is None:
            printStdErr("\nWarning: Cannot receive version number from controller after programming.",
                         "\nRestoring settings/devices settings failed.")
            return 0

        if not self.versionOld and (self.restoreSettings or self.restoreDevices):
            printStdErr("\nCould not receive valid version number from old board, no settings/devices",
                        "\nhave been restored.")
            return 0

        if self.restoreSettings:
            printStdErr("\nTrying to restore compatible settings from {0} to {1}".format(self.versionOld.toString(), self.versionNew.toString()))

            if(self.versionNew.isNewer("0.2")):
                printStdErr(
                    "\nSettings may only be restored when updating to BrewPi 0.2.0 or higher")
                self.restoreSettings = False

        if self.restoreSettings:
            self.restore_settings()

        if self.restoreDevices:
            self.restore_devices()

        printStdErr("\n%(a)s program script complete." % msg_map)
        self.ser.close()
        self.ser = None
        return 1

    def parse_restore_settings(self, restoreWhat):
        restoreSettings = False
        restoreDevices = False
        if 'settings' in restoreWhat:
            if restoreWhat['settings']:
                restoreSettings = True
        if 'devices' in restoreWhat:
            if restoreWhat['devices']:
                restoreDevices = True
        # Even when restoreSettings and restoreDevices are set to True here,
        # they might be set to false due to version incompatibility later

        printStdErr("\nSettings will {0}be restored{1}.".format(("" if restoreSettings else "not "), (" if possible" if restoreSettings else "")))
        printStdErr("\nDevices will {0}be restored{1}.\n".format(("" if restoreDevices else "not "), (" if possible" if restoreDevices else "")))

        self.restoreSettings = restoreSettings
        self.restoreDevices = restoreDevices

    def open_serial(self, config, baud, timeout):
        if self.ser:
            self.ser.close()
        self.ser = None
        self.ser = util.setupSerial(config, baud, timeout, 1.0, True)
        if self.ser is None:
            return False
        return True

    def open_serial_with_retry(self, config, baud, timeout):
        # reopen serial port
        retries = 30
        self.ser = None
        while retries:
            time.sleep(1)
            if self.open_serial(config, baud, timeout):
                return True
            retries -= 1
        return False

    def delay_serial_open(self):
        pass

    def fetch_version(self, msg):
        version = brewpiVersion.getVersionFromSerial(self.ser)
        if version is None:
            printStdErr("\nWarning: Cannot receive version number from controller. Your controller is",
                        "\neither not programmed yet or running a very old version of BrewPi. It will",
                        "\nbe reset to defaults.")
        else:
            printStdErr("{0}\nFound:\n{1}\non port:{2}".format(msg, version.toExtendedString(), self.ser.name))
        return version

    def fetch_current_version(self):
        self.versionOld = self.fetch_version("\nChecking current version:\n")
        return self.versionOld

    def fetch_new_version(self):
        self.versionNew = self.fetch_version("\nChecking new version:\n")
        return self.versionNew

    def retrieve_settings_from_serial(self):
        ser = self.ser
        self.oldSettings.clear()
        printStdErr("\nRequesting old settings from %(a)s." % msg_map)
        expected_responses = 2
        # versions older than 2.0.0 did not have a device manager
        if not self.versionOld.isNewer("0.2.0"):
            expected_responses += 1
            ser.write("d{}")  # installed devices
            time.sleep(1)
        ser.write("c")  # control constants
        ser.write("s")  # control settings
        time.sleep(2)

        while expected_responses:
            line = ser.readline()
            if line:
                line = util.asciiToUnicode(line)
                if line[0] == 'C':
                    expected_responses -= 1
                    self.oldSettings['controlConstants'] = json_decode_response(
                        line)
                elif line[0] == 'S':
                    expected_responses -= 1
                    self.oldSettings['controlSettings'] = json_decode_response(
                        line)
                elif line[0] == 'd':
                    expected_responses -= 1
                    self.oldSettings['installedDevices'] = json_decode_response(
                        line)

    def save_settings_to_file(self):
        # This is format" "2019-01-08-16-50-15"
        oldSettingsFileName = 'settings-{0}.json'.format(time.strftime("%Y-%m-%dT%H-%M-%S"))
        # oldSettingsFileName = 'settings-' + time.strftime("%b-%d-%Y-%H-%M-%S") + '.json' # This is format: "Jan-08-2019-16-31-56"
        settingsBackupDir = '{0}settings/controller-backup/'.format(util.addSlash(util.scriptPath()))
        if not os.path.exists(settingsBackupDir):
            os.makedirs(settingsBackupDir, 0777)

        oldSettingsFilePath = os.path.join(
            settingsBackupDir, oldSettingsFileName)
        oldSettingsFile = open(oldSettingsFilePath, 'wb')
        oldSettingsFile.write(json.dumps(self.oldSettings))
        oldSettingsFile.truncate()
        oldSettingsFile.close()
        # Make sure file can be accessed by all in case the script ran as root
        os.chmod(oldSettingsFilePath, 0777)
        printStdErr("\nSaved old settings to file {0}.".format(oldSettingsFileName))

    def delay(self, countDown):
        printStdErr("")
        while countDown > 0:
            time.sleep(1)
            printStdErr("Back up in {0}.".format(str(countDown)))
            countDown -= 1

    def reset_settings(self, setTestMode=False):
        printStdErr("\nResetting EEPROM to default settings.")
        self.ser.write('E\n')
        if setTestMode:
            self.ser.write('j{mode:t}')
        time.sleep(5)  # resetting EEPROM takes a while, wait 5 seconds
        # read log messages from arduino
        while 1:  # read all lines on serial interface
            line = self.ser.readline()
            if line:  # line available?
                if line[0] == 'D':
                    self.print_debug_log(line)
            else:
                break

    def print_debug_log(self, line):
        try:  # debug message received
            expandedMessage = expandLogMessage.expandLogMessage(line[2:])
            printStdErr(expandedMessage)
        except Exception, e:  # catch all exceptions, because out of date file could cause errors
            printStdErr("\nError while expanding log message: {0}".format(str(e)))
            printStdErr(("%(a)s debug message: " % msg_map) + line[2:])

    def restore_settings(self):
        oldSettingsDict = self.get_combined_settings_dict(self.oldSettings)
        ms = MigrateSettings()
        restored, omitted = ms.getKeyValuePairs(oldSettingsDict,
                                                self.versionOld.toString(),
                                                self.versionNew.toString())

        printStdErr("\nMigrating these settings:\n{0}".format(json.dumps(restored.items())))
        printStdErr("\nOmitting these settings:\n{0}".format(json.dumps(omitted.items())))

        self.send_restored_settings(restored)

    def get_combined_settings_dict(self, oldSettings):
        # copy keys/values from controlConstants
        combined = oldSettings.get('controlConstants').copy()
        # add keys/values from controlSettings
        combined.update(oldSettings.get('controlSettings'))
        return combined

    def send_restored_settings(self, restoredSettings):
        for key in restoredSettings:
            setting = restoredSettings[key]
            command = "j{" + json.dumps(key) + ":" + \
                json.dumps(setting) + "}\n"
            self.ser.write(command)
            # make readline blocking for max 5 seconds to give the controller time to respond after every setting
            oldTimeout = self.ser.timeout
            self.ser.timeout = 5
            # read all replies
            while 1:
                line = self.ser.readline()
                if line:  # line available?
                    if line[0] == 'D':
                        self.print_debug_log(line)
                if self.ser.inWaiting() == 0:
                #if self.ser.readline() == 0:  # WiFi Change
                    break
            self.ser.timeout = 5

    def restore_devices(self):
        ser = self.ser

        oldDevices = self.oldSettings.get('installedDevices')
        if oldDevices:
            printStdErr("\nNow trying to restore previously installed devices:\n{0}".format(oldDevices))
        else:
            printStdErr("\nNo devices to restore.")
            return

        detectedDevices = None
        for device in oldDevices:
            printStdErr("\nRestoring device:\n{0}".format(json.dumps(device)))
            if "a" in device.keys():  # check for sensors configured as first on bus
                if int(device['a'], 16) == 0:
                    printStdErr("A OneWire sensor was configured to be autodetected as the first sensor on the",
                                "\nbus, but this is no longer supported. We'll attempt to automatically find the",
                                "\naddress and add the sensor based on its address.")
                    if detectedDevices is None:
                        ser.write("h{}")  # installed devices
                        time.sleep(1)
                        # get list of detected devices
                        for line in ser:
                            if line[0] == 'h':
                                detectedDevices = json_decode_response(line)

                    for detectedDevice in detectedDevices:
                        if device['p'] == detectedDevice['p']:
                            # get address from sensor that was first on bus
                            device['a'] = detectedDevice['a']

            ser.write("U" + json.dumps(device))

            requestTime = time.time()
            # read log messages from arduino
            while 1:  # read all lines on serial interface
                line = ser.readline()
                if line:  # line available?
                    if line[0] == 'D':
                        self.print_debug_log(line)
                    elif line[0] == 'U':
                        printStdErr(
                            ("%(a)s reports: device updated to: " % msg_map) + line[2:])
                        break
                if time.time() > requestTime + 5:  # wait max 5 seconds for an answer
                    break
        printStdErr("\nRestoring installed devices done.")


class ArduinoProgrammer(SerialProgrammer):
    def __init__(self, config, boardType):
        SerialProgrammer.__init__(self, config)
        self.boardType = boardType

    def delay_serial_open(self):
        if self.boardType == "uno":
            # give the arduino some time to reboot in case of an Arduino UNO
            time.sleep(10)

    def flash_file(self, hexFile):
        config, boardType = self.config, self.boardType
        printStdErr("\nLoading programming settings from board.txt.")
        # location of Arduino sdk
        arduinohome = config.get('arduinoHome', '/usr/share/arduino/')
        # location of avr tools
        avrdudehome = config.get(
            'avrdudeHome', arduinohome + 'hardware/tools/')
        # default to empty string because avrsize is on path
        avrsizehome = config.get('avrsizeHome', '')
        # location of global avr conf
        avrconf = config.get('avrConf', avrdudehome + 'avrdude.conf')

        boardsFile = loadBoardsFile(arduinohome)
        if not boardsFile:
            return False
        boardSettings = fetchBoardSettings(boardsFile, boardType)

        # parse the Arduino board file to get the right program settings
        for line in boardsFile:
            if line.startswith(boardType):
                # strip board name, period and \n
                setting = line.replace(boardType + '.', '', 1).strip()
                [key, sign, val] = setting.rpartition('=')
                boardSettings[key] = val

        printStdErr("\nChecking hex file size with avr-size.")

        # start programming the Arduino
        avrsizeCommand = avrsizehome + 'avr-size ' + "\"" + hexFile + "\""

        # check program size against maximum size
        p = sub.Popen(avrsizeCommand, stdout=sub.PIPE,
                      stderr=sub.PIPE, shell=True)
        output, errors = p.communicate()
        if errors != "":
            printStdErr('\navr-size error: {0}'.format(errors))
            return False

        programSize = output.split()[7]
        printStdErr('\nProgram size: {0} bytes out of max {1}.'.format(programSize, boardSettings['upload.maximum_size']))

        # Another check just to be sure!
        if int(programSize) > int(boardSettings['upload.maximum_size']):
            printStdErr(
                "\nERROR: Program size is bigger than maximum size for your Arduino {0}.".format(boardType))
            return False

        hexFileDir = os.path.dirname(hexFile)
        hexFileLocal = os.path.basename(hexFile)

        time.sleep(1)
        # Get serial port while in bootloader
        bootLoaderPort = util.findSerialPort(bootLoader=True, my_port=config['port'])
        # bootLoaderPort = util.findSerialPort(bootLoader=True)
        if not bootLoaderPort:
            printStdErr("\nERROR: Could not find port in bootloader.")

        programCommand = (avrdudehome + 'avrdude' +
                          ' -F' +  # override device signature check
                          ' -e' +  # erase flash and eeprom before programming. This prevents issues with corrupted EEPROM
                          ' -p ' + boardSettings['build.mcu'] +
                          ' -c ' + boardSettings['upload.protocol'] +
                          ' -b ' + boardSettings['upload.speed'] +
                          ' -P ' + bootLoaderPort +
                          ' -U ' + 'flash:w:' + "\"" + hexFileLocal + "\"" +
                          ' -C ' + avrconf)

        printStdErr("\nProgramming Arduino with avrdude.")

        p = sub.Popen(programCommand, stdout=sub.PIPE,
                      stderr=sub.PIPE, shell=True, cwd=hexFileDir)
        output, errors = p.communicate()

        # avrdude only uses stderr, append its output to the returnString
        printStdErr("\nResult of invoking avrdude:{0}".format(errors))

        if("bytes of flash verified" in errors):
            printStdErr("Avrdude done, programming successful.")
        else:
            printStdErr("There was an error while programming.")
            return False

        printStdErr("\nGiving the Arduino 10 seconds to reset.")
        self.delay(10)
        return True
