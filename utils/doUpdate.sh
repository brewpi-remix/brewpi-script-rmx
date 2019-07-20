#!/bin/bash

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

# Declare this script's constants/variables
declare SCRIPTPATH GITROOT repoArray
# Declare /inc/const.inc file constants
declare THISSCRIPT SCRIPTNAME VERSION GITROOT GITURL GITPROJ PACKAGE
# Declare /inc/asroot.inc file constants
declare HOMEPATH REALUSER
# Declare my constants/variables
declare url
url="https://raw.githubusercontent.com/brewpi-remix/brewpi-script-rmx/THISBRANCH/utils/doUpdate.sh"

############
### Init
############

init() {
    # Change to current dir (assumed to be in a repo) so we can get the git info
    pushd . &> /dev/null || exit 1
    SCRIPTPATH="$( cd "$(dirname "$0")" || exit 1 ; pwd -P )"
    cd "$SCRIPTPATH" || exit 1 # Move to where the script is
    GITROOT="$(git rev-parse --show-toplevel)" &> /dev/null
    if [ -z "$GITROOT" ]; then
        echo -e "\nERROR: Unable to find repository, did you not run as root or from" > /dev/tty
        echo -e "brewpi directory?" > /dev/tty
        popd &> /dev/null || exit 1
        exit 1
    fi
    
    # Get project constants
    # shellcheck source=/dev/null
    . "$GITROOT/inc/const.inc" "$@"
    
    # Get error handling functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/error.inc" "$@"
    
    # Get help and version functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/asroot.inc" "$@"
    
    # Get help and version functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/help.inc" "$@"
    
    # Get network test functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/nettest.inc" "$@"
    
    # Get config reading functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/config.inc" "$@"
}

############
### Create a banner
############

banner() {
    local adj
    adj="$1"
    echo -e "\n***Script $THISSCRIPT $adj.***" > /dev/tty 
}

############
### Function: whatRepo
### Argument: String representing a directory
### Return: Location of .git within that tree, or blank if there is none
############

function whatRepo() {
    local thisRepo thisReturn
    thisRepo="$1"
    if [ ! -d "$thisRepo" ]; then
        return # Not a directory
    elif ! ( cd "$thisRepo" && git rev-parse --git-dir &> /dev/null ); then
        return # Not part of a repo
    fi
    pushd . &> /dev/null || exit 1
    cd "$thisRepo" || exit 1
    thisReturn=$(git rev-parse --show-toplevel)
    if [ ! -d "$thisReturn" ]; then
        thisReturn=""
    fi
    popd &> /dev/null || exit 1
    echo "$thisReturn"
}

############
### Function: updateRepo
### Argument: String representing a directory
### Return: Success
############

# Checks for proper repo, tries to update from GitHub if it is
function updateRepo() {
    local thisRepo
    thisRepo="$1"
    # First check to see if arg is a valid repo
    gitLoc=$(whatRepo "$thisRepo")
    if [ -n "$gitLoc" ]; then
        # Store the current working directory
        pushd . &> /dev/null || exit 1
        cd "$thisRepo" || exit 1
        # See if we can get the active branch
        active_branch=$(git symbolic-ref -q HEAD)
        retval=$?
        if [ $retval -eq 0 ]; then
            active_branch=${active_branch##refs/heads/}
            # Make sure we have all remote branches
            git remote set-branches origin '*'
            git fetch
            # Check local against remote
            changes=$(git log HEAD..origin/"$active_branch" --oneline)
            if [ -z "$changes" ]; then
                # no changes
                echo -e "\n$thisRepo is up to date."
                popd &> /dev/null || exit 1
                return 0
            else
                echo -e "\n$thisRepo is not up to date, updating from GitHub:"
                git pull
                retval=$?
                if [ $retval -ne 0 ]; then
                    # Not able to make a pull, probably because of changed local files
                    echo -e "\nAn error occurred during the git pull. Please update this repo manually:"
                    echo -e "$thisRepo"
                    echo -e "\nIf this is a result of having made local changes, you can stash your local"
                    echo -e "changes and then pull the current GitHub repo with:"
                    echo -e "'cd $thisRepo; sudo git stash; sudo git pull'"
                    echo -e "\nUnder normal conditions you should never see this message.  If you have no"
                    echo -e "idea what is going on, restarting the entire process or reinstalling should"
                    echo -e "reset things to normal."
                    popd &> /dev/null || exit 1
                    return 1
                else
                    ((didUpdate++))
                fi
            fi
        else
            # No local repository found
            echo -e "\nNo local repository found (you should never see this error.)"
            popd &> /dev/null || exit 1
            return 1
        fi
        # Back to where we started
        popd &> /dev/null || exit 1
        return 0
    else
        echo -e "\nNo valid repo passed to function (repo = '$thisRepo')."
    fi
}

############
### Set up repos
############

getrepos() {
    # Get app locations based on local config
    wwwPath="$(getVal wwwPath "$GITROOT")"
    toolPath="$(whatRepo "$(eval echo "/home/$(logname 2> /dev/null)/brewpi-tools-rmx/")")"
    if [ ! -d "$toolPath" ] || [ -z "$toolPath" ]; then
        toolPath="$(whatRepo "/home/pi/brewpi-tools-rmx/")"
        if [ ! -d "$toolPath" ]; then
            echo -e "\nWARN: Unable to find a local BrewPi-Tools-RMX repository." > /dev/tty
            repoArray=("$GITROOT" "$wwwPath" )
            echo -e "\nDEBUG: In getrepos, repoArray = "$repoArray"" > /dev/tty
        fi
    else
        repoArray=("$toolPath" "$GITROOT" "$wwwPath")
        echo -e "\nDEBUG: In getrepos, repoArray = "$repoArray"" > /dev/tty
    fi
}

############
### Check for Updated doUpdate Script
############

updateme() {
    # Download current doUpdate.sh to a temp file and run that instead
    local branch
    branch=$(git branch | grep \* | cut -d ' ' -f2)
    url="${url/THISBRANCH/$branch}"
    echo -e "\nDownloading current version of this script." > /dev/tty 
    cd "$SCRIPTPATH" && { curl -s "$url" -o "tmpUpdate.sh"; cd - &> /dev/null || die; } > /dev/tty 
    chown brewpi:brewpi "$SCRIPTPATH/tmpUpdate.sh" > /dev/tty 
    chmod 770 "$SCRIPTPATH/tmpUpdate.sh" > /dev/tty 
    echo -e "\nExecuting current version of script." > /dev/tty 
    eval "bash $SCRIPTPATH/tmpUpdate.sh $*" > /dev/tty 
}

############
### Update repo URL
############

doRepoUrl() {
    local currrentUrl newUrl currentRepo
    currentRepo="$1"
    pushd . &> /dev/null || die # Store current directory
    cd "$currentRepo" || die # Move to where the script is
    currrentUrl="$(git config --get remote.origin.url)"
    newUrl="${currrentUrl/lbussy/brewpi-remix}"
    if [ ! "$newUrl" == "$currentUrl" ]; then
        # Repo has moved to a new org, update to current url
        git remote set-url origin "$newUrl"
    fi
    popd &> /dev/null || die # Move back to where we started
}

############
### Process Updates
############

process() {
    echo -e "\nDEBUG in process() repoAray = \n"$repoArray""
    local doRepo didUpdate arg
    arg="$1"
    if [[ "${arg//-}" == "q"* ]]; then quick=true; else quick=false; fi
    didUpdate=0 # Hold a counter for having to do git pulls
    pushd . &> /dev/null || die # Store current directory
    cd "$(dirname "$(readlink -e "$0")")" || die # Move to where the script is
    # Loop through repos and update as necessary
    for doRepo in "${repoArray[@]}"
    do
        echo -e "\nChecking $doRepo for necessary updates." > /dev/tty 
        doRepoUrl "$doRepo" || warn
        updateRepo "$doRepo" || warn
    done
    # If we did a pull, run apt to check packages and doCleanup.sh to clean things up
    if [ "$didUpdate" -ge 1 ]; then
        if [ ! "$quick" == "true" ]; then
            # Install/update all dependencies and clean local apt cache
            "$GITROOT/utils/doDepends.sh"
        fi
        # Cleanup *.pyc files and empty dirs, update daemons, do perms
        "$GITROOT/utils/doCleanup.sh"
    fi
    popd &> /dev/null || die # Move back to where we started
}

############
### Flash controller
############

flash() {
    local yn branch
    branch==$(git branch | grep \* | cut -d ' ' -f2)
    if [ ! "$branch" == "master" ]; then
        branch="--beta"
    else
        branch=""
    fi
    echo "" > /dev/tty 
    read -rp "Do you want to flash your controller now? [y/N]: " yn  < /dev/tty
    case "$yn" in
        [Yy]* ) eval "python -u $SCRIPTPATH/utils/updateFirmware.py $branch" ;;
        * ) ;;
    esac
}

############
### Main function
############

main() {
    init "$@" # Init and call supporting libs
    const "$@" # Get script constants
    if [ "$THISSCRIPT" == "tmpUpdate.sh" ]; then
        # Delete the temp script before we do an update
        rm "$SCRIPTPATH/tmpUpdate.sh"
        getrepos "$@" # Get list of repositories to update
        echo -e "\nDEBUG in main() repoAray = \n"$repoArray""
        process "$@" # Check and process updates
        flash # Offer to flash controller
    else
        help "$@" # Process help and version requests
        asroot # Make sure we are running with root privs
        banner "starting"
        # Get the latest doUpdate.sh script and run it instead
        updateme "$@"
        THISSCRIPT="doUpdate.sh"
        banner "complete"
    fi
}

main "$@" && exit 0
