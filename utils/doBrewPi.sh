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

declare GITROOT

############
### Init
############

init() {
    # Change to current dir (assumed to be in a repo) so we can get the git info
    pushd . &> /dev/null || exit 1
    cd "$(dirname $(readlink -e $0))" || exit 1 # Move to where the script is
    GITROOT="$(git rev-parse --show-toplevel)" &> /dev/null
    if [ -z "$GITROOT" ]; then
        echo -e "\nERROR:  Unable to find my repository, did you move this file?"
        popd &> /dev/null || exit 1
        exit 1
    fi

    # Get help and version functionality
    . "$GITROOT/inc/help.inc" "$@"
}

############
### Loop and keep Brewpi running
############

loop() {
    local script stdOut stdErr python
    script="$GITROOT/brewpi.py"
    python="$GITROOT/venv/bin/python3"


    while :
    do
        if ("$python" -u "$script" --check --donotrun); then
            USE_TIMESTAMP_LOG=true "$python" -u "$script" --log --datetime
        else
            sleep 1
        fi
    done
}

############
### Main function
############

main() {
    init "$@" # Get environment information
    help "$@" # Process help and version requests
    loop "$@" # Loop forever
}

main "$@" && exit 0
