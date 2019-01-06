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

from __future__ import print_function
import sys
import os
import subprocess
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..") # append parent directory to be able to import files
import autoSerial

# Firware repository URL
firmRepo = "https://api.github.com/repos/lbussy/brewpi-firmware-rmx"

# Replacement for raw_input which works when piped through shell
def pipeInput(prompt=""):
    saved_stdin = sys.stdin
    sys.stdin = open('/dev/tty', 'r')
    result = raw_input(prompt)
    sys.stdin = saved_stdin
    return (result)

# print everything in this file to stderr so it ends up in the correct log file for the web UI
def printStdOut(*objs):
    print("", *objs, file=sys.stderr)
    
# print everything in this file to stdout so it ends up in the correct log file for the web UI
def printStdOut(*objs):
    print(*objs, file=sys.stdout)

# Quits all running instances of BrewPi
def quitBrewPi(webPath):
    import BrewPiProcess
    allProcesses = BrewPiProcess.BrewPiProcesses()
    allProcesses.stopAll(webPath + "/do_not_run_brewpi")

def updateFromGitHub(userInput, beta, useDfu, restoreSettings = True, restoreDevices = True):
    import BrewPiUtil as util
    from gitHubReleases import gitHubReleases
    import brewpiVersion
    import programController as programmer

    configFile = util.scriptPath() + '/settings/config.cfg'
    config = util.readCfgWithDefaults(configFile)

    printStdOut("\nStopping any running instances of BrewPi to check/update controller.")
    quitBrewPi(config['wwwPath'])

    hwVersion = None
    shield = None
    board = None
    family = None
    ser = None

    ### Get version number
    printStdOut("\nChecking current firmware version.")
    try:
        ser = util.setupSerial(config)
        hwVersion = brewpiVersion.getVersionFromSerial(ser)
        family = hwVersion.family
        shield = hwVersion.shield
        board = hwVersion.board

        printStdOut("\nFound the following controller:\n" + hwVersion.toExtendedString() + \
                    "\non port " + ser.name)
    except:
        if hwVersion is None:
            printStdOut("\nUnable to receive version from controller.\n"
                        "\nIs your controller unresponsive and do you wish to try restoring your")
            choice = pipeInput("firmware? [y/N]: ")
            if not any(choice == x for x in ["yes", "Yes", "YES", "yes", "y", "Y"]):
                printStdOut("\nPlease make sure your controller is connected properly and try again.")
                util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                return 0
            port, name = autoSerial.detect_port()
            if not port:
                printStdOut("\nCould not find compatible device in available serial ports.")
                util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                return 0
            if "Particle" in name:
                family = "Particle"
                if "Photon" in name:
                    board = 'photon'
                elif "Core" in name:
                    board = 'core'
            elif "Arduino" in name:
                family = "Arduino"
                if "Leonardo" in name:
                    board = 'leonardo'
                elif "Uno" in name:
                    board = 'uno'

            if board is None:
                printStdOut("\nUnable to connect to controller, perhaps it is disconnected or otherwise\n"
                            "unavailable.")
                util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                return -1
            else:
                printStdOut("\nWill try to restore the firmware on your %s." % name)
                if family == "Arduino":
                    printStdOut("\nAssuming a Rev C shield. If this is not the case, please program your Arduino\n"
                                "manually.")
                    shield = 'RevC'
                else:
                    printStdOut("\nPlease put your controller in DFU mode now by holding the setup button during\n"
                                "reset, until the LED blinks yellow.")
                    printStdOut("\nPress Enter when ready.")
                    choice = pipeInput()
                    useDfu = True # use dfu mode when board is not responding to serial

    if ser:
        ser.close()    # close serial port
        ser = None

    if hwVersion:
        printStdOut("\nCurrent firmware version on controller:\n" + hwVersion.toString())
    else:
        restoreDevices = False
        restoreSettings = False

    printStdOut("\nChecking GitHub for available release.")
    releases = gitHubReleases(firmRepo)
    availableTags = releases.getTags(beta)
    stableTags = releases.getTags(False)
    compatibleTags = []
    for tag in availableTags:
        url = None
        if family == "Arduino":
            url = releases.getBinUrl(tag, [board, shield, ".hex"])
        elif family == "Spark" or family == "Particle":
            url = releases.getBinUrl(tag, [board, 'brewpi', '.bin'])
        if url is not None:
            compatibleTags.append(tag)

    if len(compatibleTags) == 0:
        printStdOut("\nNo compatible releases found for %s %s" % (family, board))
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
                choice = pipeInput("Enter the number [0-%d] of the version you want to program\n"
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
        printStdOut("\nLatest version on GitHub: " + tag)

    if hwVersion is not None and not hwVersion.isNewer(tag):
        if hwVersion.isEqual(tag):
            printStdOut("\nYou are already running version %s." % tag)
        else:
            printStdOut("\nYour current version is newer than %s." % tag)

        if userInput:
            printStdOut("\nIf you are encountering problems, you can reprogram anyway.  Would you like")
            choice = pipeInput("to do this? [y/N]: ")
            if not any(choice == x for x in ["yes", "Yes", "YES", "yes", "y", "Y"]):
                util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                return 0
        else:
            printStdOut("\nNo update needed. Exiting.")
            exit(0)

    if hwVersion is not None and userInput:
        choice = pipeInput("\nWould you like to try to restore your settings after programming? [Y/n]: ")
        if not any(choice == x for x in ["", "yes", "Yes", "YES", "yes", "y", "Y"]):
            restoreSettings = False
        printStdOut("\nWould you like me to try to restore your configured devices after")
        choice = pipeInput("programming? [Y/n]: ")
        if not any(choice == x for x in ["", "yes", "Yes", "YES", "yes", "y", "Y"]):
            restoreDevices = False

    printStdOut("\nDownloading firmware.")
    localFileName = None
    system1 = None
    system2 = None

    if family == "Arduino":
        localFileName = releases.getBin(tag, [board, shield, ".hex"])
    elif family == "Spark" or family == "Particle":
        localFileName = releases.getBin(tag, [board, 'brewpi', '.bin'])
    else:
        printStdOut("\nError: Device family {0} not recognized".format(family))
        util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
        return -1

    if board == "photon":
        if hwVersion:
            oldVersion = hwVersion.version.vstring
        else:
            oldVersion = "0.0.0"
        latestSystemTag = releases.getLatestTagForSystem(prerelease=beta, since=oldVersion)
        if latestSystemTag is not None:
            printStdOut("\nUpdated system firmware for the photon found in release {0}".format(latestSystemTag))
            system1 = releases.getBin(latestSystemTag, ['photon', 'system-part1', '.bin'])
            system2 = releases.getBin(latestSystemTag, ['photon', 'system-part2', '.bin'])
            if system1:
                printStdOut("\nDownloaded new system firmware to:\n")
                printStdOut("{0}\nand\n".format(system1))
                if system2:
                    printStdOut("{0}\n".format(system2))
                else:
                    printStdOut("\nError: system firmware part2 not found in release")
                    util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
                    return -1
        else:
            printStdOut("\nPhoton system firmware is up to date.")

    if localFileName:
        printStdOut("\nLatest firmware downloaded to:\n" + localFileName)
    else:
        printStdOut("\nDownloading firmware failed.")
        util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
        return -1

    printStdOut("\nUpdating firmware.\n")
    result = programmer.programController(config, board, localFileName, system1, system2, useDfu,
                                                                                {'settings': restoreSettings, 'devices': restoreDevices})
    util.removeDontRunFile(config['wwwPath'] + "/do_not_run_brewpi")
    return result

if __name__ == '__main__':
    import getopt
    # Read in command line arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "asd", ['beta', 'silent', 'dfu'])
    except getopt.GetoptError:
        print ("Unknown parameter, available options: \n" +
               "--silent\t use default options, do not ask for user input\n" +
               "--beta\t\t include unstable (prerelease) releases\n")
        sys.exit()

    userInput = True
    beta = False
    useDfu = False

    for o, a in opts:
        # print help message for command line options
        if o in ('-s', '--silent'):
            userInput = False
        if o in ('-b', '--beta'):
            beta = True
        if o in ('-d', '--dfu'):
            useDfu = True

    result = updateFromGitHub(userInput=userInput, beta=beta, useDfu=useDfu)

exit(result)

