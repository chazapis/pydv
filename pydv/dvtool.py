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

import logging
import struct

from stream import DVHeaderPacket, DVFramePacket
from utils import or_valueerror

class DVToolFile(object):
    def __init__(self, name):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with name %s', name)

        self.name = name
        self.f = None

    def open(self):
        or_valueerror(self.f is None)
        try:
            self.f = open(self.name, 'a+b')
        except Exception as e:
            self.logger.error('can not open file: %s', str(e))
            return False
        self.logger.debug('opened file %s', self.name)
        return True

    def close(self):
        if self.f:
            self.f.close()
        self.f = None
        self.logger.debug('closed file %s', self.name)

    def __enter__(self):
        if not self.open():
            raise Exception('can not open file %s' % self.name)
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def write(self, stream):
        self.f.seek(0)
        self.f.truncate()

        self.f.write('DVTOOL' + struct.pack('<I', len(stream)))
        for i, packet in enumerate(stream):
            self.f.write(struct.pack('<H', 56 if i == 0 else 27) + packet.to_data())
        self.logger.info('wrote a stream of %s packets in %s', len(stream), self.name)

    def read(self):
        self.f.seek(0)

        stream = []
        magic, count = struct.unpack('<6sI', self.f.read(10))
        or_valueerror(magic == 'DVTOOL')
        for i in xrange(count):
            size, = struct.unpack('<H', self.f.read(2))
            data = self.f.read(size)
            if i == 0:
                or_valueerror(size == 56)
                packet = DVHeaderPacket.from_data(data)
            else:
                or_valueerror(size == 27)
                packet = DVFramePacket.from_data(data)
            stream.append(packet)
        self.logger.info('read a stream of %s packets from %s', len(stream), self.name)
        return stream
