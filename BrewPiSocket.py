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
import socket
import os
import stat
import pwd
import grp
import BrewPiUtil as util


class BrewPiSocket:
    """
    A wrapper class for the standard socket class.
    """

    def __init__(self, cfg):
        """ Creates a BrewPi socket object and reads the settings from a BrewPi ConfigObj.
        Does not create a socket, just prepares the settings.

        Args:
        cfg: a ConfigObj object form a BrewPi config file
        """

        self.type = 'f'  # default to file socket
        self.file = None
        self.host = 'localhost'
        self.port = None
        self.sock = 0

        isWindows = sys.platform.startswith('win')
        useInternetSocket = bool(cfg.get('useInetSocket', isWindows))
        if useInternetSocket:
            self.port = int(cfg.get('socketPort', 6332))
            self.host = cfg.get('socketHost', "localhost")
            self.type = 'i'
        else:
            self.file = util.addSlash(cfg['scriptPath']) + 'BEERSOCKET'

    def __repr__(self):
        """
        This special function ensures BrewPiSocket is printed as a dict of its member variables in print statements.
        """
        return repr(self.__dict__)

    def create(self):
        """ Creates a socket socket based on the settings in the member variables and assigns it to self.sock
        This function deletes old sockets for file sockets, so do not use it to connect to a socket that is in use.
        """
        if self.type == 'i':  # Internet socket
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind((self.host, self.port))
            util.logMessage('Bound to TCP socket on port %d ' % self.port)
        else:
            if os.path.exists(self.file):
                # If socket already exists, remove it
                os.remove(self.file)
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(self.file)  # Bind BEERSOCKET
            # Set owner and permissions for socket
            fileMode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP  # 660
            owner = 'brewpi'
            group = 'www-data'
            uid = pwd.getpwnam(owner).pw_uid
            gid = grp.getgrnam(group).gr_gid
            os.chown(self.file, uid, gid)  # chown socket
            os.chmod(self.file, fileMode)  # chmod socket

    def connect(self):
        """
        Connect to the socket represented by BrewPiSocket. Returns a new connected socket object.
        This function should be called when the socket is created by a different instance of brewpi.
        """
        sock = socket.socket
        try:
            if self.type == 'i':  # Internet socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                util.logMessage(
                    'Bound to existing TCP socket on port %d ' % self.port)
                sock.connect((self.host, self.port))
            else:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                sock.connect(self.file)
        except socket.error as e:
            print(e)
            sock = False
        finally:
            return sock

    def listen(self):
        """
        Start listing on the socket, with default settings for blocking/backlog/timeout
        """
        self.sock.setblocking(1)  # set socket functions to be blocking
        self.sock.listen(10)  # Create a backlog queue for up to 10 connections
        # set to block 0.1 seconds, for instance for reading from the socket
        self.sock.settimeout(0.1)

    def read(self):
        """
        Accept a connection from the socket and reads the incoming message.

        Returns:
        conn: socket object when an incoming connection is accepted, otherwise returns False
        msgType: the type of the message received on the socket
        msg: the message body
        """
        conn = False
        msgType = ""
        msg = ""
        try:
            conn, addr = self.sock.accept()
            message = conn.recv(4096)
            if "=" in message:
                msgType, msg = message.split("=", 1)
            else:
                msgType = message
        except socket.timeout:
            conn = False
        finally:
            return conn, msgType, msg
