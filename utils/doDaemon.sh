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

# Change to current dir (assumed to be in a repo) so we can get the git info
pushd . &> /dev/null || exit 1
SCRIPTPATH="$( cd $(dirname $0) ; pwd -P )"
cd "$SCRIPTPATH" || exit 1 # Move to where the script is
GITROOT="$(git rev-parse --show-toplevel)" &> /dev/null
if [ -z "$GITROOT" ]; then
  echo -e "\nERROR: Unable to find my repository, did you move this file or not run as root?"
  popd &> /dev/null || exit 1
  exit 1
fi

# Get project constants
. "$GITROOT/inc/const.inc" "$@"

# Get error handling functionality
. "$GITROOT/inc/error.inc" "$@"

# Get help and version functionality
. "$GITROOT/inc/asroot.inc" "$@"

# Get help and version functionality
. "$GITROOT/inc/help.inc" "$@"

echo -e "\n***Script $THISSCRIPT starting.***"

############
### Compare source and target
### Arguments are $source and $target
### Return eq, lt, gt based on "version" comparison
############

function compare() {
  local src="$1"
  local tgt="$2"
  if [ "$src" == "$tgt" ]; then echo "eq"
  elif [ "$(printf '%s\n' "$tgt" "$src" | sort -V | head -n1)" = "$tgt" ]; then echo "gt"
  else echo "lt"; fi
}

############
### Remove /etc/cron.d/brewpi
############

func_removecron() {
  if [ -f /etc/cron.d/brewpi ]; then
    read -p $'\nOld-style cron jobs for BrewPi exist.  Remove? [Y/n]: ' yn < /dev/tty
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

func_checkdaemon() {
  local daemonName="${1,,}"
  local unitFile="/etc/systemd/system/$daemonName.service"
  if [ -f "$unitFile" ]; then
    src=$(grep "^# Created for BrewPi version" "$unitFile")
    src=${src##* }
    verchk=$(compare $src $VERSION)
    if [ "$verchk" == "lt" ]; then
      echo -e "\nUnit file for $daemonName.service exists but is an older version" > /dev/tty
      read -p "($src vs. $VERSION). Upgrade to newest? [Y/n]: " yn < /dev/tty
      case "$yn" in
        [Nn]* )
          return 255;;
        * )
          return 0 ;; # Do overwrite
      esac
    elif [ "$verchk" == "eq" ]; then
      echo -e "\nUnit file for $daemonName.service exists and is the same version" > /dev/tty
      read -p "($src vs. $VERSION). Overwrite anyway? [y/N]: " yn < /dev/tty
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

func_createdaemon () {
  local scriptName="$GITROOT/utils/$1 -d"
  local daemonName="${2,,}"
  local userName="$3"
  local unitFile="/etc/systemd/system/$daemonName.service"
  if [ -f "$unitfile" ]; then
    echo -e "\nStopping $daemonName daemon.";
    systemctl stop "$daemonName";
    echo -e "Disabling $daemonName daemon.";
    systemctl disable "$daemonName";
    echo -e "Removing unit file $unitFile";
    rm "$unitFile"
  fi
  echo -e "\nCreating unit file for $daemonName."
  echo -e "# Created for BrewPi version $VERSION" > "$unitFile"
  echo -e "[Unit]" >> "$unitFile"
  echo -e "Description=BrewPi service for: $daemonName" >> "$unitFile"
  echo -e "Documentation=https://github.com/lbussy/brewpi-tools-rmx/blob/master/README.md" >> "$unitFile"
  echo -e "After=multi-user.target" >> "$unitFile"
  echo -e "\n[Service]" >> "$unitFile"
  echo -e "Type=simple" >> "$unitFile"
  echo -e "Restart=on-failure" >> "$unitFile"
  echo -e "RestartSec=1" >> "$unitFile"
  echo -e "User=$userName" >> "$unitFile"
  echo -e "Group=$userName" >> "$unitFile"
  echo -e "ExecStart=/bin/bash $scriptName" >> "$unitFile"
  echo -e "SyslogIdentifier=$daemonName" >> "$unitFile"
  echo -e "\n[Install]" >> "$unitFile"
  echo -e "WantedBy=multi-user.target" >> "$unitFile"
  chown root:root "$unitFile"
  chmod 0644 "$unitFile"
  echo -e "Reloading systemd config."
  systemctl daemon-reload
  echo -e "Enabling $daemonName daemon."
  eval "systemctl enable $daemonName"
  echo -e "Starting $daemonName daemon."
  eval "systemctl restart $daemonName"
}

# Handle BrewPi Unit file setup
brewpicheck=$(basename "$GITROOT")
func_checkdaemon "$brewpicheck"
if [[ $? == 0 ]]; then
  func_createdaemon "doBrewPi.sh" "$brewpicheck" "brewpi"
  sleep 3 # Let BrewPi touch the stdout and stderr first so perms are ok
fi

# Handle WiFi Unit file setup
func_checkdaemon "wificheck"
if [[ $? == 0 ]]; then func_createdaemon "doWiFi.sh" "wificheck" "root"; fi

echo -e "\n***Script $THISSCRIPT complete.***"

exit 0
