#!/usr/bin/python

# Copyright (C) 2019 Lee C. Bussy (@LBussy)

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

import math


class BrewConvert():
    def convert(self, value, original='plato', target='sg'):
        """
        Dispatch method for brew conversions.

        Conversions commonly used in brewing. Between SG, Plato, and Brix for
        gravity measurements; and F and C for temperatures.

        Parameters:
            value (float):      Value to be converted
            original (string):  Type of measurement being passed (e.g. sg, 
                                plato, brix, f or c)
            target (string):    Type of measurement to return (e.g. sg, 
                                plato, brix, f or c)

        Returns:
            float:  Converted value, or 0 if parameters are invalid
        """
        self.value = value
        self.original = original
        self.target = target

        method_name = 'from_{0}'.format(str(self.original))
        # Concatenate the target method from 'self'
        method = getattr(self, method_name, lambda: 0)
        return method()

    def from_sg(self):
        sg = self.value
        if self.target == 'brix':
            brix = (((182.4601 * sg - 775.6821) * sg + 1262.7794) * sg - 669.5622)
            return brix
        if self.target == 'plato':
            plato = (-1 * 616.868) + (1111.14 * sg) - (630.272 * math.pow(sg, 2)) + (135.997 * math.pow(sg, 3))
            return plato
        if self.target == 'sg':
            return sg
        return 0

    def from_brix(self):
        brix = self.value
        if self.target == 'sg':
            sg = (brix / (258.6-((brix / 258.2) * 227.1))) + 1
            return sg
        if self.target == 'plato':
            plato = brix / 1.04
            return plato
        if self.target == 'brix':
            return brix
        return 0

    def from_plato(self):
        plato = self.value
        if self.target == 'brix':
            brix = plato * 1.04
            return brix
        if self.target == 'sg':
            sg = 1 + (plato / (258.6 - ((plato / 258.2) * 227.1)))
            return sg
        if self.target == 'plato':
            return plato
        return 0

    def from_c(self):
        if self.target == 'f':
            c = self.value
            f = c * 9/5 + 32
            return f
        if self.target == 'c':
            return c
        return 0

    def from_f(self):
        if self.target == 'c':
            f = self.value
            c = (f - 32) * 5/9
            return c
        if self.target == 'f':
            return f
        return 0


def main():
    # Demo of BrewConvert class
    cvt = BrewConvert()
    print('\nBrewConvert() will convert between gravity readings (e.g. SG, Brix and Plato),'
        '\nas well as between F and C.  For example:')
    print('\t{0} SG to Brix = {1}'.format(
        1.040, cvt.convert(1.040, 'sg', 'brix')))
    print('\t{0} SG to Plato = {1}'.format(
        1.040, cvt.convert(1.040, 'sg', 'plato')))
    print('\t{0} Plato to SG = {1}'.format(10, cvt.convert(10, 'plato', 'sg')))
    print('\t{0} Plato to Brix = {1}'.format(
        10, cvt.convert(10, 'plato', 'brix')))
    print('\t{0} Brix to SG = {1}'.format(10, cvt.convert(10, 'brix', 'sg')))
    print('\t{0} Brix to Plato = {1}'.format(
        10, cvt.convert(10, 'brix', 'plato')))
    print('\t{0} C to F = {1}'.format(20, cvt.convert(20, 'c', 'f')))
    print('\t{0} F to C = {1}'.format(68, cvt.convert(68, 'f', 'c')))


if __name__ == '__main__':
    main()
    exit(0)
