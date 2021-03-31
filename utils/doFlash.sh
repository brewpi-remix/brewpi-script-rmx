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

# Declare this script's constants
declare SCRIPTPATH GITROOT ARGUMENTS
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

    # Get config file read functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/config.inc" "$@"
}


############
### Process this file's help
############

# Outputs to stdout the --help usage message.
usage() {
cat << EOF

"$SCRIPTNAME" usage: $SCRIPTPATH/$THISSCRIPT

Available options:
    --silent or -s: Use default options, do not ask for user input
    --beta or -b:   Include unstable (prerelease) releases
    --shield or -d: Allow flashing a different shield
EOF
}

# Outputs to stdout the --version message.
version() {
cat << EOF

"$SCRIPTNAME" Copyright (C) 2021 Lee C. Bussy (@LBussy)

This program comes with ABSOLUTELY NO WARRANTY.

This is free software, and you are welcome to redistribute it
under certain conditions.

There is NO WARRANTY, to the extent permitted by law.
EOF
}

localhelp() {
    local arg
    for arg in "$@"
    do
        arg="${arg//-}" # Strip out all dashes
        if [[ "$arg" == "h"* ]]; then usage; exit 0
        elif [[ "$arg" == "v"* ]]; then version; exit 0
        elif [[ "$arg" == "shield"* ]] || [[ "$arg" == "d"* ]]; then shield
        elif [[ "$arg" == "s"* ]]; then silent
        elif [[ "$arg" == "b"* ]]; then beta
        fi
    done

}

silent() {
    # --silent or -s: Use default options, do not ask for user input
    ARGUMENTS="$ARGUMENTS --silent"
}

beta() {
    # --beta or -b: Include unstable (prerelease) releases
    ARGUMENTS="$ARGUMENTS --beta"
}

shield() {
    # --shield or -d: Allow flashing a different shield
    ARGUMENTS="$ARGUMENTS --shield"
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
### Flash controller
############

flash() {
    local yn branch pythonpath
    # Check to see if we should allow beta code automatically
    branch="${GITBRNCH,,}"
    if [ ! "$branch" == "master" ] && [[ ! "$ARGUMENTS" == *"beta"* ]]; then
        ARGUMENTS="$ARGUMENTS --beta"
    fi

    # Not a glamourous way to run in the venv but it's effective
    pythonpath="/home/brewpi/venv/bin/python"
    eval "$pythonpath -u $GITROOT/updateFirmware.py $ARGUMENTS"
}

############
### Main function
############

main() {
    init "$@"       # Init and call supporting libs
    const "$@"      # Get script constants
    localhelp "$@"  # Process local help
    asroot "$@"     # Make sure we are running with root privs
    banner "starting"
    flash "$@"  # Flash firmware
    banner "complete"
}

main "$@" && exit 0
