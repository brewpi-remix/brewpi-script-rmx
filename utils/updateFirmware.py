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
import psutil
sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..") # append parent directory to be able to import files
import autoSerial
from BrewPiUtil import createDontRunFile, removeDontRunFile, stopThisChamber, readCfgWithDefaults, addSlash, setupSerial, scriptPath
from gitHubReleases import gitHubReleases
import brewpiVersion
import programController as programmer


# Globals
firmRepo = "https://api.github.com/repos/lbussy/brewpi-firmware-rmx"
userInput = True

# Replacement for raw_input which works when piped through shell
def pipeInput(prompt=""):
    saved_stdin = sys.stdin
    sys.stdin = open('/dev/tty', 'r')
    result = raw_input(prompt)
    sys.stdin = saved_stdin
    return (result)

# Return "a" or "an" depending on first letter of argument (yes this is
# a grammar function)
def article(word):
    if not word:
        return "a" # in case word is not valid
    firstLetter = word[0]
    if firstLetter.lower() in 'aeiou':
        return "an"
    else:
        return "a"

# Log to stderr.txt
def printStdErr(*objs):
    if userInput:
        print(*objs, file=sys.stderr)

# Log to stdout.txt
def printStdOut(*objs):
    if userInput:
        print(*objs, file=sys.stdout)

# Quits all running instances of BrewPi
# def quitBrewPi(webPath):
#     import BrewPiProcess
#     allProcesses = BrewPiProcess.BrewPiProcesses()
#     allProcesses.stopAll(webPath + "/do_not_run_brewpi")

# See if the version we got back from the board is valid
def goodVersion(versn):
    lst = versn.toString().split(".")
    count = len(lst)
    if count == 3:
        M,m,p = lst
        if M.isdigit() and m.isdigit() and p.isdigit():
            return True
    return False


def updateFromGitHub(beta = False, doShield = False, usePinput = True, restoreSettings = True, restoreDevices = True, ):
    configFile = '{0}settings/config.cfg'.format(addSlash(scriptPath()))
    config = readCfgWithDefaults(configFile)
    
    stopResult = stopThisChamber(config['scriptPath'], config['wwwPath'])
    if stopResult is True:
        # BrewPi was running and stopped.  Start after update.
        startAfterUpdate = True
        pass
    elif stopResult is False:
        # Unable to stop BrewPi
        return False
    elif stopResult is None:
        # BrewPi was not probably not running, don't start after update.
        startAfterUpdate = False
        pass

    hwVersion = None
    shield = None
    board = None
    family = None
    ser = None

    ### Get version number
    printStdErr("\nChecking current firmware version.")
    try:
        ser = setupSerial(config, 57600, 1.0, 1.0, True)
        hwVersion = brewpiVersion.getVersionFromSerial(ser)
        family = hwVersion.family
        shield = hwVersion.shield
        board = hwVersion.board

        printStdErr("\nFound the following controller:\n" + hwVersion.toExtendedString() + \
                    "\non port " + ser.name + ".")
    except:
        if hwVersion is None:
            choice = pipeInput("\nUnable to receive version from controller. If your controller is" +
                               "\nunresponsive, or if this is a new controller you can choose to proceed" + 
                               "\nand flash the firmware. Would you like to do this? [y/N]: ").lower()
            if not choice.startswith('y'):
                printStdErr("\nPlease make sure your controller is connected properly and try again.")
                if startAfterUpdate:
                    # Only restart if it was running when we started
                    removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
                else:
                    printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                        '\nmay have to investigate.')
                return True

            # Be sure to check the configured port
            if config['port'] == 'auto':
                printStdErr("\nUsing auto port configuration.")
                port, name = autoSerial.detect_port()
            else:
                printStdErr("\nUsing port {0} according to configuration settings.".format(config['port']))
                port, name = autoSerial.detect_port(my_port = config['port'])

            if not port:
                printStdErr("\nCould not find compatible device in available serial ports.")
                if startAfterUpdate:
                    # Only restart if it was running when we started
                    removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
                else:
                    printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                        '\nmay have to investigate.')
                return False
            if "Arduino" in name:
                family = "Arduino"
                if "Uno" in name:
                    board = 'uno'

            if board is None:
                printStdErr("\nUnable to connect to an Arduino Uno, perhaps it is disconnected or otherwise"
                            "\nunavailable.")
                if startAfterUpdate:
                    # Only restart if it was running when we started
                    removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
                else:
                    printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                        '\nmay have to investigate.')
                return False
            else:
                printStdErr("\nProcessing a firmware flash for your blank %s." % name)

    if ser:
        ser.close() # Close serial port so we can flash it
        ser = None

    if hwVersion:
        # Make sure we didn't get half a string (happens when the BrewPi process
        # does not shut down or restarts)
        if goodVersion(hwVersion):
            printStdErr("\nCurrent firmware version on controller: " + hwVersion.toString())
        else:
            printStdErr("\nInvalid version returned from controller. Make sure you are running as root" + 
                    "\nand the script is able to shut down correctly.")
            if startAfterUpdate:
                # Only restart if it was running when we started
                removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
            else:
                    printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                        '\nmay have to investigate.')
            return False
    else:
        restoreDevices = False
        restoreSettings = False

    printStdErr("\nChecking GitHub for available release(s).")
    releases = gitHubReleases(firmRepo)
    availableTags = releases.getTags(beta)
    stableTags = releases.getTags(False)
    compatibleTags = []

    # Allow reflashing the shield type
    if doShield is True:
        shield = None

    # Allow selecting the desired shield type
    if shield is None:
        shields = releases.getShields()

        printStdErr("\nPlease select the shield type you would like to use. Available shields:")
        for i in range(len(shields)):
            printStdErr("[{0}] {1}".format(i, shields[i]))

        # Give chance to exit
        printStdErr("[{0}] {1}".format(i + 1, "Cancel firmware update"))

        while 1:
            try:
                choice = pipeInput("\nEnter the number [0-{0}] of the shield you would like to use.\n"
                                   "[default = {0} ({1})]: ".format(len(shields) - 1, shields[len(shields) - 1]))
                if choice == "":
                    selection = len(shields) - 1
                elif int(choice) == len(shields):
                    printStdErr("\nExiting without making any changes.")
                    if startAfterUpdate:
                        # Only restart if it was running when we started
                        removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
                    else:
                        printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                            '\nmay have to investigate.')
                    return True
                else:
                    selection = int(choice)

            except ValueError:
                printStdErr("\nNot a valid choice. Try again.")
                continue

            try:
                shield = shields[selection]
                printStdErr("\nReflashing controller with {0} shield.".format(shield))
            except IndexError:
                printStdErr("\nNot a valid choice. Try again.")
                continue
            break

    for tag in availableTags:
        url = None
        if family == "Arduino":
            url = releases.getBinUrl(tag, [board, shield, ".hex"])
        if url is not None:
            compatibleTags.append(tag)

    if len(compatibleTags) == 0:
        printStdErr("\nNo compatible releases found for {0} {1} {2} with {3} {4} shield.".format(article(family), family.capitalize(), board.capitalize(), article(shield), str(shield).upper()))
        if startAfterUpdate:
            # Only restart if it was running when we started
            removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
        else:
            printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                '\nmay have to investigate.')
        return False

    # Default tag is latest stable tag, or latest unstable tag if no stable tag is found
    for i, t in enumerate(compatibleTags):
        if t in stableTags:
            default_choice = i
            break
        elif t in compatibleTags:
            default_choice = i
            break

    tag = compatibleTags[default_choice]

    if userInput:
        printStdErr("\nAvailable releases:")
        for i, menu_tag in enumerate(compatibleTags):
            printStdErr("[%d] %s" % (i, menu_tag))
        printStdErr("[" + str(len(compatibleTags)) + "] Cancel firmware update")
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
                printStdErr("Select by the number corresponding to your choice [0-%d]" % num_choices)
                continue
            if selection == num_choices:
                if startAfterUpdate:
                    # Only restart if it was running when we started
                    removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
                else:
                    printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                        '\nmay have to investigate.')
                return True # choice = skip updating
            try:
                tag = compatibleTags[selection]
            except IndexError:
                printStdErr("\nNot a valid choice. Try again.")
                continue
            break
    else:
        printStdErr("\nLatest version on GitHub: " + tag)

    if doShield is False:
        if hwVersion is not None and not hwVersion.isNewer(tag):
            if hwVersion.isEqual(tag):
                printStdErr("\nYou are already running version %s." % tag)
            else:
                printStdErr("\nYour current version is newer than %s." % tag)

            if userInput:
                choice = pipeInput("\nIf you are encountering problems, you can reprogram anyway.  Would you like" + 
                                "\nto do this? [y/N]: ").lower()
                if not choice.startswith('y'):
                    if startAfterUpdate:
                        # Only restart if it was running when we started
                        removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
                    return True
            else:
                printStdErr("\nNo update needed. Exiting.")
                if startAfterUpdate:
                    # Only restart if it was running when we started
                    removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
                else:
                    printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                        '\nmay have to investigate.')
                return True

    if hwVersion is not None and userInput:
        choice = pipeInput("\nWould you like to try to restore your settings after programming? [Y/n]: ").lower()
        if not choice.startswith('y'):
            restoreSettings = False
        choice = pipeInput("\nWould you like me to try to restore your configured devices after" + 
                           "\nprogramming? [Y/n]: ").lower()
        if not choice.startswith('y'):
            restoreDevices = False

    localFileName = None
    system1 = None
    system2 = None

    if family == "Arduino":
        localFileName = releases.getBin(tag, [board, shield, ".hex"])
    else:
        printStdErr("\nError: Device family {0} not recognized".format(family))
        if startAfterUpdate:
            # Only restart if it was running when we started
            removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
        else:
            printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                '\nmay have to investigate.')
        return False

    if localFileName:
        printStdErr("\nLatest firmware downloaded to:\n" + localFileName)
    else:
        printStdErr("\nDownloading firmware failed.")
        if startAfterUpdate:
            # Only restart if it was running when we started
            removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
        else:
            printStdErr('\nBrewPi was not running when we started. If it does not start after this you',
                '\nmay have to investigate.')
        return False

    printStdErr("\nUpdating firmware.")
    result = programmer.programController(config, board, localFileName, {'settings': restoreSettings, 'devices': restoreDevices})
    if startAfterUpdate:
        # Only restart if it was running when we started
        removeDontRunFile('{0}do_not_run_brewpi'.format(addSlash(config['wwwPath'])))
    else:
        printStdErr('\nBrewPi was not running when we started, leaving do_not_run_brewpi in\n{0}.'.format(addSlash(config['wwwPath'])))
    return result


def main():
    import getopt
    # Read in command line arguments
    try:
        opts, args = getopt.getopt(sys.argv[1:], "sbh", ['beta', 'silent', 'shield'])
    except getopt.GetoptError:
        # print help message for command line options
        print ("Unknown parameter, available options: \n" +
               "\t--silent or -s\t Use default options, do not ask for user input\n" +
               "\t--beta or -b\t Include unstable (prerelease) releases\n" + 
               "\t--shield or -h\t Allow flashing a different shield\n")
        return True

    beta = False
    doShield = False
    userInput = True

    for o, a in opts:
        if o in ('-s', '--silent'):
            userInput = False
        if o in ('-b', '--beta'):
            beta = True
        if o in ('-h', '--shield'):
            doShield = True

    result = updateFromGitHub(beta, doShield, userInput)
    return result


if __name__ == '__main__':
    result = main()
    exit(result)
