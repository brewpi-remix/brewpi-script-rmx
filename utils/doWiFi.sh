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

# Global constants/variables declaration
declare STDOUT STDERR SCRIPTPATH THISSCRIPT WLAN INTERACT GITROOT REBOOT LOOP
declare MAX_FAILURES INTERVAL fails
# Declare /inc/const.inc file constants
declare THISSCRIPT SCRIPTNAME VERSION GITROOT GITURL GITPROJ PACKAGE
# Declare /inc/asroot.inc file constants
declare HOMEPATH REALUSER

### User-editable settings ###
# Time (in seconds) in between tests when running in CRON or Daemon mode
LOOP=600
# Total number of times to try and contact the router if first packet fails
# After this the interface is restarted
MAX_FAILURES=3
# Time (in seconds)to wait between failed attempts contacting the router
INTERVAL=10
# Reboot on failure
REBOOT=false
# Set log names
STDOUT="stdout.txt"
STDERR="stderr.txt"
# Global variables declaration
fails=0

############
### Init
############

init() {
    # Change to current dir (assumed to be in a repo) so we can get the git info
    pushd . &> /dev/null || exit 1
    SCRIPTPATH="$( cd "$(dirname "$0")" || exit 1; pwd -P )"
    cd "$SCRIPTPATH" || exit 1 # Move to where the script is
    GITROOT="$(git rev-parse --show-toplevel)" &> /dev/null
    if [ -z "$GITROOT" ]; then
        echo -e "\nERROR: Unable to find my repository, did you move this file or not run as root?" > /dev/tty
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
    
    # Get wireless lan device name and gateway
    WLAN="$(iw dev | awk '$1=="Interface"{print $2}')"
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
### Function: log() to add timestamps and log level
############

log() {
    local -i lvl
    local msg now name level
    lvl="$1" && local msg="$2"
    now=$(date '+%Y-%m-%d %H:%M:%S')
    name="${THISSCRIPT%.*}" && name=${name^^}
    case "$lvl" in
        2 )
            level="WARN"
        ;;
        3 )
            level="ERROR"
        ;;
        * )
            level="INFO"
        ;;
    esac
    # If we are interactive, send to tty (straight echo will break func here)
    [ "$INTERACT" == true ] && echo -e "$level: $msg" > /dev/tty && return
    logmsg="$now $name $level: $msg"
    # Send "INFO to stdout else (WARN and ERROR) send to stderr
    if [ "$level" = "INFO" ]; then
        echo "$logmsg" >> "$GITROOT/logs/$STDOUT"
    else
        echo "$logmsg" >> "$GITROOT/logs/$STDERR"
    fi
}

############
### Return current wireless LAN gateway
############

getgateway() {
    local gateway
    # Get gateway address
    gateway=$(/sbin/ip route | grep -m 1 'default' | awk '{ print $3 }')
    ### Sometimes network is so hosed, gateway IP is missing from route
    if [ -z "$gateway" ]; then
        # Try to restart interface and get gateway again
        restart
        gateway=$(/sbin/ip route | grep -m 1 'default' | awk '{ print $3 }')
    fi
    echo "$gateway"
}

############
### Perform ping test
############

do_ping() {
    local retval gateway
    gateway="$1"
    while [ "$fails" -lt "$MAX_FAILURES" ]; do
        [ "$fails" -gt 0 ] && sleep "$INTERVAL"
        # Try pinging
        ping -c 3 -w 10 -I "$WLAN" "$gateway" > /dev/null
        retval="$?"
        if [ "$retval" -eq 0 ]; then
            #log 1 "Successful ping of $gateway."
            fails="$MAX_FAILURES"
            echo true
        else
            # If that didn't work...
            ((fails++))
            log 2 "$fails failure(s) to reach $gateway."
            if [ "$fails" -ge "$MAX_FAILURES" ]; then
                echo false
            fi
        fi
    done
}

############
### Restart WLAN
############

restart() {
    ### Restart wireless interface
    ip link set dev "$WLAN" down
    ip link set dev "$WLAN" up
}

############
### Determine if we are running in CRON or Daemon mode
############

getinteract() {
    # See if we are interactive (no cron or daemon (-d) mode)
    pstree -s $$ | grep -q bash && cron=false || cron=true
    [[ ! "${1//-}" == "d"* ]] && daemon=false || daemon=true
    if [[ "$daemon" == false ]] && [[ "$cron" == false ]]; then
        echo true
    else
        echo false
    fi
}

############
### Keep checking the adapter
############

check_loop() {
    local gateway
    local -i before after delay
    before=0
    after=0
    delay=0
    while :
    do
        if [ -z "$WLAN" ]; then
            if [ "$REBOOT" == true ]; then
                log 3 "Unable to determine wireless interface name.  Rebooting."
                reboot
            else
                log 3 "Unable to determine wireless interface name.  Exiting."
                exit 1
            fi
        fi
        gateway=$(getgateway)
        if [ -z "$gateway" ]; then
            exit 1
            if [ "$REBOOT" == true ]; then
                log 3 "Unable to determine gateway.  Rebooting."
                reboot
            else
                log 3 "Unable to determine gateway.  Exiting."
                exit 1
            fi
        fi
        before=$(date +%s)
        if [ "$(do_ping "$gateway")" == false ]; then
            log 3 "Gateway unreachable. Restarting $WLAN."
            restart
        fi
        fails=0
        after=$(date +%s)
        (("delay=$LOOP-($after-$before)"))
        [ "$delay" -lt "1" ] && delay=10
        sleep "$delay"
    done
}

############
### Check the adapter for one go-around
############

check_once() {
    local gateway
    if [ -z "$WLAN" ]; then
        log 3 "Unable to determine wireless interface name.  Exiting."
        exit 1
    fi
    gateway=$(getgateway)
    if [ -z "$gateway" ]; then
        log 3 "Unable to determine gateway.  Exiting."
        exit 1
    fi
    if [ "$(do_ping "$gateway")" == true ]; then
        log 1 "Ping of gateway $gateway successful."
        fails=0
    else
        log 3 "Gateway unreachable. Restarting $WLAN."
        restart
        fails=0
    fi
}

############
### Main loop
############

main() {
    init "$@"
    if [ -z "$WLAN" ]; then
        log 3 "Unable to find wireless adapter in system. Exiting." > /dev/tty
    fi
    const "$@"
    asroot # Make sure we are running with root privs
    help "$@" # Process help and version requests
    banner "starting"
    INTERACT=$(getinteract "$@")
    sudo iw dev wlan0 set power_save off # Turn off power management for WiFi
    # If we're interactive, just run it once
    if [ "$INTERACT" == true ]; then
        banner "starting"
        check_once # Check adapter for only one set of events
        banner "complete"
    else
        check_loop # Check adapter forever
    fi
}

main "$@" && exit 0
