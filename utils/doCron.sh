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

# Change to current dir (assumed to be in a repo) so we can get the git info
pushd . &> /dev/null || exit 1
cd "$(dirname "$0")" || exit 1 # Move to where the script is
GITROOT="$(git rev-parse --show-toplevel)" &> /dev/null
if [ -z "$GITROOT" ]; then
  echo -e "\nERROR:  Unable to find my repository, did you move this file?"
  popd &> /dev/null || exit 1
  exit 1
fi

############
### Init
############

# Change to current dir (assumed to be in a repo) so we can get the git info
pushd . &> /dev/null || exit 1
cd "$(dirname "$0")" || exit 1 # Move to where the script is
GITROOT="$(git rev-parse --show-toplevel)" &> /dev/null
if [ -z "$GITROOT" ]; then
  echo -e "\nERROR:  Unable to find my repository, did you move this file?"
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

echo -e "\n***Script $THISSCRIPT starting.***"

############
### doCronEntry:  Prompts to create or update crontab entry.  Two arguments:
############

function doCronEntry {
  # Prompts to create or update crontab entry.  Two arguments:
  #   $1 = Entry name (i.e. brewpi or wifi)
  #   $2 = Cron tab entry
  entry=$1
  newEntry=$2
  echo -e "\nChecking entry for $entry."
  # find old entry for this name
  oldEntry=$(grep -A1 "entry:$entry" "$cronfile" | tail -n 1)
  # check whether it is up to date
  if [ "$oldEntry" != "$newEntry" ]; then
    # if not up to date, prompt to replace
    echo -e "\nYour current cron entry:"
    if [ -z "$oldEntry" ]; then
      echo "None."
    else
      echo "$oldEntry"
    fi
    echo -e "\nLatest version of this cron entry:"
    echo -e "$newEntry"
    while true; do
            echo -e "\nYour current cron entry differs from the latest version, would you like me"
        read -p "to create or update it? [Y/n]: " yn  < /dev/tty
        case $yn in
            '' ) doUpdate=1; break ;;
            [Yy]* ) doUpdate=1; break ;;
            [Nn]* ) break ;;
            * ) echo -e "\nEnter [y]es or [n]o." ;;
        esac
    done
    if [ ! -z $doUpdate ]; then
      line=$(grep -n "entry:$entry" /etc/cron.d/brewpi | cut -d: -f 1)
      if [ -z "$line" ]; then
        echo -e "\nAdding new cron entry to file."
        # entry did not exist, add at end of file
        echo "# entry:$entry" | tee -a "$cronfile" > /dev/null
        echo "$newEntry" | tee -a "$cronfile" > /dev/null
      else
        echo -e "\nReplacing cron entry on line $line with newest version."
        # get line number to replace
        cp "$cronfile" /tmp/brewpi.cron
        # write head of old cron file until replaced line
        head -"$line" /tmp/brewpi.cron | tee "$cronfile" > /dev/null
        # write replacement
        echo "$newEntry" | tee -a "$cronfile" > /dev/null
        # write remainder of old file
        tail -n +$((line+2)) /tmp/brewpi.cron | tee -a "$cronfile" > /dev/null
      fi
    fi
  fi
  echo -e "\nDone checking entry $entry."
}

############
# Update /etc/cron.d/brewpi
# Settings are stored in the cron file itself:
#   active entries
#   scriptpath
#   stdout/stderr redirect paths
#
# Entries is a list of entries that should be active.
#   entries="brewpi wifi"
# If an entry is disabled, it is prepended with ~
#   entries="brewpi ~wifi"
#
# Each entry is two lines, one comment with the entry name, one for the actual entry:
#   entry:wifi
#   */10 * * * * root sudo -u brewpi touch $stdoutpath $stderrpath; $scriptpath/utils/checkWiFi.sh 1>>$stdoutpath 2>>$stderrpath &
#
# This script checks whether the available entries are up-to-date.  If not,
# it can replace the entry with a new version.  If the entry is not in
# entries (enabled or disabled), it needs to be disabled or added.
# Known entries:
#   brewpi
#   wifi
#
# Full Example:
#   stderrpath="/home/brewpi/logs/stderr.txt"
#   stdoutpath="/home/brewpi/logs/stdout.txt"
#   scriptpath="/home/brewpi"
#   entries="brewpi wifi"
#   # entry:brewpi
#   * * * * * brewpi python $scriptpath/brewpi.py --checkstartuponly --dontrunfile $scriptpath/brewpi.py 1>/dev/null 2>>$stderrpath; [ $? != 0 ] && python -u $scriptpath/brewpi.py 1>$stdoutpath 2>>$stderrpath &
#   # entry:wifi
#   */10 * * * * root sudo -u brewpi touch $stdoutpath $stderrpath; $scriptpath/utils/checkWiFi.sh 1>>$stdoutpath 2>>$stderrpath &
#
############

############
### Check for old crontab entry
############

crontab -u brewpi -l > /tmp/oldcron 2> /dev/null
if [ -s /tmp/oldcron ]; then
  if grep -q "brewpi.py" /tmp/oldcron; then
    > /tmp/newcron||die
    firstLine=true
    while read line
    do
      if [[ "$line" == *brewpi.py* ]]; then
        case "$line" in
          \#*) # Copy commented lines
            echo "$line" >> /tmp/newcron;
            continue ;;
          *)   # Process anything else
            echo -e "It looks like you have an old brewpi entry in your crontab."
            echo -e "The cron job to start/restart brewpi has been moved to cron.d."
            echo -e "This means the lines for brewpi in your crontab are not needed"
            echo -e "anymore.  Nearly all users will want to comment out this line.\n"
            firstLine=false
            echo "crontab line: $line"
            read -p "Do you want to comment out this line? [Y/n]: " yn </dev/tty
            case "$yn" in
              ^[Yy]$ ) echo "Commenting line:\n";
                            echo "# $line" >> /tmp/newcron;;
              ^[Nn]$ ) echo -e "Keeping original line:\n";
                            echo "$line" >> /tmp/newcron;;
              * ) echo "Not a valid choice, commenting out old line.";
                              echo "Commenting line:\n";
                                  echo "# $line" >> /tmp/newcron;;
            esac
        esac
      fi
    done < /tmp/oldcron
        # Install the updated old cron file to the new location
    crontab -u brewpi /tmp/newcron||die 2> /dev/null
    rm /tmp/newcron||warn
    if ! ${firstLine}; then
      echo -e "Updated crontab to read:\n"
      crontab -u brewpi -l||die 2> file
      echo -e "Finished updating crontab."
    fi
  fi
fi
rm /tmp/oldcron||warn

# default cron lines for brewpi
cronfile="/etc/cron.d/brewpi"
# make sure it exists
touch "$cronfile"

# Get variables from old cron job.
entries=$(grep -m1 'entries=' /etc/cron.d/brewpi) && entries=${entries##*=}
scriptpath=$(grep -m1 'scriptpath=' /etc/cron.d/brewpi) && scriptpath=${scriptpath##*=}
stdoutpath=$(grep -m1 'stdoutpath=' /etc/cron.d/brewpi) && stdoutpath=${stdoutpath##*=}
stderrpath=$(grep -m1 'stderrpath=' /etc/cron.d/brewpi) && stderrpath=${stderrpath##*=}

# if the variables did not exist, add the defaults
if [ -z "$entries" ]; then
  entries="brewpi"
  echo -e "\nNo cron file present, or it is an old version, starting fresh."
  rm -f "$cronfile"
  echo "entries=\"brewpi\"" | tee "$cronfile" > /dev/null
fi

if [ -z "$scriptpath" ]; then
  scriptpath="$GITROOT"
  echo -e "\nNo previous setting for scriptpath found, using default:\n$scriptpath."
  entry="1iscriptpath=$scriptpath"
  sed -i "$entry" "$cronfile"
fi

if [ -z "$stdoutpath" ]; then
  stdoutpath="$GITROOT/logs/stdout.txt"
  echo -e "\nNo previous setting for stdoutpath found, using default:\n$stdoutpath."
  entry="1istdoutpath=$stdoutpath"
  sed -i "$entry" "$cronfile"
fi

if [ -z "$stderrpath" ]; then
  stderrpath="$GITROOT/logs/stderr.txt"
  echo -e "\nNo previous setting for stderrpath found, using default:\n$stderrpath."
  entry="1istderrpath=$stderrpath"
  sed -i "$entry" "$cronfile"
fi

# crontab entries
brewpicron='* * * * * brewpi python $scriptpath/brewpi.py --checkstartuponly --dontrunfile $scriptpath/brewpi.py 1>/dev/null 2>>$stderrpath; [ $? != 0 ] && python -u $scriptpath/brewpi.py 1>$stdoutpath 2>>$stderrpath &'
wificheckcron='*/10 * * * * root sudo -u brewpi touch $stdoutpath $stderrpath; $scriptpath/utils/checkWiFi.sh 1>>$stdoutpath 2>>$stderrpath &'

# Entry for brewpi
for entry in $entries; do
  if [[ $entry =~ .*brewpi* ]]; then
    doCronEntry brewpi "$brewpicron"
  fi
done

# Entry for WiFi check script
foundWiFi=false
for entry in $entries; do
  if [[ $entry =~ .*~wifi* ]]; then
    foundWiFi=true
    echo -e "\nWiFi disabled."
  elif [[ $entry =~ .*wifi* ]]; then
    # Check whether cron entry is up to date
    foundWiFi=true
    doCronEntry wifi "$wificheckcron"
  fi
done

# If there was no entry for wifi, ask to add it or disable it
wlan=$(cat /proc/net/wireless | perl -ne '/(\w+):/ && print $1')
if [ "$foundWiFi" == false ]; then
  echo -e "\nNo setting found for wifi check script."
  if [[ ! -z "$wlan" ]]; then
    echo -e "\nIt looks like you're running a WiFi adapter on your Pi.  Some users"
    echo -e "have experienced issues with the adapter losing network connectivity."
    echo -e "This script can create a scheduled job to help reconnect the Pi"
    echo -e "to your network.\n"
      read -p "Would you like to create this job? [Y/n]: " yn </dev/tty
    if [ -z "$yn" ]; then
      yn="y"
    fi
    case "$yn" in
      y | Y | yes | YES| Yes )
        # update entries="..." to entries="... wifi" (enables check)
        sed -i '/entries=.*/ s/"$/ wifi"/' "$cronfile"
        doCronEntry wifi "$wificheckcron"
        ;;
      * )
       # update entries="..." to entries="... ~wifi" (disables check)
       sed -i '/entries=.*/ s/"$/ ~wifi"/' "$cronfile"
       echo -e "\nSetting wifiChecker to disabled."
       ;;
    esac
  else
    echo -e "\nIt looks like you're not running a WiFi adapter on your Pi."
  fi
fi

echo -e "\nRestarting cron:"
/etc/init.d/cron restart||die

echo -e "\n***Script $THISSCRIPT complete.***"

