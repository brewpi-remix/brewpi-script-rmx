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

# Ignore unused variables:
# shellcheck disable=SC2034
# Declare this script's constants/variables
declare SCRIPTPATH GITROOT WWWPATH TOOLPATH
# Declare /inc/const.inc file constants
declare THISSCRIPT SCRIPTNAME VERSION GITROOT GITURL GITPROJ PACKAGE
# Declare /inc/asroot.inc file constants
declare HOMEPATH REALUSER
# Declare my constants/variables

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
    echo -e "\n***Script $THISSCRIPT $adj.***"
}

############
### Set up repos
############

getrepos() {
    # Get app locations based on local config
    WWWPATH="$(getVal wwwPath "$GITROOT")"
    TOOLPATH="$(whatRepo "$(eval echo "/home/$(logname 2> /dev/null)/brewpi-tools-rmx/")")"
    if [ ! -d "$TOOLPATH" ] || [ -z "$TOOLPATH" ]; then
        TOOLPATH="$(whatRepo "/home/pi/brewpi-tools-rmx/")"
        if [ ! -d "$TOOLPATH" ]; then
            echo -e "\nWARN: Unable to find a local BrewPi-Tools-RMX repository." > /dev/tty
        fi
    fi
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
### Add some functions
############

# TODO: Finish this file

############
### Main function
############

main() {
    init "$@" # Init and call supporting libs
    const "$@"
    asroot # Make sure we are running with root provs
    help "$@"
    banner "starting"
    # Enter some stuff
    getrepos    # Get all the paths
    echo "Base name of currrent script: $THISSCRIPT"
    echo "Short name of currrent script: $SCRIPTNAME"
    echo "Currrent tagged version: $VERSION"
    echo "Location of git root for scripts: $GITROOT"
    echo "URL for origin: $GITURL"
    echo "Name of Git project: $GITPROJ"
    echo "Upper case name of project: $PACKAGE"
    echo "Current user home path: $HOMEPATH"
    echo "Real user calling script: $REALUSER"
    echo "Tool Path: $TOOLPATH"
    echo "Script Path: $GITROOT"
    echo "WWW Path: $WWWPATH"
    banner "complete"
}

main "$@" && exit 0
