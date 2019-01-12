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
### Fix permissions
############

echo -e "\nFixing file permissions for $WEBPATH."
chown -R www-data:www-data "$WEBPATH"||warn
find "$WEBPATH" -type d -exec chmod 750 {} \;||warn
find "$WEBPATH" -type f -exec chmod 640 {} \;||warn
find "$WEBPATH/data" -type d -exec chmod 770 {} \;||warn
find "$WEBPATH/data" -type f -exec chmod 660 {} \;||warn
find "$WEBPATH" -type f -name "*.json" -exec chmod 660 {} \;||warn
chmod 775 "$WEBPATH/"||warn

echo -e "\nFixing file permissions for $GITROOT."
chown -R brewpi:brewpi "$GITROOT"||warn
find "$GITROOT" -type d -exec chmod 775 {} \;||warn
find "$GITROOT" -type f -exec chmod 660 {} \;||warn
find "$GITROOT" -type f -regex ".*\.\(py\|sh\)" -exec chmod 770 {} \;||warn

echo -e "\n***Script $THISSCRIPT complete.***"

exit 0

