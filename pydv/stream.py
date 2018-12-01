# Copyright (C) 2018 by Antony Chazapis SV9OAN
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

from utils import or_valueerror

class Packet(object):
    pass

class DVHeaderPacket(Packet):
    __slots__ = ['stream_id', 'dstar_header']

    def __init__(self, stream_id, dstar_header):
        self.stream_id = stream_id
        self.dstar_header = dstar_header

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 56)
        or_valueerror(data[:4] == 'DSVT')
        or_valueerror(data[4] == '\x10')
        or_valueerror(data[8] == '\x20')
        stream_id, = struct.unpack('<H', data[12:14])
        return cls(stream_id, data[15:])

    def to_data(self):
        # XXX ON1ARF in "Format of files and UDP-streams used on D-STAR"
        # says the 12th byte should be \x01, while LX3JL uses \x02 in xlxd
        return ('DSVT\x10\x00\x00\x00\x20\x00\x01\x02' +
                struct.pack('<H', self.stream_id) +
                '\x80' +
                self.dstar_header)

class DVFramePacket(Packet):
    __slots__ = ['stream_id', 'packet_id', 'is_last', 'dstar_frame']

    def __init__(self, stream_id, packet_id, is_last, dstar_frame):
        self.stream_id = stream_id
        self.packet_id = packet_id
        self.is_last = is_last
        self.dstar_frame = dstar_frame

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 27)
        or_valueerror(data[:4] == 'DSVT')
        or_valueerror(data[4] == '\x20')
        or_valueerror(data[8] == '\x20')
        stream_id, packet_id = struct.unpack('<HB', data[12:15])
        is_last = (packet_id & 64 != 0)
        return cls(stream_id, packet_id, is_last, data[15:])

    def to_data(self):
        # XXX Same as above for 12th byte
        return ('DSVT\x20\x00\x00\x00\x20\x00\x01\x02' +
                struct.pack('<HB', self.stream_id, self.packet_id % 21) +
                self.dstar_frame)
