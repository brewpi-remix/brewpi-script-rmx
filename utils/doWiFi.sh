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

### User-editable settings ###
# Time (in seconds) in between tests when running in CRON or Daemon mode
declare -i LOOP=600
# Total number of times to try and contact the router if first packet fails
# After this the interface is restarted
declare -i MAX_FAILURES=3
# Time (in seconds)to wait between failed attempts contacting the router
declare -i INTERVAL=10

############
### Init
############

# Change to current dir (assumed to be in a repo) so we can get the git info
pushd . &> /dev/null || exit 1
cd "$( cd $(dirname $0) ; pwd -P )" || exit 1 # Move to where the script is
GITROOT="$(git rev-parse --show-toplevel)" &> /dev/null
if [ -z "$GITROOT" ]; then
  echo -e "\nERROR: Unable to find my repository, did you move this file or not run as root?"
  popd &> /dev/null || exit 1
  exit 1
fi

# Get project constants
. "$GITROOT/inc/const.inc"

# Get error handling functionality
. "$GITROOT/inc/error.inc"

# Get help and version functionality
. "$GITROOT/inc/asroot.inc"

# Get help and version functionality
. "$GITROOT/inc/help.inc" "$@"

############
### Function: log() to add timestamps and log level
############

log() {
  declare -i local lvl="$1" && local msg="$2"
  local now=$(date '+%Y-%m-%d %H:%M:%S')
  local name="${THISSCRIPT%.*}" && name=${name^^}
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
  logmsg="$now $name $level: $msg"
  # If we are interacive, send to tty (straight echo will break func here)
  [ "$interact" == true ] && echo -e "$logmsg" > /dev/tty && return
  # Send "INFO to stdout else (WARN and ERROR) send to stderr
  if [ "$level" = "INFO" ]; then
    echo "$logmsg" >> "$GITROOT/logs/stdout.txt"
  else
    echo "$logmsg" >> "$GITROOT/logs/stderr.txt"
  fi
}

############
### Return current wireless LAN gateway
############

func_getgateway() {
  # Get gateway address
  local gateway=$(/sbin/ip route | grep -m 1 default | awk '{ print $3 }')
  ### Sometimes network is so hosed, gateway IP is missing from route
  if [ -z "$gateway" ]; then
    # Try to restart interface and get gateway again
    func_restart
    local gateway=$(/sbin/ip route | grep -m 1 default | awk '{ print $3 }')
  fi
  echo "$gateway"
}

############
### Perform ping test
############

func_ping() {
  while [ "$fails" -lt "$MAX_FAILURES" ]; do
    [ "$fails" -gt 0 ] && sleep "$INTERVAL"
    # Try pinging
    ping -c 1 -I "$wlan" "$gateway" > /dev/null
    if [ "$?" -eq 0 ]; then
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

func_restart() {
  ### Restart wireless interface
  log 3 "Router unreachable. Restarting $wlan."
  ifconfig "$wlan" down
  ifconfig "$wlan" up
}

############
### Determine if we are running in CRON or Daemon mode
############

func_getinteract() {
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
### Print banner
############

func_banner(){
  echo -e "\n***Script $THISSCRIPT $1.***"
}

############
### Main loop
############

main() {
  interact=$(func_getinteract "$@")
  [ "$interact" == true ] && func_banner "starting"
  # If we're interactive, just run it once
  if [ "$interact" == true ]; then
    # Get wireless lan device name
    wlan=$(cat /proc/net/wireless | perl -ne '/(\w+):/ && print $1')
    if [ -z "$wlan" ]; then
      log 3 "Unable to determine wireless interface name.  Exiting."
      exit 1
    fi
    gateway=$(func_getgateway)
    if [ -z "$gateway" ]; then
      log 3 "Unable to determine gateway.  Exiting."
      exit 1
    fi
    if [ "$(func_ping "$gateway")" == true ]; then
      fails=0
    else
      func_restart
      fails=0
    fi
  # Else, loop forever
  else
    declare -i before=0
    declare -i after=0
    declare -i delay=0
    while :
    do
      # Get wireless lan device name
      wlan=$(cat /proc/net/wireless | perl -ne '/(\w+):/ && print $1')
      if [ -z "$wlan" ]; then
        log 3 "Unable to determine wireless interface name.  Exiting."
        exit 1
      fi
      gateway=$(func_getgateway)
      if [ -z "$gateway" ]; then
        log 3 "Unable to determine gateway.  Exiting."
        exit 1
      fi
      before=$(date +%s)
      if [ "$(func_ping "$gateway")" == true ]; then
        fails=0
      else
        func_restart
        fails=0
      fi
      after=$(date +%s)
      let "delay=$LOOP-($after-$before)"
      [ "$delay" -lt "1" ] && delay=10
      sleep "$delay"
    done
  fi
  [ "$interact" == true ] && func_banner "complete"
}

declare -i fails=0
main "$@"

exit 0

