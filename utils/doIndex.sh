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

func_doinit() {
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

  # Files for which we will create links
  INDEXLINKS="multi-index/index.php touch-icon-ipad.png touch-icon-ipad-retina.png touch-icon-iphone.png favicon.ico"
}

############
### Get web locations
############

func_getweb() {
  # Get this app's web root in config file
  wwwPath="$(getVal wwwPath $GITROOT)"
  # Find root web path based on Apache2 config
  echo -e "\nSearching for default web location."
  rootWeb="$(grep DocumentRoot /etc/apache2/sites-enabled/000-default* |xargs |cut -d " " -f2)"
  if [ ! -z "$rootWeb" ]; then
    echo -e "\nFound $rootWeb in /etc/apache2/sites-enabled/000-default*."
  else
    echo "Something went wrong searching for /etc/apache2/sites-enabled/000-default*."
    echo "Fix that and come back to try again."
    exit 1
  fi
}

############
### Create links
############

func_createlinks() {
  # Loop through the files to make links
  for link in $INDEXLINKS; do
    echo -e "\nCreating link to $link in $rootWeb."
    ln -sf "$wwwPath/$link" "$rootWeb/$(basename $link)"
  done
}

############
### Main
############

main() {
  func_doinit "$@" # Initialize constants and variables
  echo -e "\n***Script $THISSCRIPT starting.***"
  func_getweb # Get web locations
  func_createlinks # Create all index links
  echo -e "\n***Script $THISSCRIPT complete.***"
}

main "$@"
exit 0

