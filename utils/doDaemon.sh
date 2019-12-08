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
### Compare source vs. target
### Arguments are $source and $target
### Return eq, lt, gt based on "version" comparison
############

function compare() {
    local src tgt
    src="$1"
    tgt="$2"
    if [ "$src" == "$tgt" ]; then
        echo "eq"
        elif [ "$(printf '%s\n' "$tgt" "$src" | sort -V | head -n1)" = "$tgt" ]; then
        echo "gt"
    else
        echo "lt";
    fi
}

############
### Remove /etc/cron.d/brewpi
############

removecron() {
    local yn
    if [ -f /etc/cron.d/brewpi ]; then
        read -rp $'\nOld-style cron jobs for BrewPi exist.  Remove? [Y/n]: ' yn < /dev/tty
        case $yn in
            [Nn]* ) return ;;
            * ) # Ok to remove;;
        esac
        echo -e "\nRemoving deprecated cron job(s)."
        rm -f /etc/cron.d/brewpi
        echo -e "\nRestarting cron:"
        /etc/init.d/cron restart
    fi
}

############
### Check existence and version of any current unit files
### Required:  daemonName - Name of Unit
### Returns:  0 to execute, 255 to skip
############

checkdaemon() {
    local daemonName unitFile src verchk
    daemonName="${1,,}"
    unitFile="/etc/systemd/system/$daemonName.service"
    if [ -f "$unitFile" ]; then
        src=$(grep "^# Created for BrewPi version" "$unitFile")
        src=${src##* }
        verchk="$(compare "$src" "$VERSION")"
        if [ "$verchk" == "lt" ]; then
            echo -e "\nUnit file for $daemonName.service exists but is an older version" > /dev/tty
            read -rp "($src vs. $VERSION). Upgrade to newest? [Y/n]: " yn < /dev/tty
            case "$yn" in
                [Nn]* )
                return 255;;
                * )
                return 0 ;; # Do overwrite
            esac
            elif [ "$verchk" == "eq" ]; then
            echo -e "\nUnit file for $daemonName.service exists and is the same version" > /dev/tty
            read -rp "($src vs. $VERSION). Overwrite anyway? [y/N]: " yn < /dev/tty
            case "$yn" in
                [Yy]* ) return 0;; # Do overwrite
                * ) return 255;;
            esac
            elif [ "$verchk" == "gt" ]; then
            echo -e "\nVersion of $daemonName.service file is newer than the version being installed."
            echo -e "Skipping."
            return 255
        fi
    else
        return 0
    fi
}

############
### Create systemd unit file
### Required:
###   scriptName - Name of script to run under Bash
###   daemonName - Name to be used for Unit
###   userName - Context under which daemon shall be run
############

createdaemon () {
    local scriptName daemonName userName unitFile
    scriptName="$GITROOT/utils/$1 -d"
    daemonName="${2,,}"
    userName="$3"
    unitFile="/etc/systemd/system/$daemonName.service"
    if [ -f "$unitFile" ]; then
        echo -e "\nStopping $daemonName daemon.";
        systemctl stop "$daemonName";
        echo -e "Disabling $daemonName daemon.";
        systemctl disable "$daemonName";
        echo -e "Removing unit file $unitFile";
        rm "$unitFile"
    fi
    echo -e "\nCreating unit file for $daemonName."
    {
        echo -e "# Created for BrewPi version $VERSION

[Unit]
Description=BrewPi Remix daemon for: $daemonName
Documentation=https://docs.brewpiremix.com/
After=multi-user.target

[Service]
Type=simple
Restart=on-failure
RestartSec=1
User=$userName
Group=$userName
ExecStart=/bin/bash $scriptName
SyslogIdentifier=$daemonName

[Install]
WantedBy=multi-user.target"                                     
    } > "$unitFile"
    chown root:root "$unitFile"
    chmod 0644 "$unitFile"
    echo -e "Reloading systemd config."
    systemctl daemon-reload
    echo -e "Enabling $daemonName daemon."
    eval "systemctl enable $daemonName"
    echo -e "Starting $daemonName daemon."
    eval "systemctl restart $daemonName"
}

############
### Call the creation of unit files
############

brewpi_unit() {
    local brewpicheck retval
    # Handle BrewPi Unit file setup
    brewpicheck=$(basename "$GITROOT")
    checkdaemon "$brewpicheck"
    retval="$?"
    if [[ "$retval" == 0 ]]; then
        createdaemon "doBrewPi.sh" "$brewpicheck" "brewpi"
        # This is necessary so that WiFi check (as root) does not create them first
        touch "$GITROOT/logs/stdout.txt" && chown brewpi:brewpi "$GITROOT/logs/stdout.txt"
        touch "$GITROOT/logs/stderr.txt" && chown brewpi:brewpi "$GITROOT/logs/stderr.txt"
    fi
}

wifi_unit() {
    local retval
    # Handle WiFi Unit file setup
    if [[ ! "$*" == *"-nowifi"* ]]; then
        checkdaemon "wificheck"
        retval="$?"
        if [[ "$retval" == 0 ]]; then createdaemon "doWiFi.sh" "wificheck" "root"; fi
    fi
}

############
### Main function
############

main() {
    init "$@" # Init and call supporting libs
    const "$@"
    asroot # Make sure we are running with root provs
    help "$@"
    banner "starting"
    removecron # Remove old brewpi cron.d entries
    brewpi_unit "$@" # Create BrewPi daemon unit file
    wifi_unit "$@" # Create WiFiCheck daemon unit file
    banner "complete"
}

main "$@" && exit 0
