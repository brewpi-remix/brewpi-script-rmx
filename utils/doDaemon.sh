#!/bin/bash

# Copyright (C) 2018  Lee C. Bussy (@LBussy)

# This file is part of LBussy's BrewPi Tools Remix (BrewPi-Tools-RMX).
#
# BrewPi Tools RMX is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# BrewPi Tools RMX is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BrewPi Tools RMX. If not, see <https://www.gnu.org/licenses/>.

# These scripts were originally a part of brewpi-tools, an installer for
# the BrewPi project. Legacy support (for the very popular Arduino
# controller) seems to have been discontinued in favor of new hardware.

# All credit for the original brewpi-tools goes to @elcojacobs,
# @vanosg, @routhcr, @ajt2 and I'm sure many more contributors around
# the world. My apologies if I have missed anyone; those were the names
# listed as contributors on the Legacy branch.

# See: 'original-license.md' for notes about the original project's
# license and credits.

############
### Init
############

# Change to current dir (assumed to be in a repo) so we can get the git info
pushd . &> /dev/null || exit 1
cd "$(dirname "$0")" || exit 1 # Move to where the script is
GITROOT="$(git rev-parse --show-toplevel)" &> /dev/null
if [ -z "$GITROOT" ]; then
  echo -e "\nERROR:  Unable to find my repository, did you move this file?"
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

echo -e "\n***Script $THISSCRIPT starting.***"

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
  if [ -f "$unitFile" ]; then
    echo
    read -p "Unit file for $daemonName seems to already exist. Overwrite with newest? [Y/n]: " yn < /dev/tty
    case $yn in
      [Nn]* ) return ;;
      * )
        echo -e "\nStopping $daemonName daemon.";
        systemctl stop "$daemonName";
        echo -e "Disabling $daemonName daemon.";
        systemctl disable "$daemonName";
        echo -e "Removing unit file $unitFile";
        rm "$unitFile";;
    esac
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
  enable="systemctl enable $daemonName"
  eval "$enable"
  echo -e "Starting $daemonName daemon."
  restart="systemctl restart $daemonName"
  eval "$restart"
}

brewpicheck=$(basename "$GITROOT")
func_createdaemon "doBrewPi.sh" "$brewpicheck" "brewpi"
sleep 3 # Let BrewPi touch the stdout and stderr first so perms are ok
func_createdaemon "doWiFi.sh" "wificheck" "root"

echo -e "\n***Script $THISSCRIPT complete.***"

exit 0
