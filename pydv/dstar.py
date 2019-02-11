# Copyright (C) 2017 Antony Chazapis SV9OAN
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

import struct
import string

from crc import CCITTChecksum
from utils import or_valueerror, pad

class DSTARCallsign(object):
    __slots__ = ['callsign']

    def __init__(self, callsign):
        or_valueerror(len(callsign) > 3)
        or_valueerror(set(callsign[:3]).issubset(string.ascii_letters + string.digits))
        or_valueerror(not callsign[:3].isdigit())
        or_valueerror(set(callsign[3:]).issubset(string.ascii_letters + string.digits + ' '))
        or_valueerror(len(callsign) <= 8)

        self.callsign = callsign.upper()

    def __str__(self):
        return self.callsign.ljust(8)

class DSTARSuffix(object):
    __slots__ = ['suffix']

    def __init__(self, suffix):
        or_valueerror(set(suffix).issubset(string.ascii_letters + string.digits + ' '))
        or_valueerror(len(suffix) <= 4)

        self.suffix = suffix.upper()

    def __str__(self):
        return self.suffix.ljust(4)

class DSTARModule(object):
    __slots__ = ['module']

    def __init__(self, module):
        or_valueerror(len(module) == 1)
        or_valueerror(set(module).issubset(string.ascii_letters + ' '))

        self.module = module.upper()

    def __str__(self):
        return self.module

class DSTARHeader(object):
    __slots__ = ['flag_1',
                 'flag_2',
                 'flag_3',
                 'repeater_1_callsign',
                 'repeater_2_callsign',
                 'ur_callsign',
                 'my_callsign',
                 'my_suffix']

    def __init__(self,
                 flag_1,
                 flag_2,
                 flag_3,
                 repeater_1_callsign,
                 repeater_2_callsign,
                 ur_callsign,
                 my_callsign,
                 my_suffix):
        self.flag_1 = flag_1
        self.flag_2 = flag_2
        self.flag_3 = flag_3
        self.repeater_1_callsign = repeater_1_callsign
        self.repeater_2_callsign = repeater_2_callsign
        self.ur_callsign = ur_callsign
        self.my_callsign = my_callsign
        self.my_suffix = my_suffix

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 41)
        header = data[:39]
        flag_1, \
        flag_2, \
        flag_3, \
        repeater_1_callsign, \
        repeater_2_callsign, \
        ur_callsign, \
        my_callsign, \
        my_suffix = struct.unpack('BBB8s8s8s8s4s', header)
        repeater_1_callsign = DSTARCallsign(repeater_1_callsign)
        repeater_2_callsign = DSTARCallsign(repeater_2_callsign)
        ur_callsign = DSTARCallsign(ur_callsign)
        my_callsign = DSTARCallsign(my_callsign)
        my_suffix = DSTARSuffix(my_suffix)
        # xlxd may rewrite header callsigns, without recomputing the checksum
        # crc = data[39:]
        # checksum = CCITTChecksum()
        # checksum.update(header)
        # or_valueerror(crc == checksum.result())
        return cls(flag_1,
                   flag_2,
                   flag_3,
                   repeater_1_callsign,
                   repeater_2_callsign,
                   ur_callsign,
                   my_callsign,
                   my_suffix)

    def to_data(self):
        header = struct.pack('BBB8s8s8s8s4s', self.flag_1,
                                              self.flag_2,
                                              self.flag_3,
                                              str(self.repeater_1_callsign),
                                              str(self.repeater_2_callsign),
                                              str(self.ur_callsign),
                                              str(self.my_callsign),
                                              str(self.my_suffix))
        checksum = CCITTChecksum()
        checksum.update(header)
        crc = checksum.result()
        return header + crc

class DSTARFrame(object):
    __slots__ = ['dvcodec', 'dvdata']

    def __init__(self, dvcodec, dvdata):
        self.dvcodec = dvcodec
        self.dvdata = dvdata

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 12)
        dvcodec, dvdata = data[:9], data[9:]
        return cls(dvcodec, dvdata)

    def to_data(self):
        return pad(self.dvcodec, 9) + pad(self.dvdata, 3)
