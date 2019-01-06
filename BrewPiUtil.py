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

from __future__ import print_function
import time
import sys
import os
import serial
import autoSerial

try:
  import configobj
except ImportError:
  print("\nBrewPi requires ConfigObj to run, please install it with \n"
        "'sudo apt-get install python-configobj")
  sys.exit(1)

def addSlash(path):
  """
  Adds a slash to the path, but only when it does not already have a slash at the end
  Params: a string
  Returns: a string
  """
  if not path.endswith('/'):
    path += '/'
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
    cfg = addSlash(sys.path[0]) + 'settings/config.cfg'

  defaultCfg = scriptPath() + '/settings/defaults.cfg'
  config = configobj.ConfigObj(defaultCfg)

  if cfg:
    try:
      userConfig = configobj.ConfigObj(cfg)
      config.merge(userConfig)
    except configobj.ParseError:
      logMessage("ERROR: Could not parse user config file %s." % cfg)
    except IOError:
      logMessage("Could not open user config file %s. Using default config file." % cfg)
  return config

def configSet(configFile, settingName, value):
  if not os.path.isfile(configFile):
    logMessage("User config file %s does not exist, creating with defaults." % configFile)
  try:
    config = configobj.ConfigObj(configFile)
    config[settingName] = value
    config.write()
  except IOError as e:
    logMessage("I/O error(%d) while updating %s: %s \n" % (e.errno, configFile, e.strerror))
    logMessage("Your permissions likely are not set correctly.  To fix\n" + 
               "this, run 'sudo ./fixPermissions.sh' from your Tools directory.")
  return readCfgWithDefaults(configFile)  # return updated ConfigObj

def printStdErr(*objs):
  print(*objs, file=sys.stderr)

def printStdOut(*objs):
  print(*objs, file=sys.stdout)

def logMessage(message):
  """
  Prints a timestamped message to stderr
  """
  printStdErr(time.strftime("%b %d %Y %H:%M:%S   ") + message)

def scriptPath():
  """
  Return the path of BrewPiUtil.py. __file__ only works in modules, not in the main script.
  That is why this function is needed.
  """
  return os.path.dirname(__file__)

def removeDontRunFile(path='/var/www/do_not_run_brewpi'):
  if os.path.isfile(path):
    os.remove(path)
    if not sys.platform.startswith('win'):  # cron not available
      print("\nBrewPi script will restart automatically.")
  else:
    print("\nFile do_not_run_brewpi does not exist at %s." % path)

def findSerialPort(bootLoader):
  (port, name) = autoSerial.detect_port(bootLoader)
  return port

def setupSerial(config, baud_rate=57600, time_out=0.1):
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
          continue # continue with altport
      else:
        port = portSetting
      try:
        ser = serial.Serial(port, baudrate=baud_rate, timeout=time_out, write_timeout=0)
        if ser:
          break
      except (IOError, OSError, serial.SerialException) as e:
        # error += '0}.\n({1})'.format(portSetting, str(e))
        error += str(e) + '\n'
    if ser:
      break
    tries += 1
    time.sleep(1)

  if ser:
    # discard everything in serial buffers
    ser.flushInput()
    ser.flushOutput()
  else:
    logMessage("Error(s) while opening serial port: \n" + error)
  
  # yes this is monkey patching, but I don't see how to replace the methods on a dynamically instantiated type any other way
  if dumpSerial:
    ser.readOriginal = ser.read
    ser.writeOriginal = ser.write

    def readAndDump(size=1):
      r = ser.readOriginal(size)
      sys.stdout.write(r)
      return r

    def writeAndDump(data):
      ser.writeOriginal(data)
      sys.stderr.write(data)

    ser.read = readAndDump
    ser.write = writeAndDump

  return ser

# remove extended ascii characters from string, because they can raise UnicodeDecodeError later
def asciiToUnicode(s):
  s = s.replace(chr(0xB0), '&deg')
  return unicode(s, 'ascii', 'ignore')

