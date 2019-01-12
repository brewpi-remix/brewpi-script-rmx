#!/bin/bash

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

############
### Init
############

# Set up some project variables
THISSCRIPT="wifiChecker.sh"
VERSION="0.4.5.0"
# These should stay the same
PACKAGE="BrewPi-Script-RMX"

# Support the standard --help and --version.
#
# func_usage outputs to stdout the --help usage message.
func_usage () {
  echo -e "$PACKAGE $THISSCRIPT version $VERSION
Usage: sudo . $THISSCRIPT"
}
# func_version outputs to stdout the --version message.
func_version () {
  echo -e "$THISSCRIPT ($PACKAGE) $VERSION
Copyright (C) 2018 Lee C. Bussy (@LBussy)
This is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published
by the Free Software Foundation, either version 3 of the License,
or (at your option) any later version.
<https://www.gnu.org/licenses/>
There is NO WARRANTY, to the extent permitted by law."
}
if test $# = 1; then
  case "$1" in
    --help | --hel | --he | --h )
      func_usage; exit 0 ;;
    --version | --versio | --versi | --vers | --ver | --ve | --v )
      func_version; exit 0 ;;
  esac
fi

# Print banner if we are not running in cron
pstree -s $$ | grep -q bash && CRON=false || CRON=true
if [ "$CRON" = false ]; then
  echo -e "\n***Script $THISSCRIPT starting.***\n"
fi

function log {
  case $1 in
    1 )
        level="INFO"  ;;
    2 )
        level="WARN"  ;;
    3 )
        level="ERROR" ;;
    * )
        level="INFO"  ;;
  esac
  msg=$2
  now=$(date '+%Y-%m-%d %H:%M:%S')
  name=$(echo ${THISSCRIPT^} | awk -F'.' '{print $1}')
  if [ "$level" = "INFO" ]; then
    echo -e "$now $name $level: $msg"
  else
    echo -e "$now $name $level: $msg" >&2
  fi
}

### Check if we have root privs to run
if [[ $EUID -ne 0 ]]; then
   log 3 "This script must be run as root: sudo ./$THISSCRIPT"
   exit 1
fi

############
### Functions to catch/display errors during runtime
############
warn() {
  local fmt="$1"
  command shift 2>/dev/null
  log 3 "$fmt"
  log 3 "${@}"
  log 3
  log 3 "*** ERROR ERROR ERROR ERROR ERROR ***"
  log 3 "-------------------------------------"
  log 3 "See above lines for error message."
  log 3 "Script did not complete."
  log 3
}

die () {
  local st="$?"
  warn "$@"
  exit "$st"
}

### User-editable settings ###
# Total number of times to try and contact the router if first packet fails
MAX_FAILURES=3
# Time to wait between failed attempts contacting the router
INTERVAL=15

# Start fails at 0
fails=0
# Get wireless lan device name
wlan=$(cat /proc/net/wireless | perl -ne '/(\w+):/ && print $1')

if [ "$1" = "--checkinterfaces" ]; then
  # Make sure auto {$wlan} is added to /etc/network/interfaces,
  # otherwise it causes trouble bringing the interface back up
  grep "auto $wlan" /etc/network/interfaces > /dev/null
  if [ $? -ne 0 ]; then
    printf '%s\n' 0a "auto $wlan" . w | ed -s /etc/network/interfaces
  fi
  exit 0
fi

# Get gateway address
gateway=$(/sbin/ip route | grep -m 1 default | awk '{ print $3 }')
### Sometimes network is so hosed, gateway IP is missing from ip route
if [ -z "$gateway" ]; then
  log 3 "$Cannot find gateway IP."
  let fails="MAX_FAILURES+1"
fi

while [ $fails -lt $MAX_FAILURES ]; do
  ### Try pinging
  ping -c 1 -I $wlan "$gateway" > /dev/null
  if [ $? -eq 0 ]; then
    log 1 "Successfully pinged $gateway."
    break
  fi
  ### If that didn't work...
  let "fails=fails+1"
  if [ $fails -lt $MAX_FAILURES ]; then
    log 2 "$fails failure(s) to reach $gateway."
    sleep $INTERVAL
  fi
done

### Restart wireless interface
if [ $fails -ge $MAX_FAILURES ]; then
  log 3 "Unable to reach router. Restarting $wlan interface."
  /sbin/ifdown $wlan
  /sbin/ifup $wlan
  exit 1
fi

exit 0
