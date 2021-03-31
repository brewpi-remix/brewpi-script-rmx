# <a name="top"></a>![BrewPi Remix Legacy Remix Logo](https://raw.githubusercontent.com/brewpi-remix/brewpi-www-rmx/master/images/brewpi_logo.png)

# BrewPi Remix Remix Utilities

The `utils` directory contains `bash` scripts which are used both by the user, and the system.  They are generally used to enforce conditions prior to executing a Python script, such as activating the Python virtual environment (venv) or runnign as root.

|Filename|Description|
|---|---|
|`doBrewPi.sh`|This is the script called by the BrewPi Remix daemon which does all of the work of keeping BrewPi Remix running.  You should not need to execute this script in normal operation. The daemon runs as `brewpi`, or the name of the chamber when used in multi-chamber mode.|
|`doCleanup.sh`|This is a script which is called by the upgrade process, intended to help clean up remnants of the previous version before restarting.|
|`doDaemon.sh`|This script checks and/or creates the system daemons used by BrewPi Remix: the BrewPi Remix Daemon (named for the chamber in multi-chamber mode) and the WiFIChecker.|
|`doDepends.sh`|This script checks and enforces the apt and pip dependencies for BrewPi Remix.|
|`doFlash.sh`|This script will set up and execute the `updateFirmware.py` code to flash firmware from the command line.|
|`doIndex.sh`|This script is called by the install process to generate the root web index files as symlinks.|
|`doMenu.sh`|This script is not yet used.|
|`doPerms.sh`|This script may be the most used for BrewPi Remix users.  It will check all file and system permissions.  After any manual manipulation of files, this script should be called in order to ensure BrewPi Remix can operate.  It is often the first troubleshooting step when a user asks for help.|
|`doUpdate.sh`|This is the update script used to bring BrewPi Remix up to the current version.|
|`doWiFi.sh`|This script is the compliment to the `doBrewPi.sh` script.  Historically, the Raspberry Pi has had challenges remaining connected to WiFi.  This script is run by a daemon process called `wificheck` and will periodically ping the gateway.  When it is unable to reach the gateway it will restart the network stack as first aid.|