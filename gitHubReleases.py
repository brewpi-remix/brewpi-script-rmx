#!/usr/bin/python3

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


from urllib.request import urlopen as urlopen
import simplejson as json
import os
import pwd
import grp
import stat

repo = "https://api.github.com/repos/brewpi-remix/brewpi-firmware-rmx"

class gitHubReleases:
    def __init__(self, url):
        """
        Gets all available releases using the GitHub API
            :param url:     URL to a BrewPi firmware repository on GitHub
        """
        self.url = url
        self.releases = []
        self.update()

    def download(self, url, path):
        """
        Downloads the file at url to destination directory path, saving it
        with the same filename as in the url.
            :param url:     File to download
            :param path:    Directory into which to download
            :return:        Full path to file
        """
        try:
            f = urlopen(url)
            print("\nDownloading from: \n{0}".format(url))

            # Open our local file for writing
            fileName = os.path.join(path, os.path.basename(url))
            with open(fileName, "wb") as localFile:
                localFile.write(f.read())

            # Set owner and permissions for file
            fileMode = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP # 660
            owner = 'brewpi'
            group = 'brewpi'
            uid = pwd.getpwnam(owner).pw_uid
            gid = grp.getgrnam(group).gr_gid
            os.chown(fileName, uid, gid) # chown file
            os.chmod(fileName, fileMode) # chmod file
            return os.path.abspath(fileName)

        #handle errors
        #except urlopen.HTTPError as e:
        #    print("HTTP Error: {0} {1}".format(e.code, url))
        #except urlopen.URLError as e:
        #    print("URL Error: {0} {1}".format(e.reason, url))
        except Exception as ex:
            print("Unknown Error: {0}".format(ex))
        return None

    def update(self):
        """
        Update myself by downloading a list of releases from GitHub
        """
        #with urlopen(self.url + "/releases") as url:
        #    self.releases = url.read()

        try:
            self.releases = json.loads(urlopen(self.url + "/releases").read().decode('utf-8'))
        except:
            print("Unhandled error while downloading releases from GitHub.")
            sys.exit(1)

    def findByTag(self, tag):
        """
        Find release info for release tagged with 'tag'
            :param tag: Tag of release
            :return:    Dictionary with release info. None if not found
        """
        try:
            match = next((release for release in self.releases if release["tag_name"] == tag))
        except StopIteration:
            print("tag '{0}' not found".format(tag))
            return None
        return match

    def getBinUrl(self, tag, wordsInFileName):
        """
        Finds the download URL for a binary inside a release
            :param tag:             Tag name of the release
            :param wordsInFileName: Words to look for in the filename
            :return:                First URL that has all the words
                                    in the filename
        """
        release = self.findByTag(tag)
        downloadUrl = None

        AllUrls = (asset["browser_download_url"] for asset in release["assets"])

        for url in AllUrls:
            urlFileName = url.rpartition('/')[2] # isolate filename, which is after the last /
            if all(word.lower() in urlFileName.lower() for word in wordsInFileName):
                downloadUrl = url
                break
        return downloadUrl

    def getBin(self, tag, wordsInFileName, path=None):
        """
        Writes .bin file in release to target directory. Defaults to
        ~/downloads/tag_name/ as download location

            :param tag:             Tag name of the release
            :param wordsInFileName: Words to look for in the filename
            :param path:            Optional target directory
            :return:
        """
        downloadUrl = self.getBinUrl(tag, wordsInFileName)
        if not downloadUrl:
            return None

        if path == None:
            path = os.path.join(os.path.dirname(__file__), "downloads")

        downloadDir = os.path.join(os.path.abspath(path), tag)
        if not os.path.exists(downloadDir):
            os.makedirs(downloadDir, 0o777) # make sure files can be accessed by all in case the script was run as root

        fileName = self.download(downloadUrl, downloadDir)
        return fileName

    def getLatestTag(self, board, prerelease):
        """
        Get latest tag that contains a binary for the given board
            :param board:   Board name
            :return:        Tag of release
        """

        for release in self.releases:
            # search for stable release
            tag = release["tag_name"]
            if self.getBinUrl(tag, [board]):
                if release["prerelease"] == prerelease:
                    return tag
        return None

    def getTags(self, prerelease):
        """
        Get all available tags in repository
            :param prerelease:  True if unstable (prerelease) tags should be included
            :return:            List of tags
        """

        if prerelease:
            return [release["tag_name"] for release in self.releases]
        else:
            return [release["tag_name"] for release in self.releases if release['prerelease']==False]

    def getShields(self):
        """
        Get list of shield types in downloads
            :return:        List of Shields
        """
        shields = []
        # Get everything that has a key name of 'name'
        names = extract_values(self.releases, 'name')
        for name in names:
            # Only keep the firmware file names
            if name.startswith('brewpi-') and name.endswith('.hex'):
                file = (name.split('-'))
                # Keep only uniques
                if file[3].lower() not in shields:
                    # Create the list
                    shields.append(file[3].lower())
        shields.sort() # Sort the list
        return shields

def extract_values(obj, key):
    """Pull all values of specified key from nested JSON."""
    arr = []
    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr
    results = extract(obj, arr, key)
    return results

if __name__ == "__main__":
    # Test code
    releases = gitHubReleases(repo)

    latest = releases.getLatestTag('uno', False)
    print("Latest tag: " + latest)
    print("Stable releases: ", releases.getTags(prerelease=False))
    print("All releases: ", releases.getTags(prerelease=True))
    print("All supported shields: ", releases.getShields())
