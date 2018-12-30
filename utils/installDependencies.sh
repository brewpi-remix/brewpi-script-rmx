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
THISSCRIPT="fixPermissions.sh"
VERSION="0.4.5.0"
# These should stay the same
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
  echo -e "sudo . $THISSCRIPT\n" 1>&2
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
  echo "Setup NOT completed."
  echo
}

die () {
  local st="$?"
  warn "$@"
  exit "$st"
}

############
### Check for network connection
###########
echo -e "\nChecking for connection to GitHub.\n"
ping -c 3 github.com &> /dev/null 1>&2
if [ $? -ne 0 ]; then
  echo "----------------------------------------------"
  echo "Could not ping github.com. Are you sure you"
  echo "have a working Internet connection? Installer"
  echo "will exit, because it needs to fetch code from"
  echo "github.com."
  echo
  exit 1
fi
echo -e "\nConnection to Internet sucessfull.\n"

############
### Update required packages
############
lastUpdate=$(stat -c %Y /var/lib/apt/lists)
nowTime=$(date +%s)
if [ $(($nowTime - $lastUpdate)) -gt 604800 ] ; then
  echo -e "\nLast apt-get update was over a week ago. Running"
  echo -e "apt-get update before updating dependencies.\n"
  apt-get update||die
  echo
fi

echo -e "\n***** Processing BrewPi dependencies. *****\n"

echo -e "Updating required apt packages.\n"

# Install support for Arduino
apt-get install arduino-core -y

# Install general stuff
apt-get install git-core pastebinit build-essential -y

# Install Apache
apt-get install apache2 -y

# Install PHP
apt-get install libapache2-mod-php php-cli php-common php-cgi php php-mbstring -y

# Install Python
apt-get install python-dev python-pip python-configobj -y

echo -e "\nUpdating required python packages via pip.\n"
pip install pyserial psutil simplejson configobj gitpython --upgrade

echo -e "\n***** Done processing BrewPi dependencies. *****\n"

