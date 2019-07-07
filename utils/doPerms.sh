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

    # Get config file read functionality
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
### Fix permissions
############

perms() {
    local wwwPath
    # Get app locations based on local config
    wwwPath="$(getVal wwwPath "$GITROOT")"
    echo -e "\nFixing file permissions for $wwwPath."
    chown -R www-data:www-data "$wwwPath" || warn
    chown -R brewpi:www-data "$wwwPath/data" || warn
    find "$wwwPath" -type d -exec chmod 2770 {} \; || warn
    find "$wwwPath" -type f -exec chmod 640 {} \; || warn
    find "$wwwPath/data" -type f -exec chmod 660 {} \; || warn
    find "$wwwPath" -type f -name "*.json" -exec chmod 660 {} \; || warn
    echo -e "\nFixing file permissions for $GITROOT."
    chown -R brewpi:brewpi "$GITROOT" || warn
    chown -R brewpi:www-data "$GITROOT/settings" || warn
    if [ -f "$GITROOT/BEERSOCKET" ]; then
        chown -R brewpi:www-data "$GITROOT/BEERSOCKET" || warn
    fi
    find "$GITROOT" -type d -exec chmod 775 {} \; || warn
    find "$GITROOT" -type f -exec chmod 660 {} \; || warn
    find "$GITROOT" -type f -regex ".*\.\(py\|sh\)" -exec chmod 770 {} \; || warn
    find "$GITROOT/logs" -type f -iname "*.txt" -exec chmod 777 {} \; || warn
    find "$GITROOT/settings" -type f -exec chmod 664 {} \; || warn
    echo -e "\nAllowing BrewPi python access to Bluetooth interfaces."
    setcap cap_net_raw+eip $(eval readlink -f `which python`)
}

############
### Fix users and groups
############

checkuser() {
    echo -e "\nChecking user accounts."
    if ! id -u brewpi >/dev/null 2>&1; then
        useradd brewpi -m -G dialout,sudo,www-data||die
    else
        usermod -a -G dialout,sudo,www-data brewpi
    fi
    # Add current user to www-data & brewpi group
    usermod -a -G www-data,brewpi "$REALUSER"||die
}

############
### Main function
############

main() {
    init "$@" # Init and call supporting libs
    const "$@" # Get script constants
    asroot # Make sure we are running with root privs
    help "$@" # Process help and version requests
    banner "starting"
    perms # Check/set file and dir permissions
    checkuser # Check/set user attributes
    banner "complete"
}

main "$@" && exit 0
