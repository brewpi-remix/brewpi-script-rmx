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
### Include file to get config file values
### Usage: value="$(getVal $configItem $scriptPath)"
### Arguments: Strings representing:
###               1) Configuration item requested
###               2) Script root (will find config in ./settings/*)
### Return: String value of configuration item
############

# Get location of config file based on brewpi path
getConfigFile() {
  local _configPath="${1}/settings"
  if [ -f "$_configPath/config.cfg" ]; then
    echo "$_configPath/config.cfg"
  else
    echo "$_configPath/defaults.cfg"
  fi
}

# Raw read of config file
readConfig() {
  local _temp=$((grep -E "^${2} = " -m 1 "${1}" 2>/dev/null || echo "VAR = __UNDEFINED__") | head -n 1 | cut -d '=' -f 2-;)
  echo "$_temp"
}

# Strip leading/trailing spaces and trailing slash
strip() {
  local _temp=$(echo "${1}" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')
  echo "${_temp%/}"
}

# Get requested value
getVal() {
  local _configFile="$(getConfigFile ${2})"
  local _val="$(readConfig "${_configFile}" "${1}")";
  if [ "${_val}" = "__UNDEFINED__" ]; then
    local _val="$(readConfig "${2}" "${1}")";
  fi
  local _val=$(printf -- "%s" "${_val}";)
  echo $(strip ${_val})
}

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
