#!/bin/bash
# shellcheck disable=SC2034

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

# Declare this script's constants
declare SCRIPTPATH GITROOT APTPACKAGES PIP3PACKAGES
# Declare /inc/const.inc file constants
declare THISSCRIPT SCRIPTNAME VERSION GITROOT GITURL GITPROJ PACKAGE
# Declare /inc/asroot.inc file constants
declare HOMEPATH REALUSER
# Declare placeholders for nginx work
declare KEEP_NGINX

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
    
    # Read configuration
    # shellcheck source=/dev/null
    . "$GITROOT/inc/config.inc" "$@"
    
    # Check network connectivity
    # shellcheck source=/dev/null
    . "$GITROOT/inc/nettest.inc" "$@"
    
    # Packages to be installed/checked via apt
    APTPACKAGES="git python3 python3-pip python3-setuptools arduino-core apache2 php libapache2-mod-php php-cli php-cgi php-mbstring php-xml libatlas-base-dev python3-numpy python3-scipy"
    # Packages to be installed/check via pip3
    PIP3PACKAGES="pyserial psutil simplejson configobj gitpython sentry-sdk"
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
### Check last apt update date
############

apt_check() {
    echo -e "\nFixing any broken installations before proceeding."
    # Update any expired keys
    for key in $(sudo apt-key list 2> /dev/null | grep expired | cut -d'/' -f2 | cut -d' ' -f1); do
        sudo apt-key adv --recv-keys --keyserver keys.gnupg.net "$key" 2> /dev/null
    done
    # Fix any broken installs
    sudo apt-get --fix-broken install -y||die
    # Remove any orphaned packages
    sudo apt-get autoremove --purge -y -q=2||die
    # Run 'apt update' if last run was > 1 week ago
    lastUpdate=$(stat -c %Y /var/lib/apt/lists)
    nowTime=$(date +%s)
    if [ $((nowTime - lastUpdate)) -gt 604800 ] ; then
        echo -e "\nLast apt update was over a week ago. Running apt update before updating"
        echo -e "dependencies."
        apt-get update -yq||die
        echo
    fi
}

############
### Remove php5 packages if installed
############

rem_php5() {
    echo -e "\nChecking for previously installed php5 packages."
    # Get list of installed packages
    php5packages="$(dpkg --get-selections | awk '{ print $1 }' | grep 'php5')"
    if [[ -z "$php5packages" ]] ; then
        echo -e "\nNo php5 packages found."
    else
        echo -e "\nFound php5 packages installed.  It is recomended to uninstall all php before"
        echo -e "proceeding as BrewPi requires php7 and will install it during the install"
        read -rp "process.  Would you like to clean this up before proceeding?  [Y/n]: " yn  < /dev/tty
        case $yn in
            [Nn]* )
                echo -e "\nUnable to proceed with php5 installed, exiting.";
            exit 1;;
            * )
                sudo apt-get autoremove --purge php5 -y -q=2;
                echo -e "\nCleanup of the php environment complete."
            ;;
        esac
    fi
}

############
### Remove nginx packages if installed
############

rem_nginx() {
    echo -e "\nChecking for previously installed nginx packages."
    # Get list of installed packages
    nginxPackage="$(dpkg --get-selections | awk '{ print $1 }' | grep 'nginx')"
    if [[ -z "$nginxPackage" ]] ; then
        echo -e "\nNo nginx packages found."
    else
        echo -e "\nFound nginx packages installed. nginx will interfere with Apache2 and it is";
        echo -e "recommended to uninstall. You can either do that now, or choose to reconfigure";
        echo -e "nginx to use an alternate port. Choose one of the following:";
        echo -e "\n\t[u] Uninstall nginx (this will break Fermentrack if installed.)";
        echo -e "\t[r] Reconfiggure nginx (and Fermentrack) to use a different port.";
        echo -e "\t[X] Exit and do nothing.\n";
        read -rp "[u/r/X]: " yn  < /dev/tty
        case $yn in
            [Uu]* )
                # Uninstall nginx
                echo "";
                sudo systemctl stop nginx;
                sudo systemctl disable nginx;
                sudo apt-get autoremove --purge nginx -y -q=2;
                echo -e "\nCleanup of the nginx environment complete.";
                ;;
            [Rr]* )
                echo -e "\nReconfiguring nginx to alternate port.";
                KEEP_NGINX=1;;
            * )
                echo -e "\nMaking no changes.";
                exit 1;
                ;;
        esac
    fi
}

############
### Reconfigure nginx
############

keep_nginx() {
    local path ip
    path="/etc/nginx/sites-enabled"
    echo -e "\nAttempting to configure nginx for ports 81/444."
    for file in "$path"/*; do
        expanded=$(readlink -f "$file")
        cp "$expanded" "$expanded.bak"
        sed -i "s/listen 80 default_server/listen 81 default_server/g" "$expanded"
        sed -i "s/listen \[::\]:80 default_server/listen \[::\]:81 default_server/g" "$expanded"
        sed -i "s/listen 443 ssl default_server/listen 444 ssl default_server/g" "$expanded"
        sed -i "s/listen \[::\]:443 ssl default_server/listen \[::\]:444 ssl default_server/g" "$expanded"
    done
    systemctl restart nginx;
    ip=$(ifconfig | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1')
    echo -e "\nReconfigured nginx to serve applications on port 81/444. You will have to"
    echo -e "access your previous nginx websites with the port at the end of the URL like:"
    echo -e "http://$(hostname).local:81 or http://$ip:81"
    sleep 5
}

############
### Install and update required packages
############

do_packages() {
    # Now install any necessary packages if they are not installed
    local didInstall
    didInstall=0
    echo -e "\nFixing any broken installations before proceeding."
    sudo apt-get --fix-broken install -y||die
    echo -e "\nChecking and installing required dependencies via apt."
    for pkg in ${APTPACKAGES,,}; do
        pkgOk=$(dpkg-query -W --showformat='${Status}\n' "${pkg,,}" | \
        grep "install ok installed")
        if [ -z "$pkgOk" ]; then
            ((didInstall++))
            echo -e "\nInstalling '$pkg'.\n"
            apt-get install "${pkg,,}" -y -q=2||die
            echo
        fi
    done
    if [[ "$didInstall" -gt 0 ]]; then
        echo -e "All required apt packages have been installed."
    else
        echo -e "\nNo apt packages were missing."
    fi
    
    # Get list of installed packages with upgrade available
    upgradesAvail=$(dpkg --get-selections | xargs apt-cache policy {} | \
        grep -1 Installed | sed -r 's/(:|Installed: |Candidate: )//' | \
    uniq -u | tac | sed '/--/I,+1 d' | tac | sed '$d' | sed -n 1~2p)
    
    # Loop through only the required packages and see if they need an upgrade
    for pkg in ${APTPACKAGES,,}; do
        if [[ ${upgradesAvail,,} == *"$pkg"* ]]; then
            echo -e "\nUpgrading '$pkg'.\n"
            apt-get install "${pkg,,}" -y -q=2||die
            doCleanup=1
        fi
    done
    
    # Cleanup if we updated packages
    if [ -n "$doCleanup" ]; then
        echo -e "\nCleaning up local repositories."
        apt-get clean -y||warn
        apt-get autoclean -y||warn
        apt-get autoremove --purge -y||warn
    else
        echo -e "\nNo apt updates to apply."
    fi
    
    # Install any Python packages not installed, update those installed
    echo -e "\nChecking and installing required dependencies via pip3."
    # shellcheck disable=SC2016
    pipcmd='pipInstalled=$(pip3 list --format=columns)'
    eval "$pipcmd"
    # shellcheck disable=SC2016
    pipcmd='pipInstalled=$(echo "$pipInstalled" | cut -f1 -d" ")'
    eval "$pipcmd"
    for pkg in ${PIP3PACKAGES,,}; do
        # shellcheck disable=SC2154
        if [[ ! ${pipInstalled,,} == *"$pkg"* ]]; then
            echo -e "\nInstalling '$pkg'."
            pip3 install "$pkg" -q||die
        else
            echo -e "\nChecking for update to '$pkg'."
            pip3 install "$pkg" --upgrade -q||die
        fi
    done
}

############
### Reset BT baud rate < Pi4
############

do_aioblescan() {
    # Install aioblescan
    local blerepo device fast safe file
    echo -e "\nInstalling BLEacon support via aioblescan."
    blerepo="https://github.com/brewpi-remix/aioblescan.git"
    file="/usr/bin/btuart"
    fast="\$HCIATTACH \/dev\/serial1 bcm43xx 921600 noflow - \$BDADDR"
    safe="\$HCIATTACH \/dev\/serial1 bcm43xx 460800 noflow - \$BDADDR"
    rm -fr "$HOMEPATH/aioblescan"
    git clone "$blerepo" "$HOMEPATH/aioblescan"
    (cd "$HOMEPATH/aioblescan" || exit; python3 setup.py install)
    rm -fr "$HOMEPATH/aioblescan"
    # Slow down uart speeds on < Pi4
    if [ -f "$file" ]; then
        sed -i "s/$fast/$safe/g" "$file"
    fi
    device=$(hciconfig | grep "hci" | grep "UART" | tr -s ' ' | cut -d":" -f1)
    if [ -n "$device" ]; then
        if grep -vq "Pi 4" /proc/device-tree/model; then
            stty -F /dev/serial1 460800
        fi
    fi
}

############
### Main
############

main() {
    init "$@" # Init and call supporting libs
    const "$@" # Get script constants
    asroot # Make sure we are running with root privs
    help "$@" # Handle help and version requests
    banner "starting"
    apt_check # Check on apt packages
    rem_php5 # Remove php5 packages
    rem_nginx # Offer to remove nginx packages
    if [[ $KEEP_NGINX -eq 1 ]]; then
        keep_nginx "$@" # Attempt to reconfigure nginx
    fi
    do_packages # Check on required packages
    do_aioblescan
    banner "complete"
}

main "$@" && exit 0
