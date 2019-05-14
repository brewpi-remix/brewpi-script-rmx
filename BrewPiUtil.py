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
import BrewPiProcess
import psutil
from psutil import process_iter as ps
from time import sleep, strftime
import BrewPiSocket

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
            with open(path, 'w'):
                    os.utime(path, None)
            os.chmod(path, 0666)
            # File creation successful
            return True
        except:
            # File creation failure
            print("\nUnable to create {0}.".format(path))
            return False
    else:
        # print("\nFile already exists at {0}.".format(path))
        return None


def findSerialPort(bootLoader):
    (port, name) = autoSerial.detect_port(bootLoader)
    return port


def setupSerial(config, baud_rate=57600, time_out=1.0, wtime_out=1.0, noLog=False):
    ser = None
    dumpSerial = config.get('dumpSerial', False)

    error1 = None
    error2 = None
    # open serial port
    tries = 0
    if noLog:
        printStdErr("Opening serial port.")
    else:
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
                error = '{0} {1}'.format(error, str(e))
        if ser:
            break
        tries += 1
        sleep(1)

    if ser:
        # Discard everything in serial buffers
        ser.flushInput()
        ser.flushOutput()
    else:
        if noLog:
            logMessage("Error(s) while opening serial port: {0}\n".format(error))
        else:
            printStdErr("Error(s) while opening serial port: {0}\n".format(error))

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


def stopThisChamber(scriptPath = '/home/brewpi/', wwwPath = '/var/www/html/'):
    # Quit BrewPi process running from this chamber
    scriptPath = addSlash(scriptPath)
    wwwPath = addSlash(wwwPath)

    dontRunFilePath = '{0}do_not_run_brewpi'.format(wwwPath)

    printStdErr("\nStopping this chamber's instance(s) of BrewPi to check/update controller.")
    
    # Create do not run file
    dontRunCreated = False
    try:
        result = createDontRunFile(dontRunFilePath)
        if result is False:
            # Unable to create semaphore
            dontRunCreated = False
            return False
        if result is None:
            # File already existed
            dontRunCreated = False
            pass
        if result is True:
            # Created dontrunfile
            dontRunCreated = True
            pass
    except:
        printStdErr("\nUnable to call createDontRunFile().")
        return False

    try:
        procKilled = False
        i = 0
        for proc in psutil.process_iter():
            if any('python' in proc.name() and '{0}brewpi.py'.format(scriptPath) in s for s in proc.cmdline()):
                i += 1
                beerSocket = '{0}BEERSOCKET'.format(scriptPath)
                pid = proc.pid
                # TODO: Figure out how to send a stopMessage to socket?
                #printStdErr('\nStopping BrewPi in {0}.'.format(scriptPath))
                #socket = BrewPiSocket.BrewPiSocket(config)
                #socket.connect()
                #socket.write('stopScript') # This does not work
                #printStdErr('\nPausing 5 seconds to allow process to exit normally.')
                # If proc still exists, continue
                if proc.is_running():
                    printStdErr('\nStopping BrewPi with PID {0}.'.format(proc.pid))
                    try:
                        proc.terminate()
                        sleep(5)
                        if proc.is_running():
                            printStdErr('\nProcess still exists. Terminating BrewPi with PID {0}.'.format(proc.pid))
                            proc.kill()
                            sleep(5)
                            if proc.is_running():
                                printStdErr("\nUnable to stop process {0}, no error returned".format(proc.pid))
                                procKilled = False
                            else:
                                procKilled = True
                        else:
                            procKilled = True
                    except:
                        printStdErr("\nUnable to stop process {0}, are you running as root?".format(proc.pid))
                        procKilled = False
                else:
                    procKilled = None # Proc shut down for some other reason
        if i == 0:
            procKilled = None # BrewPi was not running
    except:
        printStdErr("\nUnable to iterate processes.")
        procKilled = False

    if dontRunCreated and procKilled:
        # Both file created and proc killed
        return True
    elif procKilled is None and not dontRunCreated:
        # File existed and proc did not exist
        return None
    elif dontRunCreated and not procKilled:
        # Created file but proc was not killed, remove file
        try:
            removeDontRunFile(dontRunFilePath)
        except:
            printStdErr("\nUnable to remove {0}.".format(dontRunFilePath))
        return False
    elif procKilled and not dontRunCreated:
        # Proc killed but file already existed
        return None


def asciiToUnicode(s):
    # Remove extended ascii characters from string, because they can raise
    # UnicodeDecodeError later
    s = s.replace(chr(0xB0), '&deg')
    return unicode(s, 'ascii', 'ignore')
