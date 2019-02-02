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

# Get help and version functionality
. "$GITROOT/inc/help.inc"

# Get help and version functionality
. "$GITROOT/inc/asroot.inc"

# Get error handling functionality
. "$GITROOT/inc/error.inc"

# Network test
. "$GITROOT/inc/nettest.inc"

# Read configuration
. "$GITROOT/inc/config.inc"

# Go back where we were when this all started
popd &> /dev/null || exit 1

echo -e "\n***Script $THISSCRIPT starting.***"

# Make sure all dependencies are installed and updated
"$GITROOT/utils/doDepends.sh"

# Change into script directory so stuff works
pushd . &> /dev/null || exit 1
cd "$(dirname "$0")" || exit 1 # Move to where the script is

############
### Function: updateRepo
### Argument: String representing a directory
### Return: Success
############

# Checks for proper repo, tries to update from GitHub if it is
function updateRepo() {
  local thisRepo="$1"
  # First check to see if arg is a valid repo
  gitLoc=$(whatRepo "$thisRepo")
  if [ -n "$gitLoc" ]; then
    # Store the current working directory
    pushd . &> /dev/null || exit 1
    cd "$thisRepo" || exit 1
    # See if we can get the active branch
    active_branch=$(git symbolic-ref -q HEAD)
    retval=$?
    if [ $retval -eq 0 ]; then
      active_branch=${active_branch##refs/heads/}
      # Check local against remote
      git fetch
      changes=$(git log HEAD..origin/"$active_branch" --oneline)
      if [ -z "$changes" ]; then
        # no changes
        echo -e "\n$thisRepo is up to date."
          popd &> /dev/null || exit 1
        return 0
      else
        echo -e "\n$thisRepo is not up to date, updating from GitHub:"
        git pull
        retval=$?
        if [ $retval -ne 0 ]; then
          # Not able to make a pull, probably because of changed local files
          echo -e "\nAn error occurred during the git pull. Please update this repo manually:"
                echo -e "$thisRepo"
          echo -e "\nIf this is a result of having made local changes, you can stash your local"
          echo -e "changes and then pull the current GitHub repo with:"
          echo -e "'cd $thisRepo; sudo git stash; sudo git pull'"
          echo -e "\nUnder normal conditions you should never see this message.  If you have no"
          echo -e "idea what is going on, restarting the entire process or reinstalling should"
          echo -e "reset things to normal."
          popd &> /dev/null || exit 1
          return 1
        else
          ((didUpdate++))
        fi
      fi
    else
      # No local repository found
      echo -e "\nNo local repository found (you should never see this error.)"
      popd &> /dev/null || exit 1
      return 1
    fi
    # Back to where we started
    popd &> /dev/null || exit 1
    return 0
  else
    echo -e "\nNo valid repo passed to function ($thisRepo)."
  fi
}

# Get app locations based on local config
scriptPath="$(whatRepo .)"
wwwPath="$(getVal wwwPath $scriptPath)"
toolPath="$(whatRepo $(eval echo ~$(logname))/brewpi-tools-rmx)"

declare -i didUpdate=0 # Hold a counter for having to do git pulls
declare -a repoArray=("$toolPath" "$scriptPath" "$wwwPath" )

# Loop through repos and update as necessary
for doRepo in "${repoArray[@]}"; do
  echo -e "\nChecking $doRepo for necessary updates."
  updateRepo "$doRepo" || echo -e "\nError updating: $doRepo"
done
# If we did a pull, run doCleanup.sh to clean things up
if [ "$didUpdate" -ge 1 ]; then "$GITROOT/utils/doCleanup.sh"; fi

# Move back to where we started
popd &> /dev/null || exit 1

echo -e "\n***Script $THISSCRIPT complete.***"

exit 0
