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
#. "$GITROOT/inc/asroot.inc" # (runs as 'brewpi')

# Get help and version functionality
. "$GITROOT/inc/help.inc" "$@"

############
### Loop and keep Brewpi running
############

script="$GITROOT/brewpi.py"
stdOut="$GITROOT/logs/stdout.txt"
stdErr="$GITROOT/logs/stderr.txt"
touch "$stdOut"
touch "$stdErr"
sudo chown brewpi:brewpi "$GITROOT/logs/std*.txt"
sudo chmod 660 "$GITROOT/logs/std*.txt"

while :
do
  if ! python "$script" --checkstartuponly --dontrunfile
    then python -u "$script" 1>"$stdOut" 2>>"$stdErr"
  fi
  sleep 10
done

