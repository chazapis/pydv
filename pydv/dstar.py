# Copyright (C) 2017 by Antony Chazapis SV9OAN
#
# Based on OpenDV:
# Copyright (C) 2006-2013 by Jonathan Naylor G4KLX
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import struct

from crc import CCITTChecksum

RADIO_HEADER_LENGTH_BYTES = 41

LONG_CALLSIGN_LENGTH  = 8
SHORT_CALLSIGN_LENGTH = 4

class DSTARHeader(object):
    def __init__(self,
                 my_call_1='',
                 my_call_2='',
                 your_call='',
                 rpt_call_1='',
                 rpt_call_2='',
                 flag_1=0,
                 flag_2=0,
                 flag_3=0):
        self.my_call_1 = my_call_1
        self.my_call_2 = my_call_2
        self.your_call = your_call
        self.rpt_call_1 = rpt_call_1
        self.rpt_call_2 = rpt_call_2
        self.flag_1 = flag_1
        self.flag_2 = flag_2
        self.flag_3 = flag_3

        self.fmt = 'BBB{lc}s{lc}s{lc}s{lc}s{sc}s'.format(lc=LONG_CALLSIGN_LENGTH,
                                                         sc=SHORT_CALLSIGN_LENGTH)

    def load(data, check=True):
        assert(len(data) >= (RADIO_HEADER_LENGTH_BYTES - (0 if check else 2))

        (self.flag_1,
         self.flag_2,
         self.flag_3,
         self.rpt_call_2,
         self.rpt_call_1,
         self.your_call,
         self.my_call_1,
         self.my_call_2) = struct.unpack(self.fmt, data[:RADIO_HEADER_LENGTH_BYTES - 2]) 

        if check:
            cksum = CCITTChecksum()
            cksum.update(data[:RADIO_HEADER_LENGTH_BYTES - 2])
            if not cksum.check(data[RADIO_HEADER_LENGTH_BYTES - 2:RADIO_HEADER_LENGTH_BYTES])
                raise ValueError

    def dump(check=True):
        data = struct.pack(self.fmt, self.flag_1,
                                     self.flag_2,
                                     self.flag_3,
                                     self.rpt_call_2,
                                     self.rpt_call_1,
                                     self.your_call,
                                     self.my_call_1,
                                     self.my_call_2)

        if check:
            cksum = CCITTChecksum()
            cksum.update(data)
            data += cksum.result()

        return data
