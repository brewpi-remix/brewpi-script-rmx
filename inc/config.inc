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
### Include file to get config file values
### Usage: value="$(getVal $configItem $scriptPath)"
### Arguments: Strings representing:
###               $configItem) Configuration item requested
###               $scriptPath) Script root (will find config in ./settings/\*)
### Return: String value of configuration item
############

# Get location of config file based on brewpi path
getConfigFile() {
    local configPath
    configPath="${1}/settings"
    if [ -f "$configPath/config.cfg" ]; then
        echo "$configPath/config.cfg"
    else
        echo "$configPath/defaults.cfg"
    fi
}

# Get location of default file based on brewpi path
getDefaultFile() {
    local configPath
    configPath="${1}/settings"
    if [ -f "$configPath/defaults.cfg" ]; then
        echo "$configPath/defaults.cfg"
    fi
}

# Raw read of config file
readConfig() {
    local val
    val=$( (grep -E "^${2} = " -m 1 "${1}" 2>/dev/null || echo "VAR = __UNDEFINED__") | head -n 1 | cut -d '=' -f 2-;)
    echo "$val"
}

# Strip leading/trailing spaces and trailing slash
strip() {
    local val
    val=$(echo "${1}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
    echo "${val%/}"
}

# Get requested value
getVal() {
    local configFile defConfigFile val configItem configPath
    configItem="${1}"
    configPath="${2}"
    configFile="$(getConfigFile "${configPath}")"
    defConfigFile="$(getDefaultFile "${configPath}")"
    val="$(readConfig "${configFile}" "${configItem}")"
    if [[ "${val}" == *"__UNDEFINED__"* ]]; then
        val="$(readConfig "${defConfigFile}" "${configItem}")"
    fi
    val=$(printf -- "%s" "${val}";)
    echo "$(strip "${val}")"
}

# Check if we were used as an include or called directly,
(return 0 2>/dev/null) || echo "Intended to be used as an include file only."
