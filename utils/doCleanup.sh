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

# Declare this script's constants
declare SCRIPTPATH GITROOT
# Declare /inc/const.inc file constants
declare THISSCRIPT SCRIPTNAME VERSION GITROOT GITURL GITPROJ PACKAGE
# Declare /inc/asroot.inc file constants
declare HOMEPATH REALUSER

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
        echo -e "\nERROR: Unable to find my repository, did you move this file or not run as root?"
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
}

############
### Create a banner
############

banner() {
    local adj
    adj="$1"
    echo -e "\n***Script $THISSCRIPT $adj.***"
}

############
### Cleanup compiler files and empty directories
############

cleanup() {
    local numPYC numEmptyDirs
    # Delete old .pyc files
    echo -e "\nCleaning up BrewPi script directory."
    numPYC=$( find "$GITROOT" -name "*.pyc" | wc -l | tr -d ' ' )
    if [ "$numPYC" -gt 0 ]; then
        find "$GITROOT" -name "*.pyc" -delete
        echo -e "Deleted $numPYC old .pyc files."
    fi
    #  Delete empty directories from script directory
    echo -e "\nCleaning up empty directories."
    numEmptyDirs=$( find "$GITROOT" -type d -empty | wc -l | tr -d ' ' )
    if [ "$numEmptyDirs" -gt 0 ]; then
        find "$GITROOT" -type d -empty -delete
        echo -e "Deleted $numEmptyDirs empty directories."
    fi
}

############
### Do the needful via the other scripts
############

extern() {
    sudo bash "$GITROOT/utils/doDaemon.sh" "$@"  # Set up or upgrade cron
    sudo bash "$GITROOT/utils/doPerms.sh" "$@"   # Fix file permissions
}

############
### Main function
############

main() {
    init "$@" # Init and call supporting libs
    const "$@" # Get script constants
    asroot # Make sure we are running with root privs
    help "$@" # Allow help and version response
    banner "starting"
    cleanup # Remove *.pyc files and empty directories
    extern "$@" # Call other scripts
    banner "complete"
}

main "$@" && exit 0
