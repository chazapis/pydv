# Copyright (C) 2017 by Antony Chazapis SV9OAN
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

import random

from dstar import DSTARHeader
from network import NetworkAddress, UDPClientSocket

class DExtraHeader(DSTARHeader):
    def __init__(self,
                 my_call_1='',
                 my_call_2='',
                 your_call='',
                 rpt_call_1='',
                 rpt_call_2='',
                 flag_1=0,
                 flag_2=0,
                 flag_3=0,
                 band_1=0,
                 band_2=0,
                 band_3=0,
                 unique_id=None):
        super(DExtraHeader, self).__init__(my_call_1,
                                           my_call_2,
                                           your_call,
                                           rpt_call_1,
                                           rpt_call_2,
                                           flag_1,
                                           flag_2,
                                           flag_3)
        self.band_1 = band_1
        self.band_2 = band_2
        self.band_3 = band_3
        self.unique_id = unique_id if unique_id is not None else random.randint(1, 0xffff)

    def load(data, check=True):
        assert(len(data) >= 56)

        (self.band_1,
         self.band_2,
         self.band_3,
         self.unique_id) = struct.unpack('9xBBB<Hx', data[:15])
        super(DExtraHeader, self).load(data[15:], check)

    def dump(check=True):
        data = 'DSVT\x10\x00\x00\x00\x20'
        data += struct.pack('BBB<H', self.band_1,
                                     self.band_2,
                                     self.band_3,
                                     self.unique_id)
        data += '\x80'
        data += super(DExtraHeader, self).dump(check)

        return data

class DExtraConnection(object):
    def __init__(self, address, port, callsign):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with (\'%s\', %d)', address, port)

        self.address = address
        self.port = port
        self.callsign = callsign

        self.sock = None

    def open(self):
        assert(self.sock is None)

        try:
            self.sock = UDPClientSocket(address, port)
            self.sock.open()
        except Exception as e:
            self.logger.error('can not open UDP socket: %s', str(e))
            self.sock = None
            return False

        return True

    def close(self):
        assert(self.sock)

        try:
            self.sock.close()
        except:
            pass
        self.sock = None
