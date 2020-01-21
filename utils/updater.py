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
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BrewPi Script RMX. If not, see <https://www.gnu.org/licenses/>.

# These scripts were originally a part of brewpi-script, an installer for
# the BrewPi project. Legacy support (for the very popular Arduino
# controller) seems to have been discontinued in favor of new hardware.

# All credit for the original brewpi-script goes to @elcojacobs,
# @m-mcgowan, @rbrady, @steersbob, @glibersat, @Niels-R and I'm sure
# many more contributors around the world. My apologies if I have
# missed anyone; those were the names listed as contributors on the
# Legacy branch.

# See: 'original-license.md' for notes about the original project's
# license and credits

############
### Init
############

import subprocess
from time import localtime, strftime
import sys
import os
import pwd
import grp
import stat
#import urllib2
import argparse
from git import Repo
import requests
from pprint import pprint as pp

sys.path.append(os.path.dirname(os.path.abspath(__file__)) + "/..") # append parent directory to be able to import files
try:
    import BrewPiUtil
    from BrewPiUtil import addSlash, stopThisChamber, scriptPath, readCfgWithDefaults, removeDontRunFile
    import brewpiVersion
except ImportError as e:
    print("Not part of a BrewPi Git repository, error:\n{0}".format(e), file=sys.stderr)

# Configuration items
rawurl = "https://raw.githubusercontent.com/brewpi-remix/brewpi-script-rmx/THISBRANCH/utils/updater.py"
tmpscriptname = "tmpUpdate.py"  # Name of script running from GitHub
scriptname = "updater.py"       # Name of core script

####  ********************************************************************
####
####  IMPORTANT NOTE:  I don't care if you play with the code, but if
####  you do, please comment out the next lines.  Otherwise I will
####  receive a notice for every mistake you make.
####
####  ********************************************************************
# import sentry_sdk
# sentry_sdk.init("https://5644cfdc9bd24dfbaadea6bc867a8f5b@sentry.io/1803681")

def logMessage(*objs):
    print(*objs, file=sys.stdout)

def logError(*objs):
    print(*objs, file=sys.stderr)

def stopBrewPi(scriptPath, wwwPath): # Quits all running instances of BrewPi
    startAfterUpdate = None
    print("\nStopping running instances of BrewPi.")
    stopResult = stopThisChamber(scriptPath, wwwPath)
    if stopResult is True:
        # BrewPi was running and stopped.  Start after update.
        startAfterUpdate = True
    elif stopResult is False:
        # Unable to stop BrewPi
        startAfterUpdate = False
    elif stopResult is None:
        # BrewPi was not probably not running, don't start after update.
        startAfterUpdate = None
    return startAfterUpdate

def updateMeAndRun(scriptpath, args = None) -> bool: # Pull down current version and run it instead
    # Download current script from Git and run it instead
    retval = True
    global rawurl
    global scriptname
    tmpscript = os.path.join(scriptpath, tmpscriptname)
    repo = Repo(scriptpath)
    branch = repo.active_branch
    url = rawurl.replace("THISBRANCH", str(branch))
    response = requests.get(url)
    if response.status_code == 200:
        logMessage("Downloading current version of this script.")
        try:
            owner = 'brewpi'
            group = 'brewpi'
            uid = pwd.getpwnam(owner).pw_uid  # Get UID
            gid = grp.getgrnam(group).gr_gid  # Get GID
            filemode = stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH | stat.S_IROTH | stat.S_IXOTH  # 775
            file = open(tmpscript, 'w')
            file.write(response.text)
            file.close()
            os.chown(tmpscript, uid, gid)  # chown root directory
            os.chmod(tmpscript, filemode)  # chmod root directory
        except Exception as e:
            logError("Failed to write temp file, error: {0}".format(e))
            retval = False
    else:
        logError("Failed to download update script from GitHub.")
        retval = False

    if retval:
        logMessage("Executing online version of script.")
        print("DEBUG: opts = {0}".format(args))
        try:
            pout = None
            if not args:
                pout = subprocess.run([tmpscript])
            else:
                pout = subprocess.run([tmpscript, args])
            if pout.returncode > 0:
                retval = False  # Error

        except Exception as e:
            logError("Failed to execute online file, error: {0}".format(e))
            retval = False

    return retval

def getRepoName(url: str) -> str:
    last_slash_index = url.rfind("/")
    last_suffix_index = url.rfind(".git")
    if last_suffix_index < 0:
        last_suffix_index = len(url)
    if last_slash_index < 0 or last_suffix_index <= last_slash_index:
        logError("Badly formatted url: '{}'".format(url))
    return url[last_slash_index + 1:last_suffix_index]

def checkRoot(): # Determine if we are running as root or not
    if os.geteuid() != 0:
        return False
    else:
        return True

def deleteFile(file): # Delete a file
    if os.path.exists(file):
        os.remove(file)
        return True
    else:
        return False

def doArgs(scriptpath) -> bool:
    retval = False
    # Initiate the parser
    helptext = "This script will update your current chamber to the latest version,\nor allow " +\
               "you to change your current branch. Be sure to run as root or with sudo."
    parser = argparse.ArgumentParser(description = helptext)

    # Add arguments
    parser.add_argument("-v", "--version", help="show current version and exit", action="store_true")
    parser.add_argument("-a", "--ask",
                        help="ask which branch to check out",
                        action="store_true")

    # Read arguments from the command line
    args = parser.parse_args()

    # Check for --version or -V
    if args.version:
        repo = Repo(scriptpath)
        tags = repo.tags
        tag = tags[len(tags) - 1]
        url = ""
        for remote in repo.remotes:
            url = remote.url  # Assuming only one remote at this time
        reponame = getRepoName(url)
        print("Current version of '{0}': {1}.".format(reponame, tag))
        exit(0)

    # Check for --ask or -a
    if args.ask:
        retval = True # Change branches

    return retval

def refreshBranches() -> bool:
    logMessage("Refreshing branch information.")
    pout = subprocess.run([
        "git",
        "config",
        "remote.origin.fetch",
        "+refs/heads/*:refs/remotes/origin/*"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)
    if pout.returncode > 0:
        return False # Error

    pout = subprocess.run([
        "git",
        "fetch",
        "--all"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    if pout.returncode > 0:
        return False # Error

    return True # Ok

def banner(thisscript, adj):
    logMessage("\n***Script {0} {1}.***".format(thisscript, adj))

def runAfterUpdate(scriptpath): # Handle dependencies update and cleanup
    retval = True
    logMessage("Updating dependencies as needed.")
    dodepends = os.path.join(scriptpath, "utils/doDepends.sh")
    pout = subprocess.run([
        "bash",
        dodepends])
    if pout.returncode > 0:
        logError("Updating dependencies failed.")
        retval = False # Error
    return retval

def check_repo(repo): # Check most recent commit date on the repo passed to it
    updated = False
    localBranch = repo.active_branch.name
    newBranch = localBranch
    remoteRef = None

    print("You are on branch " + localBranch)

    if not localBranch in ["master", "legacy"] and not userInput:
        print("Your checked out branch is not master, our stable release branch.")
        print("It is highly recommended that you switch to the stable master branch.")
        choice = raw_input("Would you like to do that? [Y/n]: ")
        if any(choice == x for x in ["", "yes", "Yes", "YES", "yes", "y", "Y"]):
            print("Switching branch to master.")
            newBranch = "master"

    ### Get available remotes
    remote = repo.remotes[0] # default to first found remote
    if userInput and len(repo.remotes) > 1:
        print("Multiple remotes found in " + repo.working_tree_dir)
        for i, rem in enumerate(repo.remotes):
            print("[%d] %s" % (i, rem.name))
        print("[" + str(len(repo.remotes)) + "] Skip updating this repository.")
        while 1:
            try:
                choice = raw_input("From which remote do you want to update? [%s]:  " % remote)
                if choice == "":
                    print("Updating from default remote %s." % remote)
                    break
                else:
                    selection = int(choice)
            except ValueError:
                print("Use the number!")
                continue
            if selection == len(repo.remotes):
                return False # choice = skip updating
            try:
                remote = repo.remotes[selection]
            except IndexError:
                print("Not a valid selection. Try again.")
                continue
            break

    repo.git.fetch(remote.name, "--prune")

    ### Get available branches on the remote
    try:
        remoteBranches = remote.refs
    except AssertionError as e:
        print("Failed to get references from remote: " + repr(e))
        print("Aborting update of " + repo.working_tree_dir)
        return False

    if userInput:
        print("\nAvailable branches on the remote '%s' for %s: " % (remote.name, repo.working_tree_dir))

    for i, ref in enumerate(remoteBranches):
        remoteRefName = "%s" % ref
        if "/HEAD" in remoteRefName:
            remoteBranches.pop(i)  # remove HEAD from list

    for i, ref in enumerate(remoteBranches):
        remoteRefName = "%s" % ref
        remoteBranchName = remoteRefName.replace(remote.name + "/", "")
        if remoteBranchName == newBranch:
            remoteRef = ref
        if userInput:
            print("[%d] %s" % (i, remoteBranchName))

    if userInput:
        print("[" + str(len(remoteBranches)) + "] Skip updating this repository.")

        while 1:
            try:
                choice = raw_input("Enter the number of the branch you wish to update [%s]: " % localBranch)
                if choice == "":
                    print("Keeping current branch %s" % localBranch)
                    break
                else:
                    selection = int(choice)
            except ValueError:
                print("Please make a valid choice.")
                continue
            if selection == len(remoteBranches):
                return False # choice = skip updating
            try:
                remoteRef = remoteBranches[selection]
            except IndexError:
                print("Not a valid selection. Try again.")
                continue
            break

    if remoteRef is None:
        print("Could not find branch selected branch on remote. Aborting.")
        return False

    remoteBranch = ("%s" % remoteRef).replace(remote.name + "/", "")

    checkedOutDifferentBranch = False
    if localBranch != remoteBranch:
        print("The " + remoteBranch + " branch is not your currently active branch - ")
        choice = raw_input("would you like me to check it out for you now? (Required to continue) [Y/n]: ")
        if any(choice == x for x in ["", "yes", "Yes", "YES", "yes", "y", "Y"]):
            stashedForCheckout = False
            while True:
                try:
                    if remoteBranch in repo.branches:
                        print(repo.git.checkout(remoteBranch))
                    else:
                        print(repo.git.checkout(remoteRef, b=remoteBranch))
                    print("Successfully switched to " + remoteBranch)
                    checkedOutDifferentBranch = True
                    break
                except git.GitCommandError as e:
                    if not stashedForCheckout:
                        if "Your local changes to the following files would be overwritten by checkout" in str(e):
                            print("Local changes exist in your current files that need to be stashed to continue.")
                            if not stashChanges(repo):
                                return
                            print("Trying to checkout again.")
                            stashedForCheckout = True # keep track of stashing, so it is only tried once
                            continue # retry after stash
                    else:
                        print(e)
                        print("I was unable to checkout. Please try it manually from the command line and\nre-run this tool.")
                        return False
        else:
            print("Skipping this branch.")
            return False

    if remoteRef is None:
        print("Error: Could not determine which remote reference to use, aborting.")
        return False

    localDate = repo.head.commit.committed_date
    localDateString = strftime("%a, %d %b %Y %H:%M:%S", localtime(localDate))
    localSha = repo.head.commit.hexsha
    localName = repo.working_tree_dir

    remoteDate = remoteRef.commit.committed_date
    remoteDateString = strftime("%a, %d %b %Y %H:%M:%S", localtime(remoteDate))
    remoteSha = remoteRef.commit.hexsha
    remoteName = remoteRef.name
    alignLength = max(len(localName), len(remoteName))

    print("The latest commit in " + localName.ljust(alignLength) + " is " + localSha + " on " + localDateString)
    print("The latest commit on " + remoteName.ljust(alignLength) + " is " + remoteSha + " on " + remoteDateString)

    if localDate < remoteDate:
        print("*** Updates are available ****")
        choice = raw_input("Would you like to update " + localName + " from " + remoteName + " [Y/n]: ")
        if any(choice == x for x in ["", "yes", "Yes", "YES", "yes", "y", "Y"]):
            updated = update_repo(repo, remote.name, remoteBranch)
    else:
        print("Your local version of " + localName + " is up to date.")
    return updated or checkedOutDifferentBranch

def stashChanges(repo): # Stash any local repo changes
    print ("\nYou have local changes in this repository, that are prevent a successful merge.\n" + \
           "These changes can be stashed to bring your repository back to its original\n" + \
           "state so we can merge.\n" + \
           "Your changes are not lost, but saved on the stash.  You can (optionally) get\n" + \
           "them back later with 'git stash pop'.")
    choice = raw_input("Would you like to stash local changes? (Required to continue) [Y/n]: ")
    if any(choice == x for x in ["", "yes", "Yes", "YES", "yes", "y", "Y"]):
        print("Attempting to stash any changes.\n")
        try:
            repo.git.config('--get', 'user.name')
        except git.GitCommandError as e:
            print("Warning: No user name set for git, which is necessary to stash.")
            print("--> Please enter a global username for git on this system:")
            userName = raw_input()
            repo.git.config('--global', 'user.name', userName)
        try:
            repo.git.config('--get', 'user.email')
        except git.GitCommandError as e:
            print("Warning: No user e-mail address set for git, which is necessary to stash.")
            print("--> Please enter a global user e-mail address for git on this system: ")
            userEmail = raw_input()
            repo.git.config('--global', 'user.email', userEmail)
        try:
            resp = repo.git.stash()
            print("\n" + resp + "\n")
            print("Stash successful.")

            print("##################################################################")
            print("#Your local changes were in conflict with the last update of code.#")
            print("##################################################################")
            print("The conflict was:\n")
            print("-------------------------------------------------------")
            print(repo.git.stash("show", "--full-diff", "stash@{0}"))
            print("-------------------------------------------------------")
            print ("\nTo make merging possible, these changes were stashed.\n" + \
                   "To merge the changes back in, you can use 'git stash pop'.\n" + \
                   "Only do this if you really know what you are doing.  Your\n" + \
                   "changes might be incompatible with the update or could\n" + \
                   "cause a new merge conflict.")

            return True
        except git.GitCommandError as e:
            print(e)
            print("Unable to stash, don't want to overwrite your stuff, aborting this branch\nupdate.")
            return False
    else:
        print("Changes are not stashed, cannot continue without stashing. Aborting update.")
        return False

def update_repo(repo, remote, branch): # Update a branch passed to it
    stashed = False
    repo.git.fetch(remote, branch)
    try:
        print(repo.git.merge(remote + '/' + branch))
    except git.GitCommandError as e:
        print(e)
        if "Your local changes to the following files would be overwritten by merge" in str(e):
            stashed = stashChanges(repo)
            if not stashed:
                return False

        print("Trying to merge again.")
        try:
            print(repo.git.merge(remote + '/' + branch))
        except git.GitCommandError as e:
            print(e)
            print("Sorry, cannot automatically stash/discard local changes. Aborting.")
            return False
    print(branch + " updated.")
    return True

def main():
    retval = True
    if not checkRoot():
        logError("Must run as root or with sudo.")
        retval = False
    else: # Running as root/sudo
        global tmpscriptname
        thisscript = os.path.basename(__file__)
        scriptpath = addSlash(scriptPath())
        configfile = os.path.join(scriptpath, "settings/config.cfg")
        config = readCfgWithDefaults(configfile)
        wwwpath = config['wwwPath']

        # Check command line arguments
        userinput = doArgs(scriptpath)

        sys.exit(0)

        if thisscript == tmpscriptname: # Really do the update
            # Delete the temp script before we do an update
            deleteFile(os.path.join(scriptpath, thisscript))

            if userinput:
                refreshBranches() # Make sure all remote branches are present
                logMessage("DEBUG: userinput = True")
                retval = True
                return retval  # DEBUG
                # TODO:  Change branch
            else:
                logMessage("DEBUG: userinput = False")
                retval = True
                return retval  # DEBUG

            # TODO:  Loop through directories to do an update
            #getrepos "$@" # Get list of repositories to update
            #if [ -d "$toolPath" ]; then process "$toolPath"; fi # Check and process updates
            #if [ -d "$SCRIPTPATH" ]; then process "$SCRIPTPATH"; fi # Check and process updates
            #if [ -d "$wwwPath" ]; then process "$wwwPath"; fi # Check and process updates
            retval = True


        else: # Download temp file and run it
            thisscript = scriptname
            banner(thisscript, "starting")
            restart = stopBrewPi(scriptpath, wwwpath)
            if restart == False:
                logError("Unable to stop running BrewPi.")
                retval = True
            else:
                # Get the latest update script and run it instead
                arg = None
                if userinput:
                    arg = "--ask"
                if not updateMeAndRun(scriptpath, arg):
                    retval = True
                else:
                    logMessage("Refresh your browser with ctrl-F5 if open.")
                    removeDontRunFile(os.path.join(wwwpath, "do_not_run_brewpi"))
                    runAfterUpdate(scriptpath)
                    # flash # Offer to flash controller
                    banner(thisscript, "complete")
                    retval = True

    return retval

if __name__ == '__main__':
    if main():
        sys.exit(0)
    else:
        sys.exit(1)
