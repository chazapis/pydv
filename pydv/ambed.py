# Copyright (C) 2019 Antony Chazapis SV9OAN
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

from dstar import DSTARCallsign
from stream import Packet, FixedPacket, StreamReceiveThread, StreamConnection
from utils import or_valueerror

class AMBEdOpenStreamPacket(Packet):
    __slots__ = ['callsign', 'codec_in', 'codecs_out']

    def __init__(self, callsign, codec_in, codecs_out):
        self.callsign = callsign
        self.codec_in = codec_in
        self.codecs_out = codecs_out

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 17)
        open_stream, callsign, codec_in, codecs_out = struct.unpack('7s8sBB', data)
        or_valueerror(open_stream == 'AMBEDOS')
        callsign = DSTARCallsign(callsign)
        return cls(callsign, codec_in, codecs_out)

    def to_data(self):
        return struct.pack('7s8sBB', 'AMBEDOS',
                                     str(self.callsign),
                                     self.codec_in,
                                     self.codecs_out)

class AMBEdStreamDescriptorPacket(Packet):
    __slots__ = ['stream_id', 'port', 'codec_in', 'codecs_out']

    def __init__(self, stream_id, port, codec_in, codecs_out):
        self.stream_id = stream_id
        self.port = port
        self.codec_in = codec_in
        self.codecs_out = codecs_out

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 14)
        stream_descriptor, stream_id, port, codec_in, codecs_out = struct.unpack('<8sHHBB', data)
        or_valueerror(stream_descriptor == 'AMBEDSTD')
        return cls(stream_id, port, codec_in, codecs_out)

    def to_data(self):
        return struct.pack('<8sHHBB', 'AMBEDSTD',
                                      self.stream_id,
                                      self.port,
                                      self.codec_in,
                                      self.codecs_out)

class AMBEdBusyPacket(FixedPacket):
    data = 'AMBEDBUSY'

class AMBEdCloseStreamPacket(Packet):
    __slots__ = ['stream_id']

    def __init__(self, stream_id):
        self.stream_id = stream_id

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 9)
        close_stream, stream_id = struct.unpack('<7sH', data)
        or_valueerror(close_stream == 'AMBEDCS')
        return cls(stream_id)

    def to_data(self):
        return struct.pack('<7sH', 'AMBEDCS', self.stream_id)

class AMBEdPingPacket(Packet):
    __slots__ = ['callsign']

    def __init__(self, callsign):
        self.callsign = callsign

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 17)
        ping, callsign = struct.unpack('9s8s', data)
        or_valueerror(ping == 'AMBEDPING')
        callsign = DSTARCallsign(callsign)
        return cls(callsign)

    def to_data(self):
        return struct.pack('9s8s', 'AMBEDPING', str(self.callsign))

class AMBEdPongPacket(FixedPacket):
    data = 'AMBEDPONG'

class AMBEdConnectionRecieveThread(StreamReceiveThread):
    def __init__(self, sock, callsign):
        StreamReceiveThread.__init__(self, sock)
        self.callsign = callsign

    def _process(self, data):
        try:
            packet = AMBEdStreamDescriptorPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received stream descriptor packet')
            return packet

        try:
            packet = AMBEdBusyPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received busy packet')
            return packet

        try:
            packet = AMBEdPongPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received keepalive packet')
            return packet

        self.logger.warning('unknown data received')

    def loop(self):
        # XXX Send keepalives and notify if not connected...
        # ping_packet = AMBEdPingPacket(self.callsign)
        # self.sock.write(ping_packet.to_data())

        StreamReceiveThread.loop(self)

class AMBEdConnection(StreamConnection):
    DEFAULT_PORT = 10100

    def __init__(self, callsign, address, codec_in, codecs_out):
        StreamConnection.__init__(self, callsign, address)
        self.receive_thread = AMBEdConnectionRecieveThread(self.sock, self.callsign)
        self.codec_in = codec_in
        self.codecs_out = codecs_out

    def _connect(self, timeout=3):
        self.write(AMBEdOpenStreamPacket(self.callsign, self.codec_in, self.codecs_out))
        packet = self._read(timeout, [AMBEdStreamDescriptorPacket, AMBEdBusyPacket])
        if packet and isinstance(packet, AMBEdStreamDescriptorPacket):
            # XXX Create stream...
            return True
        return False

    def _disconnect(self, timeout=3):
        # XXX Get stream id...
        # self.write(AMBEdCloseStreamPacket(self.stream.stream_id))
        return True
