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
# Go back where we were when this all started
popd &> /dev/null || exit 1

# Get project constants
. "$GITROOT/inc/const.inc"

# Get error handling functionality
. "$GITROOT/inc/error.inc"

# Get help and version functionality
. "$GITROOT/inc/asroot.inc"

# Get help and version functionality
. "$GITROOT/inc/help.inc" "$@"

# Network test
. "$GITROOT/inc/nettest.inc"

# Read configuration
. "$GITROOT/inc/config.inc"

############
### Function: whatRepo
### Argument: String representing a directory
### Return: Location of .git within that tree, or blank if there is none
############

function whatRepo() {
  local thisRepo="$1"
  if [ ! -d "$thisRepo" ]; then
    return # Not a directory
  elif ! ( cd "$thisRepo" && git rev-parse --git-dir &> /dev/null ); then
    return # Not part of a repo
  fi
  pushd . &> /dev/null || exit 1
  cd "$thisRepo" || exit 1
  local thisReturn=$(git rev-parse --show-toplevel)
  popd &> /dev/null || exit 1
  echo "$thisReturn"
}

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

############
### Set up repos
############

func_getrepos() {
  # Get app locations based on local config
  wwwPath="$(getVal wwwPath $GITROOT)"
  toolPath="$(whatRepo $(eval echo ~$(logname))/brewpi-tools-rmx)"
  if [ -z "$toolPath" ]; then
    echo -e "\nWARN: Unable to find a local BrewPi-Tools-RMX repository."
    repoArray=("$GITROOT" "$wwwPath" )
  else
    repoArray=("$toolPath" "$GITROOT" "$wwwPath" )
  fi
}

############
### Main
############

main() {
  echo -e "\n***Script $THISSCRIPT starting.***"
  declare -i didUpdate=0 # Hold a counter for having to do git pulls
  declare -a repoArray # Hold repositories to update
  pushd . &> /dev/null || die # Change into script directory so stuff works
  cd "$(dirname "$0")" || die # Move to where the script is
  func_getrepos # Get array of repos to update 
  # Loop through repos and update as necessary
  for doRepo in "${repoArray[@]}"; do
    echo -e "\nChecking $doRepo for necessary updates."
    updateRepo "$doRepo" || warn
  done
  # If we did a pull, run apt to check packages and doCleanup.sh to clean things up
  if [ "$didUpdate" -ge 1 ]; then
    "$GITROOT/utils/doDepends.sh" # Install/update all dependencies and clean local apt cache
    "$GITROOT/utils/doCleanup.sh" # Cleanup *.pyc files and empty dirs
  fi
  popd &> /dev/null || die # Move back to where we started
  echo -e "\n***Script $THISSCRIPT complete.***"
}

main
exit 0
