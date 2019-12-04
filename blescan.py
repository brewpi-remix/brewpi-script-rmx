#!/usr/bin/python3

# Copyright (C) 2018, 2019 Lee C. Bussy (@LBussy)

# This file is part of LBussy's BrewPi Tilt Remix (BrewPi-Tilt-RMX).
#
# BrewPi Tilt RMX is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# BrewPi Tilt RMX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BrewPi Tilt RMX. If not, see <https://www.gnu.org/licenses/>.

# These scripts were originally a part of brewpi-brewometer, which provided
# support in BrewPi for the Tilt Electronic Hydrometer (formerly Brewometer.)

# Credit for the original brewpi-brewometer goes to @sibowler. @supercow
# then forked that work and released a more "Legacy"-capable version for
# the BrewPi Legacy users. This was an obvious jumping-off point for
# brewpi-tilt-rmx.

# As a derivative work of BrewPi, a project released under the GNU General
# Public License v3.0, this license is attached here giving precedence for
# prior work by the BrewPi team.  Both @sibowler and @supercow have agreed
# to this licensing approach.

import bluetooth._bluetooth as bluez
import struct
import sys
import os
import time

# BLE scanner based on https://github.com/adamf/BLE/blob/master/ble-scanner.py
# BLE scanner, based on
# https://code.google.com/p/pybluez/source/browse/trunk/examples/advanced/inquiry-with-rssi.py

# https://github.com/pauloborges/bluez/blob/master/tools/hcitool.c for lescan
# https://kernel.googlesource.com/pub/scm/bluetooth/bluez/+/5.6/lib/hci.h for opcodes
# https://github.com/pauloborges/bluez/blob/master/lib/hci.c#L2782 for functions
# used by lescan

# Performs a simple device inquiry, and returns a list of ble advertisement
# discovered devices

# NOTE: Python's struct.pack() will add padding bytes unless you make the
# endianness explicit. Little endian should be used for BLE. Always start a
# struct.pack() format string with "<".


LE_META_EVENT = 0x3e
LE_PUBLIC_ADDRESS = 0x00
LE_RANDOM_ADDRESS = 0x01
LE_SET_SCAN_PARAMETERS_CP_SIZE = 7
OGF_LE_CTL = 0x08
OCF_LE_SET_SCAN_PARAMETERS = 0x000B
OCF_LE_SET_SCAN_ENABLE = 0x000C
OCF_LE_CREATE_CONN = 0x000D

LE_ROLE_MASTER = 0x00
LE_ROLE_SLAVE = 0x01

# These are actually subevents of LE_META_EVENT
EVT_LE_CONN_COMPLETE = 0x01
EVT_LE_ADVERTISING_REPORT = 0x02
EVT_LE_CONN_UPDATE_COMPLETE = 0x03
EVT_LE_READ_REMOTE_USED_FEATURES_COMPLETE = 0x04

# Advertizement event types
ADV_IND = 0x00
ADV_DIRECT_IND = 0x01
ADV_SCAN_IND = 0x02
ADV_NONCONN_IND = 0x03
ADV_SCAN_RSP = 0x04


def returnnumberpacket(pkt):
    myInteger = 0
    multiple = 256
    for c in pkt:
        myInteger += struct.unpack("B", c)[0] * multiple
        multiple = 1
    return myInteger


def returnstringpacket(pkt):
    myString = ""
    for c in pkt:
        myString += "%02x" % struct.unpack("B", c)[0]
    return myString


def printpacket(pkt):
    for c in pkt:
        sys.stdout.write("%02x " % struct.unpack("B", c)[0])


def get_packed_bdaddr(bdaddr_string):
    packable_addr = []
    addr = bdaddr_string.split(':')
    addr.reverse()
    for b in addr:
        packable_addr.append(int(b, 16))
    return struct.pack("<BBBBBB", *packable_addr)


def packed_bdaddr_to_string(bdaddr_packed):
    return ':'.join('%02x' % i for i in struct.unpack("<BBBBBB", bdaddr_packed[::-1]))


def hci_enable_le_scan(sock):
    hci_toggle_le_scan(sock, 0x01)


def hci_disable_le_scan(sock):
    hci_toggle_le_scan(sock, 0x00)


def hci_toggle_le_scan(sock, enable):
    cmd_pkt = struct.pack("<BB", enable, 0x00)
    bluez.hci_send_cmd(sock, OGF_LE_CTL, OCF_LE_SET_SCAN_ENABLE, cmd_pkt)


def hci_le_set_scan_parameters(sock):
    old_filter = sock.getsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, 14)
    SCAN_RANDOM = 0x01
    OWN_TYPE = SCAN_RANDOM
    SCAN_TYPE = 0x01


def parse_events(sock, loop_count=100):
    old_filter = sock.getsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, 14)
    # Perform a device inquiry on bluetooth device #0. The inquiry should
    # last 8 * 1.28 = 10.24 seconds. Before the inquiry is performed, bluez
    # should flush its cache of previously discovered devices
    flt = bluez.hci_filter_new()
    bluez.hci_filter_all_events(flt)
    bluez.hci_filter_set_ptype(flt, bluez.HCI_EVENT_PKT)
    sock.setsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, flt)
    done = False
    results = []
    myFullList = []

    for i in range(0, loop_count):
        pkt = sock.recv(255)
        ptype, event, plen = struct.unpack("BBB", pkt[:3])

        if event == bluez.EVT_INQUIRY_RESULT_WITH_RSSI:
            i = 0
        elif event == bluez.EVT_NUM_COMP_PKTS:
            i = 0
        elif event == bluez.EVT_DISCONN_COMPLETE:
            i = 0
        elif event == LE_META_EVENT:
            subevent, = struct.unpack("B", pkt[3])
            pkt = pkt[4:]
            if subevent == EVT_LE_CONN_COMPLETE:
                pass
                # le_handle_connection_complete(pkt)
            elif subevent == EVT_LE_ADVERTISING_REPORT:
                num_reports = struct.unpack("B", pkt[0])[0]
                report_pkt_offset = 0
                for i in range(0, num_reports):
                    # Build return string
                    ts = time.time()
                    mac = packed_bdaddr_to_string(
                        pkt[report_pkt_offset + 3:report_pkt_offset + 9])
                    uuid = returnstringpacket(
                        pkt[report_pkt_offset - 22: report_pkt_offset - 6])
                    temp = "%i" % returnnumberpacket(
                        pkt[report_pkt_offset - 6: report_pkt_offset - 4])
                    grav = "%i" % returnnumberpacket(
                        pkt[report_pkt_offset - 4: report_pkt_offset - 2])
                    txp = "%i" % struct.unpack("b", pkt[report_pkt_offset - 2])
                    rssi = "%i" % struct.unpack("b", pkt[report_pkt_offset - 1])
                    Adstring = '{0},{1},{2},{3},{4},{5},{6}'.format(
                        ts, mac, uuid, temp, grav, txp, rssi)
                    myFullList.append(Adstring)
                done = True
    sock.setsockopt(bluez.SOL_HCI, bluez.HCI_FILTER, old_filter)
    return myFullList
