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

# Generic TCP Server for iSpindel (https://github.com/universam1/iSpindel)
# Version: 1.0.1
#
# Receives iSpindel data as JSON via TCP socket and writes it to a CSV file,
# Database and/or Ubidots. This is my first Python script ever, so please bear
# with me for now.
# Stephan Schreiber <stephan@sschreiber.de>, 2017-03-15

from socket import socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR
from datetime import datetime
import thread
import json

# CONFIG Start

# General
DEBUG = 0           # Set to 1 for debug to console
PORT = 9501         # TCP Port to listen to
HOST = '0.0.0.0'    # Allowed IP range. 0.0.0.0 = any

# CSV
CSV = 1                         # Set to 1 for CSV (text file) output
OUTPATH = '/home/brewpi/data/'  # Output path; filename is {name}_{id}.csv
DLM = ';'                       # CSV delimiter (normally use ; for Excel)
NEWLINE = '\r\n'                # Newline (\r\n for windows clients)
DATETIME = 1    # Leave this at 1 to include Excel timestamp in CSV
LINES = 10      # Keep XX lines of data
AVERAGE = 3     # Average the SG over the last X

# MySQL
SQL = 0                 # 1 to enable output to MySQL database.
SQL_HOST = '127.0.0.1'  # Database host name
SQL_DB = 'iSpindel'     # Database name
SQL_TABLE = 'Data'      # Table name
SQL_USER = 'iSpindel'   # DB user
SQL_PASSWORD = 'ohyeah' # DB user's password

# Ubidots Forwarding (using existing account)
UBIDOTS = 0  # 1 to enable output to ubidots; enter token below
UBI_TOKEN = 'xxxxxxxxxxxxxxxxxxxxxxxxxxxxxx'
UBI_URL = 'http://things.ubidots.com/api/v1.6/devices/'

# ADVANCED
# Enable dynamic columns (configure pre-defined in lines 128-129)
ENABLE_ADDCOLS = 0

# CONFIG End

ACK = chr(6)            # ASCII ACK (Acknowledge)
NAK = chr(21)           # ASCII NAK (Not Acknowledged)
BUFF = 1024             # Buffer Size (greatly exaggerated for now)


def dbgprint(s):
    if DEBUG == 1:
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

    if success:
        # We have the complete iSpindel data now, so let's make it available
        if CSV == 1:
            dbgprint('{0} Writing CSV.'.format(repr(addr)))
            try:
                filename = '{0}{1}_{2}.csv'.format(
                    OUTPATH, spindel_name, str(spindel_id))
                with open(filename, 'a') as csv_file:
                    # This would sort output. But we do not want that.
                    # import csv
                    # csvw = csv.writer(csv_file, delimiter=DLM)
                    # csvw.writerow(jinput.values())
                    outstr = '{1}{0}{2}{0}{3}{0}{4}{0}{5}{0}{6}'.format(
                        DLM, spindel_name, spindel_id, str(angle), str(temperature), str(battery), str(gravity))
                    if DATETIME == 1:
                        cdt = datetime.now()
                        outstr += '{0}{1}'.format(DLM, cdt.strftime('%x %X'))
                    dbgprint('{0} Writing to CSV: "{1}"'.format(
                        repr(addr), outstr))
                    outstr += NEWLINE
                    csv_file.writelines(outstr)
                    dbgprint('{0} CSV data written.'.format(repr(addr)))
            except Exception as e:
                dbgprint('{0} CSV Error: {1}'.format(repr(addr), str(e)))

        if SQL == 1:
            try:
                import mysql.connector
                dbgprint('{0} Writing to database'.format(repr(addr)))
                # Standard field definitions:
                fieldlist = ['timestamp', 'name', 'ID', 'angle',
                             'temperature', 'battery', 'gravity']
                valuelist = [datetime.now(), spindel_name, spindel_id,
                             angle, temperature, battery, gravity]
                # Establish database connection
                cnx = mysql.connector.connect(
                    user=SQL_USER, password=SQL_PASSWORD, host=SQL_HOST, database=SQL_DB)
                cur = cnx.cursor()
                # Add extra columns dynamically?
                # This is kinda ugly; if new columns should persist, make
                # sure you add them to the lists above. For testing purposes
                # it allows to introduce new values of raw data without
                # having to fiddle around.
                if ENABLE_ADDCOLS == 1:
                    jinput = json.loads(inpstr)
                    for key in jinput:
                        if not key in fieldlist:
                            dbgprint('{0} Key \'{1}\' is not yet listed, adding it now.'.format(
                                repr(addr), key))
                            fieldlist.append(key)
                            value = jinput[key]
                            valuelist.append(value)
                            # Crude way to check if it's numeric or a string
                            # (we'll handle strings and doubles only)
                            vartype = 'double'
                            try:
                                dummy = float(value)
                            except:
                                vartype = 'varchar(64)'
                            # Check if the field exists, if not, add it
                            try:
                                dbgprint('{0} Key \'{1}\': Adding to database.'.format(
                                    repr(addr), key))
                                sql = 'ALTER TABLE {0} ADD {1} {2}'.format(
                                    SQL_TABLE, key, vartype)
                                cur.execute(sql)
                            except Exception as e:
                                if e[0] == 1060:
                                    dbgprint('{0} Key \'{1}\': exists. Consider adding it to defaults list if you want to keep it.'.format(
                                        repr(addr), key))
                                else:
                                    dbgprint('{0} Key \'{1}\': Error: {2}'.format(
                                        repr(addr), key, str(e)))
                # Gather the data now and send it to the database
                fieldstr = ', '.join(fieldlist)
                valuestr = ', '.join(['%s' for x in valuelist])
                add_sql = 'INSERT INTO Data ({0}) VALUES ({1})'.format(
                    fieldstr, valuestr)
                cur.execute(add_sql, valuelist)
                cnx.commit()
                cur.close()
                cnx.close()
                dbgprint('{0} DB data written.'.format(repr(addr)))
            except Exception as e:
                dbgprint('{0} Database Error: {1}'.format(repr(addr), str(e)))

        if UBIDOTS == 1:
            try:
                dbgprint('{0} Sending to ubidots'.format(repr(addr)))
                import urllib2
                outdata = {
                    'tilt': angle,
                    'temperature': temperature,
                    'battery': battery,
                    'gravity': gravity
                }
                out = json.dumps(outdata)
                dbgprint('{0} Sending: {1}'.format(repr(addr), out))
                url = '{0}{1}?token={2}'.format(
                    UBI_URL, spindel_name, UBI_TOKEN)
                req = urllib2.Request(url)
                req.add_header('Content-Type', 'application/json')
                req.add_header('User-Agent', spindel_name)
                response = urllib2.urlopen(req, out)
                dbgprint('{0} Received: {1}'.format(repr(addr), str(response)))
            except Exception as e:
                dbgprint('{0} Ubidots Error: {1}'.format(repr(addr), str(e)))


def main():
    ADDR = (HOST, PORT)
    serversock = socket(AF_INET, SOCK_STREAM)
    serversock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
    serversock.bind(ADDR)
    serversock.listen(5)
    while 1:
        dbgprint(
            'Waiting for connection. Listening on port: {0}'.format(str(PORT)))
        clientsock, addr = serversock.accept()
        dbgprint('Connected from: {0}'.format(str(addr)))
        thread.start_new_thread(handler, (clientsock, addr))


if __name__ == "__main__":
    main()


exit(0)
