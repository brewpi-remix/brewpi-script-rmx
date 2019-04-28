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

# Derived from Generic TCP Server for iSpindel by Stephan Schreiber
# <stephan@sschreiber.de>: (https://github.com/universam1/iSpindel)

from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from datetime import datetime
import thread
import json

# CONFIG Start

# General
DEBUG = 0           # Set to 1 for debug to console
PORT = 9501         # TCP Port to listen to
HOST = '0.0.0.0'    # Allowed IP range. 0.0.0.0 = any

# CONFIG End

ACK = chr(6)            # ASCII ACK (Acknowledge)
NAK = chr(21)           # ASCII NAK (Not Acknowledged)
BUFF = 1024             # Buffer Size (greatly exaggerated for now)


def dbgprint(s):
    print(s)


def handler(clientsock, addr):
    inpstr = ''
    success = False
    spindel_name = ''
    spindel_id = ''
    angle = 0.0
    temperature = 0.0
    battery = 0.0
    gravity = 0.0
    interval = 0
    rssi = 0
    while 1:
        data = clientsock.recv(BUFF)
        if not data:
            break  # Client closed connection
        dbgprint('{0} received: {1}'.format(repr(addr), repr(data)))
        if "close" == data.rstrip():
            clientsock.send(ACK)
            dbgprint('{0} ACK sent. Closing.'.format(repr(addr)))
            break   # Close connection
        try:
            inpstr += str(data.rstrip())
            if inpstr[0] != "{":
                clientsock.send(NAK)
                dbgprint('{0} Not JSON.'.format(repr(addr)))
                break  # Close connection
            dbgprint('{0} Input Str is now: {1}'.format(repr(addr), inpstr))
            if inpstr.find("}") != -1:
                jinput = json.loads(inpstr)
                spindel_name = jinput['name']
                dbgprint("{0} Name = {1}".format(repr(addr), spindel_name))
                spindel_id = jinput['ID']
                dbgprint("{0} ID = {1}".format(repr(addr), spindel_id))
                angle = jinput['angle']
                dbgprint("{0} Angle = {1}".format(repr(addr), angle))
                temperature = jinput['temperature']
                dbgprint("{0} Temperature = {1}".format(
                    repr(addr), temperature))
                battery = jinput['battery']
                dbgprint("{0} Battery = {1}".format(repr(addr), battery))
                try:
                    gravity = jinput['gravity']
                except:
                    # Probably using old firmware < 5.x
                    gravity = 0
                dbgprint("{0} Gravity = {1}".format(repr(addr), gravity))
                interval = jinput['interval']
                dbgprint("{0} Interval = {1}".format(repr(addr), interval))
                rssi = jinput['RSSI']
                dbgprint("{0} RSSI = {1}".format(repr(addr), rssi))
                # Looks like everything went well :)
                clientsock.send(ACK)
                success = True
                dbgprint("{0} {1} (ID:{2}): Data received ok.".format(
                    repr(addr), spindel_name, str(spindel_id)))
                break  # Close connection
        except Exception as e:
            # Something went wrong
            success = False
            dbgprint('{0} Error: {1}'.format(repr(addr), str(e)))
            clientsock.send(NAK)
            dbgprint('{0} NAK sent.'.format(repr(addr)))
            break  # Close connection server side after non-success
    clientsock.close()
    dbgprint('{0} Closed connection.'.format(repr(addr)))  # log on console


def main():
    ADDR = (HOST, PORT)
    serversock = socket(AF_INET, SOCK_STREAM)
    serversock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serversock.bind(ADDR)
    serversock.listen(5)
    while 1:
        dbgprint(
            'Waiting for connection. Listening on port: {0}'.format(str(PORT)))
        dbgprint('Use "Ctrl-C" to exit.')
        clientsock, addr = serversock.accept()
        dbgprint('Connected from: {0}'.format(str(addr)))
        thread.start_new_thread(handler, (clientsock, addr))


if __name__ == "__main__":
    main()


exit(0)
