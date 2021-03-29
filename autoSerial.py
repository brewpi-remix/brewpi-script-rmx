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


from serial.tools import list_ports
import BrewPiUtil
from pprint import pprint as pp

known_devices = [
    {'vid': 0x2341, 'pid': 0x0043, 'name': "Arduino Uno"},
    {'vid': 0x2341, 'pid': 0x0001, 'name': "Arduino Uno"},
    {'vid': 0x2341, 'pid': 0x0243, 'name': "Arduino Uno"},
    {'vid': 0x2a03, 'pid': 0x0043, 'name': "Arduino Uno"},
    {'vid': 0x2a03, 'pid': 0x0001, 'name': "Arduino Uno"},
    {'vid': 0x1a86, 'pid': 0x7523, 'name': "Arduino Uno"},
    {'vid': 0x2341, 'pid': 0x8036, 'name': "Arduino Leonardo"},
    {'vid': 0x2a03, 'pid': 0x8036, 'name': "Arduino Leonardo"},
    {'vid': 0x2341, 'pid': 0x0036, 'name': "Arduino Leonardo Bootloader"},
    {'vid': 0x2a03, 'pid': 0x0036, 'name': "Arduino Leonardo Bootloader"},
    {'vid': 0x2341, 'pid': 0x0010, 'name': "Arduino Mega2560"},
    {'vid': 0x2a03, 'pid': 0x0010, 'name': "Arduino Mega2560"},
    {'vid': 0x1D50, 'pid': 0x607D, 'name': "Particle Core"},
    {'vid': 0x2B04, 'pid': 0xC006, 'name': "Particle Photon"}
]

def recognized_device_name(device):
    for known in known_devices:
        if device.vid == known['vid'] and device.pid == known['pid']: # match on VID, PID
            return known['name']
    return None

def find_compatible_serial_ports(bootLoader = False, my_port = None):
    if my_port == None:
        ports = find_all_serial_ports()
    else:
        ports = find_my_serial_port(my_port)

    for p in ports:
        name = recognized_device_name(p)
        if name is not None:
            if "Bootloader" in name and not bootLoader:
                continue
            yield (p[0], name)

def find_all_serial_ports():
    """
    :return: a list of serial port info tuples
    :rtype:
    """
    all_ports = list_ports.comports(True)
    return iter(all_ports)

def find_my_serial_port(my_port):
    """
    :return: Requested serial port info tuple
    :rtype:
    """
    my_port = list_ports.grep(my_port, True)
    return iter(my_port)

def detect_port(bootLoader = False, my_port = None):
    """
    :return: first detected serial port as tuple: (port, name)
    :rtype:
    """
    if my_port == "auto":
        my_port = None

    port = (None, None)
    ports = find_compatible_serial_ports(bootLoader=bootLoader, my_port=my_port)

    try:
        port = next(ports)
    except StopIteration:
        return port
    try:
        another_port = next(ports)
        BrewPiUtil.logMessage("Warning: Multiple compatible ports.")
    except StopIteration:
        pass
    return port

def configure_serial_for_device(s, d):
    """ configures the serial connection for the given device.
    :param s the Serial instance to configure
    :param d the device (port, name, details) to configure the serial port
    """
    # for now, all devices connect at 57600 baud with defaults for parity/stop bits etc.
    s.setBaudrate(57600)

if __name__ == '__main__':
    print("All ports:")

    for p in find_all_serial_ports():
        try:
            if (p.vid):
                print("{0}, VID:{1:04x}, PID:{2:04x}".format(str(p), (p.vid), (p.pid)))
            else:
                print("{} has no PID.".format(str(p)))
        except ValueError:
            # could not convert pid and vid to hex
            print("Value Error: {0}, VID:{1}, PID:{2}".format(str(p), (p.vid), (p.pid)))
    print("Compatible ports: ")
    for p in find_compatible_serial_ports():
        print(p)
    print("Selected port: {0}".format(detect_port()))
