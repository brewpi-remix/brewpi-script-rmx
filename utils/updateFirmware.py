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

from __future__ import print_function
import sys
import os
import subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..") # append parent directory to be able to import files
import autoSerial

# Firmware repository URL
firmRepo = "https://api.github.com/repos/lbussy/brewpi-firmware-rmx"

# Replacement for raw_input which works when piped through shell
def pipeInput(prompt=""):
    saved_stdin = sys.stdin
    sys.stdin = open('/dev/tty', 'r')
    result = raw_input(prompt)
    sys.stdin = saved_stdin
    return (result)

# Log to stderr.txt
def printStdErr(*objs):
    if userInput:
        print(*objs, file=sys.stderr)

# Log to stdout.txt
def printStdOut(*objs):
    if userInput:
        print(*objs, file=sys.stdout)

# Quits all running instances of BrewPi
def quitBrewPi(webPath):
    import BrewPiProcess
    allProcesses = BrewPiProcess.BrewPiProcesses()
    allProcesses.stopAll(webPath + "/do_not_run_brewpi")

def updateFromGitHub(userInput, beta, restoreSettings = True, restoreDevices = True):
    import BrewPiUtil as util
    from gitHubReleases import gitHubReleases
    import brewpiVersion
    import programController as programmer

    configFile = util.scriptPath() + '/settings/config.cfg'
    config = util.readCfgWithDefaults(configFile)

    printStdErr("\nStopping any running instances of BrewPi to check/update controller.")
    quitBrewPi(config['wwwPath'])

    hwVersion = None
    shield = None
    board = None
    family = None
    ser = None

    ### Get version number
    printStdErr("\nChecking current firmware version.")
    try:
        ser = util.setupSerial(config)
        hwVersion = brewpiVersion.getVersionFromSerial(ser)
        family = hwVersion.family
        shield = hwVersion.shield
        board = hwVersion.board

        printStdErr("\nFound the following controller:\n" + hwVersion.toExtendedString() + \
                    "\non port " + ser.name)
    except:
        if hwVersion is None:
            printStdErr("\nUnable to receive version from controller.\n"
                        "\nIs your controller unresponsive and do you wish to try restoring your")
            choice = pipeInput("firmware? [y/N]: ")
            if not any(choice == x for x in ["yes", "Yes", "YES", "yes", "y", "Y"]):
                printStdErr("\nPlease make sure your controller is connected properly and try again.")
                util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                return 0
            port, name = autoSerial.detect_port()
            if not port:
                printStdErr("\nCould not find compatible device in available serial ports.")
                util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                return 0
            if "Arduino" in name:
                family = "Arduino"
                if "Uno" in name:
                    board = 'uno'

            if board is None:
                printStdErr("\nUnable to connect to controller, perhaps it is disconnected or otherwise\n"
                            "unavailable.")
                util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                return -1
            else:
                printStdErr("\nWill try to restore the firmware on your %s." % name)
                if family == "Arduino":
                    printStdErr("\nAssuming a Rev C shield. If this is not the case, please program your Arduino\n"
                                "manually.")
                    shield = 'RevC'

    if ser:
        ser.close()    # close serial port
        ser = None

    if hwVersion:
        printStdErr("\nCurrent firmware version on controller:\n" + hwVersion.toString())
    else:
        restoreDevices = False
        restoreSettings = False

    printStdErr("\nChecking GitHub for available release.")
    releases = gitHubReleases(firmRepo)
    availableTags = releases.getTags(beta)
    stableTags = releases.getTags(False)
    compatibleTags = []
    for tag in availableTags:
        url = None
        if family == "Arduino":
            url = releases.getBinUrl(tag, [board, shield, ".hex"])
        if url is not None:
            compatibleTags.append(tag)

    if len(compatibleTags) == 0:
        printStdErr("\nNo compatible releases found for %s %s" % (family, board))
        util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
        return -1

    # default tag is latest stable tag, or latest unstable tag if no stable tag is found
    default_choice = next((i for i, t in enumerate(compatibleTags) if t in stableTags), compatibleTags[0])
    tag = compatibleTags[default_choice]

    if userInput:
        print("\nAvailable releases:")
        for i, menu_tag in enumerate(compatibleTags):
            print("[%d] %s" % (i, menu_tag))
        print ("[" + str(len(compatibleTags)) + "] Cancel firmware update")
        num_choices = len(compatibleTags)
        while 1:
            try:
                choice = pipeInput("\nEnter the number [0-%d] of the version you want to program\n"
                                   "[default = %d (%s)]: " % (num_choices, default_choice, tag))
                if choice == "":
                    break
                else:
                    selection = int(choice)
            except ValueError:
                print("Select by the number corresponding to your choice [0-%d]" % num_choices)
                continue
            if selection == num_choices:
                util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                return False # choice = skip updating
            try:
                tag = compatibleTags[selection]
            except IndexError:
                print("\nNot a valid choice. Try again.")
                continue
            break
    else:
        printStdErr("\nLatest version on GitHub: " + tag)

    if hwVersion is not None and not hwVersion.isNewer(tag):
        if hwVersion.isEqual(tag):
            printStdErr("\nYou are already running version %s." % tag)
        else:
            printStdErr("\nYour current version is newer than %s." % tag)

        if userInput:
            printStdErr("\nIf you are encountering problems, you can reprogram anyway.  Would you like")
            choice = pipeInput("to do this? [y/N]: ")
            if not any(choice == x for x in ["yes", "Yes", "YES", "yes", "y", "Y"]):
                util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                return 0
        else:
            printStdErr("\nNo update needed. Exiting.")
            exit(0)

    if hwVersion is not None and userInput:
        choice = pipeInput("\nWould you like to try to restore your settings after programming? [Y/n]: ")
        if not any(choice == x for x in ["", "yes", "Yes", "YES", "yes", "y", "Y"]):
            restoreSettings = False
        printStdErr("\nWould you like me to try to restore your configured devices after")
        choice = pipeInput("programming? [Y/n]: ")
        if not any(choice == x for x in ["", "yes", "Yes", "YES", "yes", "y", "Y"]):
            restoreDevices = False

    printStdErr("\nDownloading firmware.")
    localFileName = None
    system1 = None
    system2 = None

    if family == "Arduino":
        localFileName = releases.getBin(tag, [board, shield, ".hex"])
    else:
        printStdErr("\nError: Device family {0} not recognized".format(family))
        util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
        return -1

    if localFileName:
        printStdErr("\nLatest firmware downloaded to:\n" + localFileName)
    else:
        printStdErr("\nDownloading firmware failed.")
        util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
        return -1

    printStdErr("\nUpdating firmware.\n")
    result = programmer.programController(config, board, localFileName, {'settings': restoreSettings, 'devices': restoreDevices})
    util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
    return result

if __name__ == '__main__':
    import getopt
    # Read in command line arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "asd", ['beta', 'silent'])
    except getopt.GetoptError:
        print ("Unknown parameter, available options: \n" +
               "\t--silent\t use default options, do not ask for user input\n" +
               "\t--beta\t\t include unstable (prerelease) releases\n")
        sys.exit()

    userInput = True
    beta = False

    for o, a in opts:
        # print help message for command line options
        if o in ('-s', '--silent'):
            userInput = False
        if o in ('-b', '--beta'):
            beta = True

    result = updateFromGitHub(userInput=userInput, beta=beta)

exit(result)

