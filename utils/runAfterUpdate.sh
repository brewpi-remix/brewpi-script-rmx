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

echo -e "\n***Script $THISSCRIPT starting.***"

############
### Cleanup compiler files and empty directories
############

# Delete old .pyc files
echo -e "\nCleaning up BrewPi script directory."
numPYC=$( find "$GITROOT" -name "*.pyc" | wc -l | tr -d ' ' )
if [ $numPYC -gt 0 ]; then
  find "$GITROOT" -name "*.pyc" -delete
  echo -e "Deleted $numPYC old .pyc files."
fi
#  Delete empty directories from script directory
echo -e "\nCleaning up empty directories."
numEmptyDirs=$( find "$GITROOT" -type d -empty | wc -l | tr -d ' ' )
if [ $numEmptyDirs -gt 0 ]; then
 find "$GITROOT" -type d -empty -delete
 echo -e "Deleted $numEmptyDirs empty directories."
fi

############
### Do the needfull via the other scripts
############

sudo bash "$GITROOT/utils/doDepends.sh" # Install or upgrade dependencies
sudo bash "$GITROOT/utils/doCron.sh"    # Set up or upgrade cron
sudo bash "$GITROOT/utils/doPerms.sh"   # Fix file permissions

echo -e "\n***Script $THISSCRIPT complete.***\n"
