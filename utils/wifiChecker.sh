#!/bin/bash

# Copyright (C) 2018  Lee C. Bussy (@LBussy)

# This file is part of LBussy's BrewPi Tools Remix (BrewPi-Tools-RMX).
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
# license and credits.

############
### Init
############

# Change to current dir so we can get the got info
cd "$(dirname "$0")"
GITROOT="$(git rev-parse --show-toplevel)"

# Get project constants
. "$GITROOT/inc/const.inc"

# Get help and version functionality
. "$GITROOT/inc/help.inc"

# Get help and version functionality
. "$GITROOT/inc/asroot.inc"

# Get error handling functionality
. "$GITROOT/inc/error.inc"

# Print banner if we are not running in cron
pstree -s $$ | grep -q bash && CRON=false || CRON=true
if [ "$CRON" = false ]; then
  echo -e "\n***Script $THISSCRIPT starting.***"
fi

############
### Function: log{} to add timestamps and log level
############

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

  # name = SCRIPTNAME stripped of extension and UPPERCASE
  name="${THISSCRIPT%.*}" &&   name="${name^^}"
  # Send "INFO to stdout else (WARN and ERROR) send to stderr
  if [ "$level" = "INFO" ]; then
    echo -e "$now $name $level: $msg"
  else
    echo -e "$now $name $level: $msg" >&2
  fi
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
    #log 1 "Successfully pinged $gateway."
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
