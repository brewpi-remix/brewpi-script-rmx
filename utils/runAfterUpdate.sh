#!/bin/bash

# Copyright (C) 2018  Lee C. Bussy (@LBussy)

# This file is part of LBussy's BrewPi Tools Remix (BrewPi-Script-RMX).
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
# along with BrewPi Tools RMX. If not, see <https://www.gnu.org/licenses/>.

# These scripts were originally a part of brewpi-tools, an installer for
# the BrewPi project (https://github.com/BrewPi). Legacy support (for the
# very popular Arduino controller) seems to have been discontinued in
# favor of new hardware.  No significant changes in the Legacy branch
# seem to have been made since the develop branch was merged on Mar 19,
# 2015 (e45ab). My original intent was to simply make this script work
# again since the original called for PHP5 explicity. I've spent so much
# time creating the bootstrapper and re-writing the logic I'm officialy
# calling it a re-mix.

# All credit for the original concept, as well as the BrewPi project as
# a whole, goes to Elco, Geo, Freeder, vanosg, routhcr, ajt2 and many
# more contributors around the world. Apologies if I have missed anyone.

############
### Init
############

# Set up some project variables
THISSCRIPT="runAfterUpdate.sh"
VERSION="0.4.5.0"
# These should stay the same
GITUSER="lbussy"
GITPROJ="brewpi-script-rmx"
PACKAGE="BrewPi-Script-RMX"

# Support the standard --help and --version.
#
# func_usage outputs to stdout the --help usage message.
func_usage () {
  echo -e "$PACKAGE $THISSCRIPT version $VERSION
Usage: sudo . $THISSCRIPT    {run as user 'pi'}"
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

# Make sure user pi is running with sudo
if [ $SUDO_USER ]; then REALUSER=$SUDO_USER; else REALUSER=$(whoami); fi
if [[ $EUID -ne 0 ]]; then UIDERROR="root";
elif [[ $REALUSER != "pi" ]]; then UIDERROR="pi"; fi
if [[ ! $UIDERROR == ""  ]]; then
  echo -e "\nThis script must be run by user 'pi' with sudo."
  echo -e "Enter the following command as one line:"
  echo -e "/home/$REALUSER/$GITPROJ/$THISSCRIPT\n" 1>&2
  exit 1
fi

# The script path will execute one dir above the location of this bash file
unset CDPATH
myPath="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
scriptPath="$myPath/.."

#!/usr/bin/env bash

# Delete old .pyc files and empty directories from script directory
printf "\nCleaning up BrewPi script directory.\n"
NUM_PYC_FILES=$( find "$scriptPath" -name "*.pyc" | wc -l | tr -d ' ' )
if [ $NUM_PYC_FILES -gt 0 ]; then
    find "$scriptPath" -name "*.pyc" -delete
    printf "Deleted $NUM_PYC_FILES old .pyc files\n"
fi

NUM_EMPTY_DIRS=$( find "$scriptPath" -type d -empty | wc -l | tr -d ' ' )
if [ $NUM_EMPTY_DIRS -gt 0 ]; then
    find "$scriptPath" -type d -empty -delete
    printf "Deleted $NUM_EMPTY_DIRS empty directories.\n"
fi

sudo bash "$myPath"/installDependencies.sh
sudo bash "$myPath"/updateCron.sh
sudo bash "$myPath"/fixPermissions.sh
