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

# These scripts were originally a part of brewpi-script, scripts for
# the BrewPi project (https://github.com/BrewPi). Legacy support (for the
# very popular Arduino controller) seems to have been discontinued in
# favor of new hardware.  My original intent was to simply make these
# scripts work again since the original called for PHP5 explicity. I've
# spent so much time making them work and re-writing the logic I'm
# officialy calling it a re-mix.

# All credit for the original concept, as well as the BrewPi project as
# a whole, goes to Elco, Geo, Freeder, vanosg, routhcr, ajt2 and many
# more contributors around the world. Apologies if I have missed anyone.

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

echo -e "\n***Script $THISSCRIPT starting.***\n"

### Check if we have root privs to run
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root: sudo ./$THISSCRIPT" 1>&2
   exit 1
fi

############
### Functions to catch/display errors during setup
############
warn() {
  local fmt="$1"
  command shift 2>/dev/null
  echo "$fmt"
  echo "${@}"
  echo
  echo "*** ERROR ERROR ERROR ERROR ERROR ***"
  echo "-------------------------------------"
  echo "See above lines for error message."
  echo "Script did not complete."
  echo
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

if [ "$1" = "checkinterfaces" ]; then
  ### Make sure auto wlan0 is added to /etc/network/interfaces, otherwise it causes trouble bringing the interface back up
  grep "auto wlan0" /etc/network/interfaces > /dev/null
  if [ $? -ne 0 ]; then
    printf '%s\n' 0a "auto wlan0" . w | ed -s /etc/network/interfaces
  fi
  exit 0
fi

fails=0
gateway=$(/sbin/ip route | grep -m 1 default | awk '{ print $3 }')
### Sometimes network is so hosed, gateway IP is missing from ip route
if [ -z "$gateway" ]; then
  echo "BrewPi: wifiChecker: Cannot find gateway IP. Restarting wlan0 interface. ($(date))" 1>&2
  /sbin/ifdown wlan0
  /sbin/ifup wlan0
  exit 0
fi

while [ $fails -lt $MAX_FAILURES ]; do
### Try pinging, and if host is up, exit
  ping -c 1 -I wlan0 "$gateway" > /dev/null
  if [ $? -eq 0 ]; then
    fails=0
    echo "BrewPi: wifiChecker: Successfully pinged $gateway. ($(date))"
    break
  fi
### If that didn't work...
let fails=fails+1
  if [ $fails -lt $MAX_FAILURES ]; then
    echo "BrewPi: wifiChecker: Attempt $fails to reach $gateway failed. ($(date))" 1>&2
    sleep $INTERVAL
  fi
done

### Restart wlan0 interface
if [ $fails -ge $MAX_FAILURES ]; then
  echo "BrewPi: wifiChecker: Unable to reach router. Restarting wlan0 interface. ($(date))" 1>&2
  /sbin/ifdown wlan0
  /sbin/ifup wlan0
fi
