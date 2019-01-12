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

# Change to current dir so we can get the git info
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

# Network test
. "$GITROOT/inc/error.inc"

echo -e "\n***Script $THISSCRIPT starting.***"

# Make sure git is installed
"$GITROOT/utils/doDepends.sh"

# Change directory to where the repo is
pushd "$PWD" &> /dev/null
cd "$GITROOT"

# See if we can get the active branch
active_branch=$(git symbolic-ref -q HEAD)
if [ $? -eq 0 ]; then
  active_branch=${active_branch##refs/heads/}

  # Check local against remote
  git fetch
  changes=$(git log HEAD..origin/"$active_branch" --oneline)
  if [ -z "$changes" ]; then
    # no changes
    echo "$myPath is up to date."
    exit 0
  else
    echo "$myPath is not up to date, updating from GitHub."
    git pull
    if [ $? -ne 0 ]; then
      # Not able to make a pull because of changed local files
      echo -e "\nAn error occurred during git pull. Please update $myPath manually.  You can"
      echo -e "stash your local changes and then pull with:"
      echo -e "'cd $myPath; sudo git stash; sudo git pull'"
      echo -e "\nUnder normal conditions (like, so long as you are not making script changes)"
      echo -e "you should never see this message.  If you have no idea what is going on,"
      echo -e "restarting the entire process or reinstalling should reset things to normal."
      popd
      exit 1
    fi
  fi
else
  # No local repository found
  echo -e "\nNo local repository found."
  popd
  exit 1
fi

# Back to where we started
popd

