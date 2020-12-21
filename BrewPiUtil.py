#!/usr/bin/python3

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


import sys
from sys import path, stderr, stdout, platform
import os
import serial
import psutil
import stat
import pwd
import grp
import git
from psutil import process_iter as ps
from time import sleep, strftime
from configobj import ConfigObj, ParseError
import BrewPiSocket
import autoSerial
import BrewPiProcess


def addSlash(path):
    """
    Adds a slash to the path, but only when it does not already have a slash at the end
    Params: a string
    Returns: a string
    """
    if not path.endswith('/'):
        path = '{0}/'.format(path)
    return path


def readCfgWithDefaults(configFile = None):
    """
    Reads a config file with the default config file as fallback

    Params:
    configFile: string, path to config file (defaults to {scriptpath}/settings/config.cfg)

    Returns:
    ConfigObj of settings
    """

    # Get settings folder
    settings = '{0}settings/'.format(scriptPath())

    # The configFile is always a named file rather than the default one
    if not configFile:
        configFile = '{0}config.cfg'.format(settings)

    # Now grab the default config file
    defaultFile = '{0}defaults.cfg'.format(settings)

    error = 0
    try:
        defCfg = ConfigObj(defaultFile, file_error=True)
    except ParseError:
        error = 1
        logError("Could not parse default config file:")
        logError("{0}".format(defaultFile))
    except IOError:
        error = 1
        logError("Could not open default config file:")
        logError("{0}".format(defaultFile))

    # Write default.cfg file if it's missing
    if error:
        defCfg = ConfigObj()
        defCfg.filename = defaultFile
        defCfg['scriptPath'] = '/home/brewpi/'
        defCfg['wwwPath'] = '/var/www/html/'
        defCfg['port'] = 'auto'
        defCfg['altport'] = None
        defCfg['boardType'] = 'arduino'
        defCfg['beerName'] = 'My BrewPi Remix Run'
        defCfg['interval'] = '120.0'
        defCfg['dataLogging'] = 'active'
        defCfg['logJson'] = True
        defCfg.write()

    if configFile:
        try:
            userConfig = ConfigObj(configFile, file_error=True)
            defCfg.merge(userConfig)
        except ParseError:
            error = 1
            logError("Could not parse user config file:")
            logError("{0}".format(configFile))
        except IOError:
            error = 1
            logMessage("No user config file found:")
            logMessage("{0}".format(configFile))
            logMessage("Using default configuration.")

    # Fix pathnames
    defCfg['scriptPath'] = addSlash(defCfg['scriptPath'])
    defCfg['wwwPath'] = addSlash(defCfg['wwwPath'])
    return defCfg


def configSet(settingName, value, configFile = None):
    """
    Merge in new or updated configuration

    Params:
    settingName: Name of setting to write
    value: Value of setting to write
    configFile (optional): Name of configuration file (defaults to config.cfg)

    Returns:
    ConfigObj of current settings
    """
    settings = '{0}settings/'.format(scriptPath())
    newConfigFile = "{0}config.cfg".format(settings)
    fileExists = True

    # If we passed a configFile
    if configFile:
        # Check for the file
        if not os.path.isfile(configFile):
            # If there's no configFile, assume a "/" in it means a valid path at least
            if "/" in configFile:
                # Path seems legit, create it later
                fileExists = False
            else:
                # Maybe it was a simple filename, add path and try again
                configFile = "{0}{1}".format(settings, configFile)
                if not os.path.isfile(configFile):
                    # Still no dice
                    fileExists = False
        # No configFile passed
        else:
            # Path/File exists
            fileExists = True
    # No config file passed
    else:
        # Default to config.cfg in settings directory
        configFile = newConfigFile
        if not os.path.isfile(configFile):
            fileExists = False

    # If there's no config file, create it and set permissions
    if not fileExists:
        try:
            # Create the file
            open(configFile, 'a').close()
            # chmod 660 the new file
            fileMode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
            os.chmod(configFile, fileMode)
            logMessage("Config file {0} did not exist, created new file.".format(configFile))
        except:
            logError("Unable to create '{0}'.".format(configFile))
            return readCfgWithDefaults()

    # Add or update the setting
    try:
        comment = "File created or updated on {0}\n#".format(strftime("%Y-%m-%d %H:%M:%S"))
        config = ConfigObj()
        config = readCfgWithDefaults()
        config.initial_comment = [comment]
        config.filename = configFile
        config[settingName] = value
        config.write()
    except ParseError:
        logError("Invalid configuration settings: '{0}': '{1}'".format(settingName, value))
    except IOError as e:
        logError("I/O error({0}) while setting permissions on:".format(e.errno))
        logError("{0}:".format(configFile))
        logError("{0}.".format(e.strerror))
        logError("You are not running as root or brewpi, or your")
        logError("permissions are not set correctly. To fix this, run:")
        logError("sudo {0}utils/doPerms.sh".format(scriptPath()))
    # chmod 660 the config file just in case
    try:
        fileMode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP
        os.chmod(configFile, fileMode)
    except IOError as e:
        logError("I/O error({0}) while setting permissions on:".format(e.errno))
        logError("{0}:".format(configFile))
        logError("{0}.".format(e.strerror))
        logError("You are not running as root or brewpi, or your")
        logError("permissions are not set correctly. To fix this, run:")
        logError("sudo {0}utils/doPerms.sh".format(scriptPath()))
    return readCfgWithDefaults(configFile)  # Return (hopefully updated) ConfigObj


def scriptPath():
    """
    Return the path of this file

    Params:
    None

    Returns:
    Path of module with trailing slash
    """
    return addSlash(os.path.dirname(os.path.abspath(__file__)))


def frozen():
    """
    Returns whether we are frozen via py2exe

    Params:
    None

    Returns:
    True if executing a frozen script, False if not
    """
    return hasattr(sys, "frozen")


def printStdErr(*objs):
    """
    Prints the values to environment's sys.stderr with flush
    """
    print(*objs, file=sys.stderr, flush=True)


def printStdOut(*objs):
    """
    Prints the values to environment's sys.stdout with flush
    """
    print(*objs, file=sys.stdout, flush=True)


def logMessage(*objs):
    """
    Prints a timestamped information message to stdout
    """
    if 'USE_TIMESTAMP_LOG' in os.environ:
        printStdOut(strftime("%Y-%m-%d %H:%M:%S [N]"), *objs)
    else:
        printStdOut(*objs)


def logWarn(*objs):
    """
    Prints a timestamped warning message to stdout
    """ 
    if 'USE_TIMESTAMP_LOG' in os.environ:
        printStdOut(strftime("%Y-%m-%d %H:%M:%S [W]"), *objs)
    else:
        printStdOut(*objs)


def logError(*objs):
    """
    Prints a timestamped message to stderr
    """
    if 'USE_TIMESTAMP_LOG' in os.environ:
        printStdErr(strftime("%Y-%m-%d %H:%M:%S [E]"), *objs)
    else:
        printStdErr(*objs)


def removeDontRunFile(path = None):
    """
    Removes the semaphore file which prevents script processing

    Returns:
    True: File deleted
    False: Unable to delete file
    None: File does not exist
    """
    if not path:
        config = readCfgWithDefaults()
        path = "{0}do_not_run_brewpi".format(config['wwwPath'])

    if os.path.isfile(path):
        try:
            os.remove(path)
             # Daemon not available under Windows
            if not platform.startswith('win'):
                logMessage("BrewPi script will restart automatically.")
                return None
            return True
        except IOError as e:
            logError("I/O error({0}) while setting deleting:".format(e.errno))
            logError("{0}:".format(path))
            logError("{0}.".format(e.strerror))
            logError("You are not running as root or brewpi, or your")
            logError("permissions are not set correctly. To fix this, run:")
            logError("sudo {0}utils/doPerms.sh".format(scriptPath()))
        except:
            logError("Unable to remove {0}.".format(path))
            return False
    else:
        logMessage("{0} does not exist.".format(path))
        return None


def createDontRunFile(path = None):
    """
    Creates the semaphore file which prevents script processing

    Returns:
    True: File created
    False: Unable to create file
    None: File already exists
    """
    if not path:
        config = readCfgWithDefaults()
        path = "{0}do_not_run_brewpi".format(config['wwwPath'])

    if not os.path.isfile(path):
        try:
            open(path, 'a').close()
            # chmod 660 the new file - make sure www-data can delete it
            fileMode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP # 660
            owner = 'brewpi'
            group = 'www-data'
            uid = pwd.getpwnam(owner).pw_uid
            gid = grp.getgrnam(group).gr_gid
            os.chown(path, uid, gid) # chown file
            os.chmod(path, fileMode) # chmod file
            logMessage("Semaphore {0} created.".format(path))
            return True
        except IOError as e:
            logError("I/O error({0}) while setting creating:".format(e.errno))
            logError("{0}:".format(path))
            logError("{0}.".format(e.strerror))
            logError("You are not running as root or brewpi, or your")
            logError("permissions are not set correctly. To fix this, run:")
            logError("sudo {0}utils/doPerms.sh".format(scriptPath()))
        except:
            # File creation failure
            logError("Unable to create {0}.".format(path))
            return False
    else:
        logMessage("Semaphore {0} exists.".format(path))
        return None


def findSerialPort(bootLoader, my_port=None):
    (port, name) = autoSerial.detect_port(bootLoader, my_port)
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
    elif procKilled is None and dontRunCreated:
        # Created file and proc did not exist
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
    #deg_symbol = bytes([0xB0]).decode(encoding="utf-8").strip()
    #s = s.replace(deg_symbol, '&deg')
    # This does nothing anymore
    return s


# Add unbuffered capabilities back for Python3
class Unbuffered(object):
   def __init__(self, stream):
       self.stream = stream

   def write(self, data):
       self.stream.write(data)
       self.stream.flush()

   def writelines(self, datas):
       self.stream.writelines(datas)
       self.stream.flush()

   def __getattr__(self, attr):
       return getattr(self.stream, attr)


def main():
    # Test the methods and classes
    #
    from pprint import pprint as pp
    path = "/home/brewpi"
    obj = ConfigObj()
    #
    # addSlash()
    print("Testing addslash(): Passing '{0}' returning '{1}'".format(path, addSlash(path)))
    # readCfgWithDefaults()
    obj = readCfgWithDefaults()
    print("Testing readCfgWithDefaults():")
    pp(obj)
    # configSet()
    oldObj = readCfgWithDefaults()
    oldValue = oldObj['altport']
    newObj = configSet('altport', 'Foo')
    newValue = newObj['altport']
    discard = configSet('altport', oldObj['altport'])
    print("Testing configSet():\n\tOld altport = {0}\n\tNew altport = {1}\n\tReturned to original value after test.".format(oldValue, newValue))
    # scriptPath()
    print("Testing: scriptPath() = {0}".format(scriptPath()))
    # frozen()
    print("Testing: frozen() = {0}".format(frozen()))
    # printStdErr()
    printStdErr("Testing printStdErr().")
    # printStdErr()
    printStdOut("Testing printStdOut().")
    # Test Date/time stamp messages:
    resetenv = False
    # Using timestamps - Leave it like we found it
    if not 'USE_TIMESTAMP_LOG' in os.environ:
        resetenv = True
        os.environ['USE_TIMESTAMP_LOG'] = 'True'
    # logMessage()
    logMessage("Testing logMessage().")
    # logError()
    logWarn("Testing logWarn().")
    # logError()
    logError("Testing logError().")
    if resetenv:
        del os.environ['USE_TIMESTAMP_LOG']
    # do_not_run_brewpi - Leave it like we found it
    print("Testing do_not_run_brewpi:")
    if not os.path.isfile(obj['wwwPath']):
        createDontRunFile()
        removeDontRunFile()
    else:
        removeDontRunFile()
        createDontRunFile()
    # def findSerialPort(bootLoader, my_port=None):
    # def setupSerial(config, baud_rate=57600, time_out=1.0, wtime_out=1.0, noLog=False):
    # def stopThisChamber(scriptPath = '/home/brewpi/', wwwPath = '/var/www/html/'):
    # def asciiToUnicode(s):

if __name__ == "__main__":
    # Execute tests if run as a script
    main()
    sys.exit(0)  # Exit script
