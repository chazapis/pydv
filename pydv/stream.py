# Copyright (C) 2018 Antony Chazapis SV9OAN
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

from dstar import DSTARHeader, DSTARFrame
from utils import or_valueerror

class Packet(object):
    pass

class DVHeaderPacket(Packet):
    __slots__ = ['band_1', 'band_2', 'band_3', 'stream_id', 'dstar_header']

    def __init__(self, band_1, band_2, band_3, stream_id, dstar_header):
        self.band_1 = band_1
        self.band_2 = band_2
        self.band_3 = band_3
        self.stream_id = stream_id
        self.dstar_header = dstar_header

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 56)
        or_valueerror(data[:4] == 'DSVT')
        or_valueerror(data[4] == '\x10')
        or_valueerror(data[8] == '\x20')
        band_1, band_2, band_3, stream_id = struct.unpack('<BBBH', data[9:14])
        dstar_header = DSTARHeader.from_data(data[15:])
        return cls(band_1, band_2, band_3, stream_id, dstar_header)

    def to_data(self):
        return ('DSVT\x10\x00\x00\x00\x20' +
                struct.pack('<BBBH', self.band_1, self.band_2, self.band_3, self.stream_id) +
                '\x80' +
                self.dstar_header.to_data())

class DVFramePacket(Packet):
    __slots__ = ['band_1', 'band_2', 'band_3', 'stream_id', 'packet_id', 'dstar_frame']

    def __init__(self, band_1, band_2, band_3, stream_id, packet_id, dstar_frame):
        self.band_1 = band_1
        self.band_2 = band_2
        self.band_3 = band_3
        self.stream_id = stream_id
        self.packet_id = packet_id
        self.dstar_frame = dstar_frame

    @property
    def is_last(self):
        return self.packet_id & 64 != 0

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 27)
        or_valueerror(data[:4] == 'DSVT')
        or_valueerror(data[4] == '\x20')
        or_valueerror(data[8] == '\x20')
        band_1, band_2, band_3, stream_id, packet_id = struct.unpack('<BBBHB', data[9:15])
        dstar_frame = DSTARFrame.from_data(data[15:])
        return cls(band_1, band_2, band_3, stream_id, packet_id, dstar_frame)

    def to_data(self):
        return ('DSVT\x20\x00\x00\x00\x20' +
                struct.pack('<BBBHB', self.band_1, self.band_2, self.band_3, self.stream_id, self.packet_id) +
                self.dstar_frame.to_data())
