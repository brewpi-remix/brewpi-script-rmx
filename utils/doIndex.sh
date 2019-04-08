#!/bin/bash

# Copyright (C) 2018, 2019 Lee C. Bussy (@LBussy)

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

# Declare this script's constants
declare SCRIPTPATH GITROOT WWWPATH ROOTWEB
# Declare /inc/const.inc file constants
declare THISSCRIPT SCRIPTNAME VERSION GITROOT GITURL GITPROJ PACKAGE
# Declare /inc/asroot.inc file constants
declare HOMEPATH REALUSER

############
### Init
############

init() {
    # Change to current dir (assumed to be in a repo) so we can get the git info
    pushd . &> /dev/null || exit 1
    SCRIPTPATH="$( cd "$(dirname "$0")" || exit 1 ; pwd -P )"
    cd "$SCRIPTPATH" || exit 1 # Move to where the script is
    GITROOT="$(git rev-parse --show-toplevel)" &> /dev/null
    if [ -z "$GITROOT" ]; then
        echo -e "\nERROR: Unable to find my repository, did you move this file or not run as root?"
        popd &> /dev/null || exit 1
        exit 1
    fi
    
    # Get project constants
    # shellcheck source=/dev/null
    . "$GITROOT/inc/const.inc" "$@"
    
    # Get error handling functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/error.inc" "$@"
    
    # Get help and version functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/asroot.inc" "$@"
    
    # Get help and version functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/help.inc" "$@"
    
    # Get config file read functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/config.inc" "$@"

    # Get network test functionality
    # shellcheck source=/dev/null
    . "$GITROOT/inc/nettest.inc" "$@"
}

############
### Create a banner
############

banner() {
    local adj
    adj="$1"
    echo -e "\n***Script $THISSCRIPT $adj.***"
}

############
### Get web locations
############

getweb() {
  # Get this app's web root in config file
  WWWPATH="$(getVal wwwPath "$GITROOT")"
  # Find root web path based on Apache2 config
  echo -e "\nSearching for default web location."
  ROOTWEB="$(grep DocumentRoot /etc/apache2/sites-enabled/000-default* |xargs |cut -d " " -f2)"
  if [ -n "$ROOTWEB" ]; then
    echo -e "\nFound $ROOTWEB in /etc/apache2/sites-enabled/000-default*."
  else
    echo "Something went wrong searching for /etc/apache2/sites-enabled/000-default*."
    echo "Fix that and come back to try again."
    exit 1
  fi
}

############
### Create link
############

createlinks() {
  echo -e "\nCreating link to multi-index.php in $ROOTWEB."
  rm -f "$ROOTWEB/index.html"
  ln -sf "$WWWPATH/multi-index.php" "$ROOTWEB/index.php"
}

############
### Main function
############

main() {
    init "$@" # Init and call supporting libs
    const "$@" # Get script constants
    asroot # Make sure we are running with root privs
    help "$@" # Process help and version requests
    banner "starting"
    getweb # Find web paths
    createlinks # Create symlink for Index
    banner "complete"
}

main "$@" && exit 0
