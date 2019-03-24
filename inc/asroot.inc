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

############
### Include file to check privilges and permissions
############

### Check if we have root privs to run
if [[ $EUID -ne 0 ]]; then
  sudo -n true 2> /dev/null
  retval="$?"
  if [[ "$retval" == "0" ]]; then
    echo -e "\nNot runing as root, relaunching correctly." > /dev/tty
    sleep 2
    eval "sudo bash $SCRIPTPATH/$THISSCRIPT $*"
    exit $?
  else
    # sudo not available, give instructions
    echo -e "\nThis script must be run as root: sudo $SCRIPTPATH/$THISSCRIPT $*" 1>&2 > /dev/tty
    exit 1
  fi
fi
# And get the user home directory
if [ -n "$SUDO_USER" ]; then REALUSER="$SUDO_USER"; else REALUSER=$(whoami); fi
shadow="$( (getent passwd "$REALUSER") 2>&1)"
retval="$?"
if [ "$retval" -eq 0 ]; then
  HOMEPATH="$(echo "$shadow" | cut -d':' -f6)"
else
  echo -e "\nUnable to retrieve $REALUSER's home directory. Manual install may be necessary." > /dev/tty
  exit 1
fi
