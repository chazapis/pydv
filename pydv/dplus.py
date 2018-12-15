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
import time
import Queue

from dstar import DSTARCallsign, DSTARModule
from stream import Connection, DisconnectedError, Packet, FixedPacket, DVHeaderPacket, DVFramePacket
from network import UDPClientSocket
from utils import or_valueerror, pad, StoppableThread

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

class DPlusReceiveThread(StoppableThread):
    def __init__(self, sock, name='DPlusReceiveThread'):
        self.logger = logging.getLogger(self.__class__.__name__)

        StoppableThread.__init__(self, name=name)
        self._sleep_period = 0.01

        self.sock = sock
        self.queue = Queue.Queue()

    def loop(self):
        while True: # While there is data to read from the socket
            data = self.sock.read()
            if not data:
                return

            try:
                packet = DPlusFramePacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received dvframe packet from stream %s%s', packet.dv_frame.stream_id, ' (last)' if packet.dv_frame.is_last else '')
                self.queue.put(packet)
                continue

            try:
                packet = DPlusHeaderPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received dvheader packet from stream %s', packet.dv_header.stream_id)
                self.queue.put(packet)
                continue

            try:
                packet = DPlusConnectPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received connect packet')
                self.queue.put(packet)
                continue

            try:
                packet = DPlusLoginOKPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received login ok packet')
                self.queue.put(packet)
                continue

            try:
                packet = DPlusLoginBusyPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received login busy packet')
                self.queue.put(packet)
                continue

            try:
                packet = DPlusLoginFailPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received login fail packet')
                self.queue.put(packet)
                continue

            try:
                packet = DPlusDisconnectPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received disconnect packet')
                self.queue.put(packet) # XXX Request or reply?
                continue

            try:
                packet = DPlusKeepAlivePacket.from_data(data)
            except ValueError:
                pass
            else:
                # self.logger.debug('received keepalive packet')
                keepalive_packet = DPlusKeepAlivePacket()
                self.sock.write(keepalive_packet.to_data())
                continue

            self.logger.warning('unknown data received')

class DPlusConnection(Connection):
    DEFAULT_PORT = 20001

    def __init__(self, callsign, module, reflector_callsign, reflector_module, reflector_address):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with callsign %s module %s reflector callsign %s reflector_module %s reflector_address %s', callsign, module, reflector_callsign, reflector_module, reflector_address)

        self.callsign = callsign
        self.module = module
        self.reflector_callsign = reflector_callsign
        self.reflector_module = reflector_module
        self.reflector_address = reflector_address

        self.sock = None
        self.receive_thread = None
        self.disconnected = False

    def _read(self, timeout=3, expected_packet_classes=None):
        step = 0.01
        clock = time.time()
        limit = clock + timeout
        while (clock < limit):
            try:
                packet = self.receive_thread.queue.get(True, step)
                if not packet:
                    self.disconnected = True
                    raise DisconnectedError
                if expected_packets == None:
                    return packet
                for cls in expected_packet_classes:
                    if isinstance(packet, cls):
                        return packet
            except Queue.Empty:
                pass
            clock = time.time()
        return None

    def _connect(self, timeout=3):
        self.write(DPlusConnectPacket())
        return True if self._read(timeout, [DPlusConnectPacket]) else False

    def _login(self, timeout=3):
        self.write(DPlusLoginPacket(self.callsign, ''))
        packet = self._read(timeout, [DPlusLoginOKPacket, DPlusLoginBusyPacket, DPlusLoginFailPacket])
        if packet and isinstance(packet, DPlusLoginOKPacket):
            return True
        return False

    def _disconnect(self, timeout=3):
        self.write(DPlusDisconnectPacket())
        return True if self._read(timeout, [DPlusDisconnectPacket]) else False

    def open(self):
        or_valueerror(self.sock is None)

        try:
            self.sock = UDPClientSocket(self.reflector_address)
            self.sock.open()
        except Exception as e:
            self.logger.error('can not open UDP socket: %s', str(e))
            self.sock = None
            return False
        self.logger.info('connected to reflector %s at address %s', self.reflector_callsign, self.reflector_address)

        self.receive_thread = DPlusReceiveThread(self.sock)
        self.receive_thread.start()
        self.disconnected = False

        return (self._connect() and self._login())

    def close(self):
        while not self.receive_thread.queue.empty():
            self.receive_thread.queue.get()

        if not self.disconnected:
            self._disconnect()

        self.receive_thread.join()

        if self.sock:
            self.sock.close()
        self.sock = None
        self.logger.info('disconnected from reflector %s at address %s', self.reflector_callsign, self.reflector_address)

    def __enter__(self):
        if not self.open():
            raise Exception('can not open DPlus connection to %s' % (self.reflector_address,))
        return self

    def __exit__(self, type, value, traceback):
        self.close()

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
