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

from dstar import DSTARCallsign, DSTARModule
from stream import Packet, FixedPacket, DVHeaderPacket, DVFramePacket, DisconnectedError, StreamReceiveThread, ReflectorConnection
from utils import or_valueerror

class DExtraConnectPacket(Packet):
    __slots__ = ['src_callsign', 'src_module', 'dest_module', 'revision']

    def __init__(self, src_callsign, src_module, dest_module, revision):
        self.src_callsign = src_callsign
        self.src_module = src_module
        self.dest_module = dest_module
        self.revision = revision

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 11)
        src_callsign, src_module, dest_module, src_revision = struct.unpack('8sccB', data)
        src_callsign = DSTARCallsign(src_callsign)
        src_module = DSTARModule(src_module)
        dest_module = DSTARModule(dest_module)
        or_valueerror(str(dest_module) != ' ')
        if src_revision == 11:
            revision = 1
        elif (str(src_callsign).startswith('XRF')):
            revision = 2
        else:
            revision = 0
        return cls(src_callsign, src_module, dest_module, revision)

    def to_data(self):
        return struct.pack('8sccB', str(self.src_callsign),
                                    str(self.src_module),
                                    str(self.dest_module),
                                    11 if self.revision == 1 else 0) # XXX What about revisions 0 and 2?

class DExtraConnectAckPacket(Packet):
    __slots__ = ['src_callsign', 'src_module', 'dest_module', 'revision']

    def __init__(self, src_callsign, src_module, dest_module, revision):
        self.src_callsign = src_callsign
        self.src_module = src_module
        self.dest_module = dest_module
        self.revision = revision

    @classmethod
    def from_data(cls, data):
        # Same size with disconnect
        # if (len(data) == 11):
        #     raise NotImplementedError

        or_valueerror(len(data) == 14)
        src_callsign, src_module, dest_module, ack = struct.unpack('8scc4s', data)
        src_callsign = DSTARCallsign(src_callsign)
        src_module = DSTARModule(src_module)
        dest_module = DSTARModule(dest_module)
        or_valueerror(str(dest_module) != ' ')
        or_valueerror(ack == 'ACK\x00')
        return cls(src_callsign, src_module, dest_module, 1) # XXX Could it be revision 0?

    @classmethod
    def from_connect_packet(cls, connect_packet):
        return cls(connect_packet.src_callsign,
                   connect_packet.src_module,
                   connect_packet.dest_module,
                   connect_packet.revision)

    def to_data(self):
        if self.revision == 2:
            return struct.pack('8sccB', str(self.src_callsign),
                                        str(self.dest_module),
                                        str(self.src_module),
                                        0)

        return struct.pack('8scc4s', str(self.src_callsign),
                                     str(self.src_module),
                                     str(self.dest_module),
                                     'ACK\x00')

class DExtraConnectNackPacket(Packet):
    __slots__ = ['src_callsign', 'src_module', 'dest_module']

    def __init__(self, src_callsign, src_module, dest_module):
        self.src_callsign = src_callsign
        self.src_callsign = src_module
        self.dest_module = dest_module

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 14)
        src_callsign, src_module, dest_module, nack = struct.unpack('8scc4s', data)
        src_callsign = DSTARCallsign(src_callsign)
        src_module = DSTARModule(src_module)
        dest_module = DSTARModule(dest_module)
        or_valueerror(str(dest_module) != ' ')
        or_valueerror(nack == 'NAK\x00')
        return cls(src_callsign, src_module, dest_module)

    @classmethod
    def from_connect_packet(cls, connect_packet):
        return cls(connect_packet.src_callsign,
                   connect_packet.src_module,
                   connect_packet.dest_module)

    def to_data(self):
        return struct.pack('8scc4s', str(self.src_callsign),
                                     str(self.src_module),
                                     str(self.dest_module),
                                     'NAK\x00')

class DExtraDisconnectPacket(Packet):
    __slots__ = ['src_callsign', 'src_module']

    def __init__(self, src_callsign, src_module):
        self.src_callsign = src_callsign
        self.src_module = src_module

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 11)
        src_callsign, src_module, dest_module, _ = struct.unpack('8sccB', data)
        src_callsign = DSTARCallsign(src_callsign)
        src_module = DSTARModule(src_module)
        dest_module = DSTARModule(dest_module)
        or_valueerror(str(dest_module) == ' ')
        return cls(src_callsign, src_module)

    def to_data(self):
        return struct.pack('8sc2s', str(self.src_callsign),
                                    str(self.src_module),
                                    '  ')

class DExtraDisconnectAckPacket(FixedPacket):
    data = 'DISCONNECTED'

class DExtraKeepAlivePacket(Packet):
    __slots__ = ['src_callsign']

    def __init__(self, src_callsign):
        self.src_callsign = src_callsign

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 9)
        src_callsign, _ = struct.unpack('8sc', data)
        src_callsign = DSTARCallsign(src_callsign)
        return cls(src_callsign) # XXX Get module?

    def to_data(self):
        return str(self.src_callsign) + '\x00' # XXX Send module?

class DExtraConnectionRecieveThread(StreamReceiveThread):
    def __init__(self, sock, callsign):
        StreamReceiveThread.__init__(self, sock)
        self.callsign = callsign

    def _process(self, data):
        try:
            packet = DVFramePacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received dvframe packet from stream %s%s', packet.stream_id, ' (last)' if packet.is_last else '')
            return packet

        try:
            packet = DVHeaderPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received dvheader packet from stream %s', packet.stream_id)
            return packet

        try:
            packet = DExtraConnectAckPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received connect ack packet')
            return packet

        try:
            packet = DExtraConnectNackPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received connect nack packet')
            return packet

        try:
            packet = DExtraDisconnectPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received disconnect packet from %s', packet.src_callsign)
            raise DisconnectedError

        try:
            packet = DExtraDisconnectAckPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received disconnect ack packet')
            return packet

        try:
            packet = DExtraKeepAlivePacket.from_data(data)
        except ValueError:
            pass
        else:
            # self.logger.debug('received keepalive packet from %s', packet.src_callsign)
            keepalive_packet = DExtraKeepAlivePacket(self.callsign)
            self.sock.write(keepalive_packet.to_data())
            return

        self.logger.warning('unknown data received')

class DExtraConnection(ReflectorConnection):
    DEFAULT_PORT = 30001

    def __init__(self, callsign, module, reflector_callsign, reflector_module, reflector_address):
        ReflectorConnection.__init__(self, callsign, module, reflector_callsign, reflector_module, reflector_address)
        self.receive_thread = DExtraConnectionRecieveThread(self.sock, self.callsign)

    def _connect(self, timeout=3):
        self.write(DExtraConnectPacket(self.callsign, self.module, self.reflector_module, 1))
        packet = self._read(timeout, [DExtraConnectAckPacket, DExtraConnectNackPacket])
        if packet and isinstance(packet, DExtraConnectAckPacket):
            return True
        return False

    def _disconnect(self, timeout=3):
        self.write(DExtraDisconnectPacket(self.callsign, self.module))
        return True if self._read(timeout, [DExtraDisconnectAckPacket]) else False

class DExtraOpenConnection(DExtraConnection):
    DEFAULT_PORT = 30201
