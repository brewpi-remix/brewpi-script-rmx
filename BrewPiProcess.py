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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
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


import pprint
import os
import sys
from time import sleep
from distutils.version import LooseVersion

try:
    import psutil
    if LooseVersion(psutil.__version__) < LooseVersion("2.0"):
        print("Your version of pstuil is %s \n" \
        "BrewPi requires psutil 2.0 or higher, please upgrade your version of psutil.\n" \
        "This can best be done via pip, please run:\n" \
        "  sudo apt install python3-pip\n" \
        "  sudo pip3 install psutil --upgrade\n" % psutil.__version__, file=sys.stderr)
        sys.exit(1)

except ImportError:
    print("BrewPi requires psutil to run, please install it via pip:")
    print("  sudo pip3 install psutil --upgrade")
    sys.exit(1)

import BrewPiSocket
import BrewPiUtil as util

class BrewPiProcess:
    """
    This class represents a running BrewPi process.
    It allows other instances of BrewPi to see if there would be conflicts between them.
    It can also use the socket to send a quit signal or the pid to kill the other instance.
    """
    def __init__(self):
        self.pid = None  # PID of process
        self.cfg = None  # Config file of process, full path
        self.port = None  # Serial port the process is connected to
        self.sock = None  # BrewPiSocket object which the process is connected to

    def as_dict(self):
        """
        Returns: Member variables as a dictionary
        """
        return self.__dict__

    def quit(self):
        """
        Sends a friendly quit message to this BrewPi process over its socket to ask the process to exit.
        """
        if self.sock is not None:
            conn = self.sock.connect()
            if conn:
                conn.send('quit'.encode(encoding="cp437"))
                conn.close()  # Do not shutdown the socket, other processes are still connected to it.
                print("Quit message sent to BrewPi instance with pid %s." % self.pid)
                return True
            else:
                print("Could not connect to socket of BrewPi process in order to send a quit message.")
                print("Maybe it just started and is not listening yet.")
                self.kill()
                return False

    def kill(self):
        """
        Kills this BrewPiProcess with force, use when quit fails.
        """
        process = psutil.Process(self.pid)  # Get psutil process my pid
        try:
            process.kill()
            print("SIGKILL sent to BrewPi instance with pid %d." % self.pid)
        except psutil.AccessDenied:
            print("Cannot kill process %d, you need root permission to do that." % self.pid, file=sys.stderr)
            print("Is the process running under the same user?", file=sys.stderr)

    def conflict(self, otherProcess):
        if self.pid == otherProcess.pid:
            return 0  # This is me! I don't have a conflict with myself
        if otherProcess.cfg == self.cfg:
            print("Conflict: A BrewPi process using the same config file is already running.")
            return 1
        if otherProcess.port == self.port:
            print("Conflict: A BrewPi process using the same serial port is already running.")
            return 1
        if [otherProcess.sock.type, otherProcess.sock.file, otherProcess.sock.host, otherProcess.sock.port] == \
                [self.sock.type, self.sock.file, self.sock.host, self.sock.port]:
            print("Conflict: A BrewPi process using the same BEERSOCKET is already running.")
            return 1
        return 0

class BrewPiProcesses():
    """
    This class can get all running BrewPi instances on the system as a list of BrewPiProcess objects.
    """
    def __init__(self):
        self.list = []

    def update(self):
        """
        Update the list of BrewPi processes by receiving them from the system with psutil.
        Returns: list of BrewPiProcess objects
        """
        bpList = []
        matching = []

        # some OS's (OS X) do not allow processes to read info from other processes.
        try:
            matching = [p for p in psutil.process_iter() if any('python' in p.name() and 'brewpi.py' in s for s in p.cmdline())]
        except psutil.AccessDenied:
            pass

        for p in matching:
            bp = self.parseProcess(p)
            if bp:
                bpList.append(bp)
        self.list = bpList
        return self.list

    def parseProcess(self, process):
        """
        Converts a psutil process into a BrewPiProcess object by parsing the
        config file it has been called with.
            :Params:    A psutil.Process object
            :Returns:   A BrewPiProcess object
        """
        bp = BrewPiProcess()
        try:
            bp.pid = process._pid
            cfg = [s for s in process.cmdline() if '.cfg' in s]  # get config file argument
            # Get brewpi.py file argument so we can grab path
            bps = [s for s in process.cmdline() if 'brewpi.py' in s]
        except psutil.NoSuchProcess:
            # process no longer exists
            return None

        if cfg:
            cfg = cfg[0]  # add full path to config file
        else:
            # Get path from arguments and use that to build default path to config
            cfg = os.path.dirname(str(bps)).translate(str.maketrans('', '', r"[]'")) + '/settings/config.cfg'
        bp.cfg = util.readCfgWithDefaults(cfg)
        if bp.cfg['port'] is not None:
            bp.port = bp.cfg['port']
        bp.sock = BrewPiSocket.BrewPiSocket(bp.cfg)
        return bp

    def get(self):
        """
        Returns a non-updated list of BrewPiProcess objects
        """
        return self.list

    def me(self):
        """
        Get a BrewPiProcess object of the process this function is called from
        """
        myPid = os.getpid()
        myProcess = psutil.Process(myPid)
        return self.parseProcess(myProcess)

    def findConflicts(self, process):
        """
        Finds out if the process given as argument will conflict with other running instances of BrewPi
        Always returns a conflict if a firmware update is running

        Params:
        process: a BrewPiProcess object that will be compared with other running instances

        Returns:
        bool: True means there are conflicts, False means no conflict
        """

        # some OS's (OS X) do not allow processes to read info from other processes.
        matching = []

        try:
            matching = [p for p in psutil.process_iter() if any('python' in p.name() and 'updateFirmware.py'in s for s in p.cmdline())]
        except psutil.AccessDenied:
            pass

        if len(matching) > 0:
            return 1

        for p in self.list:
            if process.pid == p.pid:  # skip the process itself
                continue
            elif process.conflict(p):
                return 1
        return 0

    def as_dict(self):
        """
        Returns the list of BrewPiProcesses as a list of dicts, except for the process calling this function
        """
        outputList = []
        myPid = os.getpid()
        self.update()
        for p in self.list:
            if p.pid == myPid:  # do not send quit message to myself
                continue
            outputList.append(p.as_dict())
        return outputList

    def __repr__(self):
        """
        Print BrewPiProcesses as a dict when passed to a print statement
        """
        return repr(self.as_dict())

    def quitAll(self):
        """
        Ask all running BrewPi processes to exit
        """
        myPid = os.getpid()
        self.update()
        for p in self.list:
            if p.pid == myPid:  # do not send quit message to myself
                continue
            else:
                p.quit()

    def stopAll(self, dontRunFilePath):
        """
        Ask all running Brewpi processes to exit, and prevent restarting by writing
        the do_not_run file
        """
        if not os.path.exists(dontRunFilePath):
            # if do not run file does not exist, create it
            dontrunfile = open(dontRunFilePath, "w")
            dontrunfile.write("1")
            dontrunfile.close()
        myPid = os.getpid()
        self.update()
        for p in self.list:
            if p.pid == myPid:  # do not send quit message to myself
                continue
            else:
                p.quit()

    def killAll(self):
        """
        Kill all running BrewPi processes with force by sending a sigkill signal.
        """
        myPid = os.getpid()
        self.update()
        for p in self.list:
            if p.pid == myPid:  # do not commit suicide
                continue
            else:
                p.kill()

def testKillAll():
    """
    Test function that prints the process list, sends a kill signal to all processes and prints the updated list again.
    """
    allScripts = BrewPiProcesses()
    allScripts.update()
    print ("Running instances of BrewPi before killing them:")
    pprint.pprint(allScripts)
    allScripts.killAll()
    allScripts.update()
    print ("Running instances of BrewPi after killing them:")
    pprint.pprint(allScripts)

def testQuitAll():
    """
    Test function that prints the process list, sends a quit signal to all processes and prints the updated list again.
    """
    allScripts = BrewPiProcesses()
    allScripts.update()
    print ("Running instances of BrewPi before asking them to quit:")
    pprint.pprint(allScripts)
    allScripts.quitAll()
    sleep(2)
    allScripts.update()
    print ("Running instances of BrewPi after asking them to quit:")
    pprint.pprint(allScripts)
