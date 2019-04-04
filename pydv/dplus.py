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

from dstar import DSTARCallsign
from stream import Packet, FixedPacket, DVHeaderPacket, DVFramePacket, StreamReceiveThread, ReflectorConnection
from utils import or_valueerror, pad

class DPlusConnectPacket(FixedPacket):
    data = '\x05\x00\x18\x00\x01'

class DPlusLoginPacket(Packet):
    __slots__ = ['callsign', 'serial']

    def __init__(self, callsign, serial):
        self.callsign = callsign
        # dxrfd suggests uses "serial" to identify peer types.
        # Hotspots send "DV019999", DVAPs "AP", while everything
        # else is considered a "dongle".
        self.serial = serial

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 28)
        login, callsign, _, serial = struct.unpack('4s8s8s8s', data[4:])
        or_valueerror(login == '\x1c\xc0\x04\x00')
        callsign = DSTARCallsign(callsign)
        return cls(callsign, serial)

    def to_data(self):
        return struct.pack('4s8s8s8s', '\x1c\xc0\x04\x00',
                                       str(self.callsign),
                                       '\x00\x00\x00\x00\x00\x00\x00\x00',
                                       pad(self.serial, 8))

class DPlusLoginOKPacket(FixedPacket):
    data = '\x08\xc0\x04\x00OKRW'

class DPlusLoginBusyPacket(FixedPacket):
    data = '\x08\xc0\x04\x00BUSY'

class DPlusLoginFailPacket(FixedPacket):
    data = '\x08\xc0\x04\x00FAIL'

class DPlusDisconnectPacket(FixedPacket):
    data = '\x05\x00\x18\x00\x00'

class DPlusKeepAlivePacket(FixedPacket):
    data = '\x03\x60\x00'

class DPlusHeaderPacket(Packet):
    __slots__ = ['dv_header']

    def __init__(self, dv_header):
        self.dv_header = dv_header

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 58)
        or_valueerror(data[:2] == '\x3a\x80')
        dv_header = DVHeaderPacket.from_data(data[2:])
        return cls(dv_header)

    def to_data(self):
        return '\x3a\x80' + self.dv_header.to_data()

class DPlusFramePacket(Packet):
    __slots__ = ['dv_frame']

    def __init__(self, dv_frame):
        self.dv_frame = dv_frame

    @classmethod
    def from_data(cls, data):
        if len(data) == 29:
            or_valueerror(data[:2] == '\x1d\x80')
            dv_frame = DVFramePacket.from_data(data[2:])
            return cls(dv_frame)
        elif len(data) == 32:
            or_valueerror(data[:2] == '\x20\x80')
            dv_frame = DVFramePacket.from_data(data[2:29])
            if not dv_frame.is_last:
                dv_frame.packet_id |= 64
            return cls(dv_frame)
        else:
            raise ValueError

    def to_data(self):
        if not self.dv_frame.is_last:
            return '\x1d\x80' + self.dv_frame.to_data()

        data = '\x20\x80' + \
               self.dv_frame.to_data()[:15] + \
               '\x55\xc8\x7a\x55\x55\x55\x55\x55\x55\x55\x55\x55\x25\x1a\xc6' # XXX Why?
        return data[:8] + '\x81' + data[9:]

class DPlusConnectionRecieveThread(StreamReceiveThread):
    def _process(self, data):
        try:
            packet = DPlusFramePacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received dvframe packet from stream %s%s', packet.dv_frame.stream_id, ' (last)' if packet.dv_frame.is_last else '')
            return packet

        try:
            packet = DPlusHeaderPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received dvheader packet from stream %s', packet.dv_header.stream_id)
            return packet

        try:
            packet = DPlusConnectPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received connect packet')
            return packet

        try:
            packet = DPlusLoginOKPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received login ok packet')
            return packet

        try:
            packet = DPlusLoginBusyPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received login busy packet')
            return packet

        try:
            packet = DPlusLoginFailPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received login fail packet')
            return packet

        try:
            packet = DPlusDisconnectPacket.from_data(data)
        except ValueError:
            pass
        else:
            self.logger.debug('received disconnect packet')
            return packet # XXX Request or reply?

        try:
            packet = DPlusKeepAlivePacket.from_data(data)
        except ValueError:
            pass
        else:
            # self.logger.debug('received keepalive packet')
            keepalive_packet = DPlusKeepAlivePacket()
            self.sock.write(keepalive_packet.to_data())
            return

        self.logger.warning('unknown data received')

class DPlusConnection(ReflectorConnection):
    DEFAULT_PORT = 20001

    def __init__(self, callsign, module, reflector_callsign, reflector_module, reflector_address):
        ReflectorConnection.__init__(self, callsign, module, reflector_callsign, reflector_module, reflector_address)
        self.receive_thread = DPlusConnectionRecieveThread(self.sock)

    def _connect(self, timeout=3):
        self.write(DPlusConnectPacket())
        packet = self._read(timeout, [DPlusConnectPacket])
        if not packet:
            return False

        self.write(DPlusLoginPacket(self.callsign, ''))
        packet = self._read(timeout, [DPlusLoginOKPacket, DPlusLoginBusyPacket, DPlusLoginFailPacket])
        if packet and isinstance(packet, DPlusLoginOKPacket):
            return True
        return False

    def _disconnect(self, timeout=3):
        self.write(DPlusDisconnectPacket())
        return True if self._read(timeout, [DPlusDisconnectPacket]) else False

    def read(self, timeout=3):
        packet = self._read(timeout, [DPlusHeaderPacket, DPlusFramePacket])
        if not packet:
            return None
        if isinstance(packet, DPlusHeaderPacket):
            return packet.dv_header
        if isinstance(packet, DPlusFramePacket):
            return packet.dv_frame

    def write(self, packet):
        if isinstance(packet, DVHeaderPacket):
            packet = DPlusHeaderPacket(packet)
        elif isinstance(packet, DVFramePacket):
            packet = DPlusFramePacket(packet)
        return self.sock.write(packet.to_data())
