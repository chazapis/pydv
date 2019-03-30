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

from dstar import DSTARHeader, DSTARFrame
from network import UDPClientSocket
from utils import or_valueerror, StoppableThread

class Packet(object): # Abstract
    __slots__ = ['data']

    def __init__(self, data):
        self.data = data

    @classmethod
    def from_data(cls, data):
        return cls(data)

    def to_data(self):
        return self.data

class FixedPacket(Packet):
    __slots__ = []

    def __init__(self):
        pass

    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == len(cls.data))
        or_valueerror(data == cls.data)
        return cls()

    def to_data(self):
        return self.__class__.data

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

class DisconnectedError(Exception):
    pass

class StreamReceiveThread(StoppableThread):
    def __init__(self, sock):
        self.logger = logging.getLogger(self.__class__.__name__)

        StoppableThread.__init__(self, name=self.__class__.__name__)
        self._sleep_period = 0.01

        self.sock = sock
        self.queue = Queue.Queue()

    def _process(self, data): # Abstract
        if not data:
            raise DisconnectedError
        return Packet.from_data(data)

    def loop(self):
        while True: # While there is data to read from the socket
            data = self.sock.read()
            if not data:
                return

            try:
                packet = self._process(data)
                if packet:
                    self.queue.put(packet)
            except DisconnectedError:
                self.queue.put(None)

class StreamConnection(object):
    def __init__(self, address):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with address %s', address)

        self.address = address

        self.sock = UDPClientSocket(self.address)
        self.receive_thread = StreamReceiveThread(self.sock)
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
                if expected_packet_classes is None:
                    return packet
                for cls in expected_packet_classes:
                    if isinstance(packet, cls):
                        return packet
            except Queue.Empty:
                pass
            clock = time.time()
        return None

    def _connect(self):
        return True

    def _disconnect(self):
        return True

    def open(self):
        try:
            self.sock.open()
        except Exception as e:
            self.logger.error('can not open UDP socket: %s', str(e))
            return False
        self.logger.info('connected to %s', self.address)

        self.receive_thread.start()
        self.disconnected = False

        return self._connect()

    def close(self):
        while not self.receive_thread.queue.empty():
            self.receive_thread.queue.get()

        if not self.disconnected:
            self._disconnect()

        self.receive_thread.join()

        self.sock.close()
        self.logger.info('disconnected from %s', self.address)

    def __enter__(self):
        if not self.open():
            raise Exception('can not open connection to %s' % (self.address,))
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def read(self, timeout=3):
        return self._read(timeout)

    def write(self, packet):
        return self.sock.write(packet.to_data())

class ReflectorConnection(StreamConnection):
    def __init__(self, callsign, module, reflector_callsign, reflector_module, reflector_address):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with callsign %s module %s reflector callsign %s reflector_module %s reflector_address %s', callsign, module, reflector_callsign, reflector_module, reflector_address)

        StreamConnection.__init__(self, reflector_address)
        self.callsign = callsign
        self.module = module
        self.reflector_callsign = reflector_callsign
        self.reflector_module = reflector_module

    def read(self, timeout=3):
        return self._read(timeout, [DVHeaderPacket, DVFramePacket])
