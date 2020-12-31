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

############
### Get the BrewPi User's Home Directory
############

userroot() {
    # Get the BrewPi user's home directory
    USERROOT=$(echo "$GITROOT" | cut -d "/" -f-3)
    if [[ ! -d "$USERROOT" ]]; then
        echo -e "\nUnable to retrieve BrewPi's home directory. Manual install may be necessary." > /dev/tty
        exit 1
    fi
}

# Check if we were used as an include or called directly,
(return 0 2>/dev/null) || echo "Intended to be used as an include file only."
