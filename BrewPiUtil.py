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
import sys
from sys import path, stderr, stdout, platform
import os
import serial
import autoSerial
from psutil import process_iter
from time import sleep, strftime

try:
    import configobj
except ImportError:
    print("\nBrewPi requires ConfigObj to run, please install it with \n"
          "'sudo apt-get install python-configobj")
    exit(1)


def addSlash(path):
    """
    Adds a slash to the path, but only when it does not already have a slash at the end
    Params: a string
    Returns: a string
    """
    if not path.endswith('/'):
        path = '{0}/'.format(path)
    return path


def readCfgWithDefaults(cfg):
    """
    Reads a config file with the default config file as fallback

    Params:
    cfg: string, path to cfg file
    defaultCfg: string, path to defaultConfig file.

    Returns:
    ConfigObj of settings
    """
    if not cfg:
        cfg = '{0}settings/config.cfg'.format(addSlash(path[0]))

    # Added to fix default config file detection for multi-chamber
    if cfg:
        defaultCfg = '{0}/defaults.cfg'.format(os.path.dirname(cfg))

    #  Conditional line added to fix default config file detection for multi-chamber
    if not defaultCfg:
        defaultCfg = '{0}settings/defaults.cfg'.format(addSlash(scriptPath()))

    config = configobj.ConfigObj(defaultCfg)

    if cfg:
        try:
            userConfig = configobj.ConfigObj(cfg)
            config.merge(userConfig)
        except configobj.ParseError:
            logMessage(
                "ERROR: Could not parse user config file {0}.".format(cfg))
        except IOError:
            logMessage(
                "Could not open user config file {0}. Using default config file.".format(cfg))
    return config


def configSet(configFile, settingName, value):
    if not os.path.isfile(configFile):
        logMessage("Config file {0} does not exist.".format(configFile))
        logMessage("Creating with defaults")
    try:
        config = configobj.ConfigObj(configFile)
        config[settingName] = value
        config.write()
        os.chmod(configFile, 0770)
    except IOError as e:
        logMessage(
            "I/O error({0}) while updating {1}: {2}\n".format(e.errno, configFile, e.strerror))
        logMessage("Your permissions likely are not set correctly.  To fix\n",
                   "this, run 'sudo ./fixPermissions.sh' from your Tools directory.")
    return readCfgWithDefaults(configFile)  # Return updated ConfigObj


def printStdErr(*objs):
    print(*objs, file=sys.stderr)


def printStdOut(*objs):
    print(*objs, file=sys.stdout)


def logMessage(*objs):
    """
    Prints a timestamped message to stdout
    """
    printStdOut(strftime("%Y-%m-%d %H:%M:%S  "), *objs)


def scriptPath():
    """
    Return the path of BrewPiUtil.py. __file__ only works in modules, not in the main script.
    That is why this function is needed.
    """
    return os.path.dirname(__file__)


def removeDontRunFile(path='/var/www/html/do_not_run_brewpi'):
    if os.path.isfile(path):
        try:
            os.remove(path)
            if not platform.startswith('win'):  # Daemon not available
                print("\nBrewPi script will restart automatically.")
                return None
            return True
        except:
            print("\nUnable to remove {0}.".format(path))
            return False
    else:
        print("\n{0} does not exist.".format(path))
        return None


def createDontRunFile(path='/var/www/html/do_not_run_brewpi'):
    if not os.path.isfile(path):
        try:
            with open(path, 'a'):
                    os.utime(path, None)
            os.chmod(path, 0666)
            return True
        except:
            print("\nUnable to create {0}.".format(path))
            return False
    else:
        print("\nFile already exists at {0}.".format(path))
        return None


def findSerialPort(bootLoader):
    (port, name) = autoSerial.detect_port(bootLoader)
    return port


def setupSerial(config, baud_rate=57600, time_out=1.0, wtime_out=1.0):
    ser = None
    dumpSerial = config.get('dumpSerial', False)

    error1 = None
    error2 = None
    # open serial port
    tries = 0
    logMessage("Opening serial port.")
    while tries < 10:
        error = ""
        for portSetting in [config['port'], config['altport']]:
            if portSetting == None or portSetting == 'None' or portSetting == "none":
                continue  # skip None setting
            if portSetting == "auto":
                port = findSerialPort(bootLoader=False)
                if not port:
                    error = "\nCould not find compatible serial device."
                    continue  # continue with altport
            else:
                port = portSetting
            try:
                ser = serial.serial_for_url(
                    port, baudrate=baud_rate, timeout=time_out, write_timeout=wtime_out)
                if ser:
                    break
            except (IOError, OSError, serial.SerialException) as e:
                error = '{0} {1}\n'.format(error, str(e))
        if ser:
            break
        tries += 1
        sleep(1)

    if ser:
        # Discard everything in serial buffers
        ser.flushInput()
        ser.flushOutput()
    else:
        logMessage("Error(s) while opening serial port: {0}\n".format(error))

    # Yes this is monkey patching, but I don't see how to replace the methods on
    # a dynamically instantiated type any other way
    if dumpSerial:
        ser.readOriginal = ser.read
        ser.writeOriginal = ser.write

        def readAndDump(size=1):
            r = ser.readOriginal(size)
            stdout.write(r)
            return r

        def writeAndDump(data):
            ser.writeOriginal(data)
            stderr.write(data)

        ser.read = readAndDump
        ser.write = writeAndDump

    return ser


def stopThisChamber(myPath='/home/brewpi/'):
    # Quit BrewPi process running from this chamber
    configFile = addSlash(myPath) + 'settings/config.cfg'
    config = readCfgWithDefaults(configFile)
    wwwPath = addSlash(config['wwwPath'])
    myPath = addSlash(config['scriptPath'])
    dontRunFilePath = '{0}do_not_run_brewpi'.format(wwwPath)

    printStdErr("\nStopping this chamber's instance(s) of BrewPi to check/update controller.")
    
    # Create do not run file
    try:
        result = createDontRunFile(dontRunFilePath)
        if result is False:
            return False
        if result is None:
            # File already existed
            pass
        if result is True:
            printStdErr('\nPausing 5 seconds to allow process to exit normally.')
            sleep(5)
    except:
        printStdErr("\nUnable to call createDontRunFile().")
        return False

    # Stop this chamber's process
    try:
        for proc in process_iter(attrs=['pid', 'name', 'cmdline']):
            if 'python' in proc.info['name'] and '{0}brewpi.py'.format(myPath) in proc.info['cmdline']:
                printStdErr("\nAttempting to stop process {0}.".format(proc.info['pid']))
                try:
                    proc.terminate()
                    return True             
                except:
                    printStdErr("\nUnable to stop process {0}, are you running as root?".format(proc.info['pid']))
                    return False
            else:
                # BrewPi was already stopped
                return None
        return None
    except:
        printStdErr("\nUnable to iterate processes.")
        return False


def asciiToUnicode(s):
    # Remove extended ascii characters from string, because they can raise
    # UnicodeDecodeError later
    s = s.replace(chr(0xB0), '&deg')
    return unicode(s, 'ascii', 'ignore')
