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

from collections import namedtuple, OrderedDict
from distutils.version import LooseVersion
import unittest

# SetttingMigrate containes 3 values:
# key: the JSON key for the version in maxVersion
# minVersion: the minimum version to restore from. Use 0 when all are valid.
# maxVersion: the maximum version to restore to. Use 1000 when the most current release is still valid
# alias: alternative keys from previous versions that should be interpreted as new key
#
SettingMigrate = namedtuple('SettingMigrate', ['key', 'minVersion', 'maxVersion', 'aliases'])

MigrateSettingsDefaultRestoreValidity = [
    SettingMigrate('tempFormat', '0', '1000', []),
    SettingMigrate('tempSetMin', '0', '1000', []),
    SettingMigrate('tempSetMax', '0', '1000', []),
    SettingMigrate('Kp', '0', '1000', []),
    SettingMigrate('Ki', '0', '1000', []),
    SettingMigrate('Kd', '0', '1000', []),
    SettingMigrate('iMaxErr', '0', '1000', []),
    SettingMigrate('pidMax', '0.2.4', '1000', []),
    SettingMigrate('idleRangeH', '0', '1000', []),
    SettingMigrate('idleRangeL', '0', '1000', []),
    SettingMigrate('heatTargetH', '0', '1000', []),
    SettingMigrate('heatTargetL', '0', '1000', []),
    SettingMigrate('coolTargetH', '0', '1000', []),
    SettingMigrate('coolTargetL', '0', '1000', []),
    SettingMigrate('maxHeatTimeForEst', '0', '1000', []),
    SettingMigrate('maxCoolTimeForEst', '0', '1000', []),
    SettingMigrate('fridgeFastFilt', '0.2.0', '1000', []),
    SettingMigrate('fridgeSlowFilt', '0.2.0', '1000', []),
    SettingMigrate('fridgeSlopeFilt', '0.2.0', '1000', []),
    SettingMigrate('beerFastFilt', '0.2.0', '1000', []),
    SettingMigrate('beerSlowFilt', '0.2.3', '1000', []),
    SettingMigrate('beerSlopeFilt', '0.2.3', '1000', []),
    SettingMigrate('lah', '0', '1000', []),
    SettingMigrate('hs', '0', '1000', []),
    SettingMigrate('heatEst', '0', '1000', []),
    SettingMigrate('coolEst', '0', '1000', []),
    SettingMigrate('fridgeSet', '0', '1000', []),
    SettingMigrate('beerSet', '0', '1000', []),
    SettingMigrate('mode', '0', '1000', [])
]

class MigrateSettings:

    def __init__(self, rv = None):
        '''
        :param rv: list of SettingMigrate namedtuples in the order they need to be restored
        '''
        if(rv == None):
            self.restoreValidity = MigrateSettingsDefaultRestoreValidity
        else:
            self.restoreValidity = rv

    def getKeyValuePairs(self, oldSettings, oldVersion, newVersion):
        '''
        Settings are in order to restore them and are read from the old settings
        Versions are compared to see which settings are still considered valid

        Keyword arguments:
        :param oldSettings: a dict of settings
        :param oldVersion: a string with the old version number
        :param newVersion: a string with the new version number
        :return keyValuePairs: OrderedDict of settings to restore
        :return oldSettings: settings that are not restored
        '''
        keyValuePairs = OrderedDict()
        oldSettingsCopy = oldSettings.copy() # get copy because we are removing items from the dict
        for setting in self.restoreValidity:
            for oldKey in [setting.key] + setting.aliases:
                if oldKey in oldSettingsCopy:
                    if (LooseVersion(oldVersion) >= LooseVersion(setting.minVersion) and
                            LooseVersion(newVersion) <= LooseVersion(setting.maxVersion)):
                        keyValuePairs[setting.key] = oldSettingsCopy.pop(oldKey)
                        break
        return keyValuePairs, oldSettingsCopy

class TestSettingsMigrate(unittest.TestCase):

    def testMinVersion(self):
        ''' Test if key is omitted when oldVersion < minVersion'''
        mg = MigrateSettings([
            SettingMigrate('key1', '0.2.0', '1000', []),
            SettingMigrate('key2', '0.1.1', '1000', []),
            ])
        oldSettings = {'key1': 1, 'key2': 2}
        restored, omitted = mg.getKeyValuePairs(oldSettings, '0.1.8', '0.3.0')
        self.assertEqual(restored,
                         OrderedDict([('key2', 2)]),
                         "Should only return key2")


    def testMaxVersion(self):
        ''' Test if key is omitted when newVersion > maxVersion'''
        mg = MigrateSettings([
            SettingMigrate('key1', '0.2.0', '0.3.0', []),
            SettingMigrate('key2', '0.1.1', '1000', []),
            ])
        oldSettings = {'key1': 1, 'key2': 2}
        restored, omitted = mg.getKeyValuePairs(oldSettings, '0.3.0', '0.4.0')
        self.assertEqual(restored,
                         OrderedDict([('key2', 2)]),
                         "Should only return key2")

    def testReturningNotRestored(self):
        mg = MigrateSettings([
            SettingMigrate('key1', '0.2.0', '0.3.0', []),
            SettingMigrate('key2', '0.1.1', '1000', []),
            ])
        oldSettings = {'key1': 1, 'key2': 2}
        restored, omitted = mg.getKeyValuePairs(oldSettings, '0.3.0', '0.4.0')
        self.assertEqual(restored,
                         OrderedDict([('key2', 2)]),
                         "Should only return key2")

    def testAliases(self):
        ''' Test if aliases for old keys result in the new key being returned with the old value'''
        mg = MigrateSettings([ SettingMigrate('key1', '0', '1000', ['key1a', 'key1b'])])
        oldSettings = {'key1a': 1}
        restored, omitted = mg.getKeyValuePairs(oldSettings, '1', '1')
        self.assertEqual(restored, OrderedDict([('key1', 1)]))

    def testBrewPiFilters(self):
        ''' Test if filters are only restored when old version > 0.2. The filter format was different earlier'''
        mg = MigrateSettings()
        oldSettings = {'fridgeFastFilt': 4}
        for oldVersion in ['0.1.0', '0.1.9', '0.1', '0.1.9.1']:
            restored, omitted = mg.getKeyValuePairs(oldSettings, oldVersion, '0.2.8')
            self.assertFalse('fridgeFastFilt' in restored,
                            "Filter settings should be omitted when older than version 0.2.0" +
                             ", failed on version " + oldVersion)
        for oldVersion in ['0.2.0', '0.2.4', '0.3', '1.0']:
            restored, omitted = mg.getKeyValuePairs(oldSettings, oldVersion, '2.0')
            self.assertTrue('fridgeFastFilt' in restored,
                            "Filter settings should be used when restoring from newer than version 0.2.0" +
                            ", failed on version " + oldVersion)

    def testPidMax(self):
        ''' Test if filters are only restored when old version > 0.2.4 It was not outputed correctly earlier'''
        mg = MigrateSettings()
        oldSettings = {'pidMax': 10.0}
        for oldVersion in ['0.1.0', '0.2', '0.2.3']:
            restored, omitted = mg.getKeyValuePairs(oldSettings, oldVersion, '0.2.8')
            self.assertFalse('pidMax' in restored,
                            "pidMax can only be trusted from version 0.2.4 or higher" +
                             ", failed on version " + oldVersion)
        for oldVersion in ['0.2.4', '0.2.5', '0.3', '1.0']:
            restored, omitted = mg.getKeyValuePairs(oldSettings, oldVersion, '2.0')
            self.assertTrue('pidMax' in restored,
                            "pidMax should be restored when restoring form version " + oldVersion)

    def testAllBrewPiSettings(self):
        ''' Test that when restoring from version 0.2.7 to 0.2.7 all settings are migrated'''
        from random import randint

        mg = MigrateSettings()
        oldSettings = dict()
        for setting in mg.restoreValidity:
            oldSettings[setting.key] = randint(0,100) # use random integer for old settings
        restored, omitted = mg.getKeyValuePairs(oldSettings, '0.2.7', '0.2.7')

        self.assertEqual(len(restored), len(oldSettings), "old and new settings should have same nr or items")

        count = 0
        for setting in restored:
            if count == 0:
                self.assertEqual(setting, 'tempFormat', "tempFormat should be restored as first setting")
            self.assertEqual(restored[setting], oldSettings[setting], "old value and restored value do not match")
            count += 1

if __name__ == "__main__":
    unittest.main()
