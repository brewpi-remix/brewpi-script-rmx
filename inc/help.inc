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
### Include file for --help and --version functionality
############

# Outputs to stdout the --help usage message.
usage() {
    echo -e "\n$SCRIPTNAME usage: sudo $SCRIPTPATH/$THISSCRIPT"
}

# Outputs to stdout the --version message.
version() {
cat << EOF

"$SCRIPTNAME" Copyright (C) 2019 Lee C. Bussy (@LBussy)

This program comes with ABSOLUTELY NO WARRANTY.

This is free software, and you are welcome to redistribute it
under certain conditions.

There is NO WARRANTY, to the extent permitted by law.
EOF
}

# Processes help/version arguments
help() {
    declare arg
    arg="$1"
    if [ -n "$arg" ]; then
        arg="${arg//-}" # Strip out all dashes
        if [[ "$arg" == "h"* ]]; then usage; exit 0; fi
        if [[ "$arg" == "v"* ]]; then version; exit 0; fi
    fi
}

# Check if we were used as an include or called directly,
(return 0 2>/dev/null) || echo "Intended to be used as an include file only."
