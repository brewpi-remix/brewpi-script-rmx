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
THISSCRIPT="runAfterUpdate.sh"
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
