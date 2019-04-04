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

import logging
import struct

from dstar import DSTARCallsign
from stream import Packet, FixedPacket, StreamReceiveThread, StreamConnection
from network import NetworkAddress
from utils import or_valueerror

# No Enum available in Python 2.7
class AMBEdCodec:
    NONE = 0
    AMBEPLUS = 1
    AMBE2PLUS = 2
    CODEC2_3200 = 4
    CODEC2_2400 = 8

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

class AMBEdFrameInPacket(Packet):
    __slots__ = ['packet_id', 'codec', 'data']

    def __init__(self, packet_id, codec, data):
        self.packet_id = packet_id
        self.codec = codec
        self.data = data

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 11)
        codec, packet_id, data = struct.unpack('BB9s', data)
        return cls(packet_id, codec, data)

    def to_data(self):
        return struct.pack('BB9s', self.codec,
                                   self.packet_id,
                                   self.data)

class AMBEdFrameOutPacket(Packet):
    __slots__ = ['packet_id', 'codec1', 'codec2', 'data1', 'data2']

    def __init__(self, packet_id, codec1, codec2, data1, data2):
        self.packet_id = packet_id
        self.codec1 = codec1
        self.codec2 = codec2
        self.data1 = data1
        self.data2 = data2

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 21)
        codec1, codec2, packet_id, data1, data2 = struct.unpack('BBB9s9s', data)
        return cls(packet_id, codec1, codec2, data1, data2)

    def to_data(self):
        return struct.pack('BBB9s9s', self.codec1,
                                      self.codec2,
                                      self.packet_id,
                                      self.data1,
                                      self.data2)

class AMBEdStreamRecieveThread(StreamReceiveThread):
    def _process(self, data):
        try:
            packet = AMBEdFrameOutPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received frame out packet')
            return packet

        self.logger.warning('unknown data received')

class AMBEdStream(StreamConnection):
    def __init__(self, connection, stream_id, codec_in, codecs_out, address):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with connection %s stream_id %s codec_in %s codecs_out %s address %s', connection, stream_id, codec_in, codecs_out, address)

        StreamConnection.__init__(self, address)
        self.connection = connection
        self.stream_id = stream_id
        self.codec_in = codec_in
        self.codecs_out = codecs_out
        self.receive_thread = AMBEdStreamRecieveThread(self.sock)

    def _disconnect(self, timeout=3):
        self.connection.write(AMBEdCloseStreamPacket(self.stream_id))
        return True

    def read(self, timeout=3):
        return self._read(timeout, [AMBEdFrameOutPacket])

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

class AMBEdConnection(StreamConnection):
    DEFAULT_PORT = 10100

    def __init__(self, callsign, address):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with callsign %s address %s', callsign, address)

        StreamConnection.__init__(self, address)
        self.callsign = callsign
        self.receive_thread = AMBEdConnectionRecieveThread(self.sock, self.callsign)

        self.codecs_out_map = {AMBEdCodec.AMBEPLUS: AMBEdCodec.AMBE2PLUS | AMBEdCodec.CODEC2_3200,
                               AMBEdCodec.AMBE2PLUS: AMBEdCodec.AMBEPLUS | AMBEdCodec.CODEC2_3200,
                               AMBEdCodec.CODEC2_3200: AMBEdCodec.AMBEPLUS | AMBEdCodec.AMBE2PLUS,
                               AMBEdCodec.CODEC2_2400: AMBEdCodec.AMBEPLUS | AMBEdCodec.AMBE2PLUS}

    def _connect(self, timeout=3):
        # Just do a ping to see that we actually have a connection
        # self.write(AMBEdPingPacket(self.callsign))
        # packet = self._read(timeout, [AMBEdPongPacket])
        # if packet:
        #     return True
        # return False
        return True

    def get_stream(self, codec_in, timeout=3):
        codecs_out = self.codecs_out_map[codec_in]
        self.write(AMBEdOpenStreamPacket(self.callsign, codec_in, codecs_out))
        packet = self._read(timeout, [AMBEdStreamDescriptorPacket, AMBEdBusyPacket])
        if packet and isinstance(packet, AMBEdStreamDescriptorPacket):
            return AMBEdStream(self,
                               packet.stream_id,
                               codec_in,
                               codecs_out,
                               NetworkAddress(self.address.host, packet.port))
        return None
