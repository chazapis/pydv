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

import logging
import struct
import time
import Queue

from dstar import DSTARCallsign, DSTARModule
from network import NetworkAddress, UDPClientSocket
from utils import or_valueerror, StoppableThread

DEXTRA_PORT = 30001

class Packet(object):
    pass

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
        if (len(data) == 11):
            raise NotImplemented

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

class DExtraDisconnectAckPacket(Packet):
    @classmethod
    def from_data(cls, data):
        or_valueerror(len(data) == 12)
        or_valueerror(data == 'DISCONNECTED')
        return cls()

    def to_data(self):
        return 'DISCONNECTED'

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

class DExtraDVHeaderPacket(Packet):
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

class DExtraDVFramePacket(Packet):
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

class DExtraReceiveThread(StoppableThread):
    def __init__(self, callsign, sock, name='DExtraReceiveThread'):
        self.logger = logging.getLogger(self.__class__.__name__)

        StoppableThread.__init__(self, name=name)
        self._sleep_period = 0.01

        self.callsign = callsign
        self.sock = sock
        self.queue = Queue.Queue()

    def loop(self):
        while True: # While there is data to read from the socket
            data = self.sock.read()
            if not data:
                return

            try:
                packet = DExtraDVFramePacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received dvframe packet from stream %s%s', packet.stream_id, ' (last)' if packet.is_last else '')
                self.queue.put(packet)
                continue

            try:
                packet = DExtraDVHeaderPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received dvheader packet from stream %s', packet.stream_id)
                self.queue.put(packet)
                continue

            try:
                packet = DExtraConnectAckPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received connect ack packet')
                self.queue.put(packet)
                continue

            try:
                packet = DExtraConnectNackPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received connect nack packet')
                self.queue.put(packet)
                continue

            try:
                packet = DExtraDisconnectPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received disconnect packet from %s', packet.src_callsign)
                self.queue.put(packet)
                continue

            try:
                packet = DExtraDisconnectAckPacket.from_data(data)
            except ValueError:
                pass
            else:
                self.logger.debug('received disconnect ack packet')
                self.queue.put(packet)
                continue

            try:
                packet = DExtraKeepAlivePacket.from_data(data)
            except ValueError:
                pass
            else:
                # self.logger.debug('received keepalive packet from %s', packet.src_callsign)
                keepalive_packet = DExtraKeepAlivePacket(self.callsign)
                self.sock.write(keepalive_packet.to_data())
                continue

            self.logger.warning('unknown data received')

class DExtraConnection(object):
    def __init__(self, callsign, reflector_callsign, reflector_module, reflector_address):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with callsign %s reflector callsign %s reflector_module %s reflector_address %s', callsign, reflector_callsign, reflector_module, reflector_address)

        self.callsign = callsign
        self.reflector_callsign = reflector_callsign
        self.reflector_module = reflector_module
        self.reflector_address = reflector_address

        self.sock = None
        self.receive_thread = None

    def _connect(self, timeout=3):
        connect_packet = DExtraConnectPacket(self.callsign, DSTARModule(' '), self.reflector_module, 1)
        self.sock.write(connect_packet.to_data())

        clock = time.clock()
        limit = clock + timeout
        while (clock < limit):
            packet = self.read(timeout=limit - clock)
            if packet:
                if isinstance(packet, DExtraConnectAckPacket):
                    return True
                if isinstance(packet, DExtraConnectNackPacket):
                    return False
            clock = time.clock()
        return False

    def _disconnect(self, timeout=3):
        disconnect_packet = DExtraDisconnectPacket(self.callsign, DSTARModule(' '))
        self.sock.write(disconnect_packet.to_data())

        clock = time.clock()
        limit = clock + timeout
        while (clock < limit):
            packet = self.read(timeout=limit - clock)
            if packet and isinstance(packet, DExtraDisconnectAckPacket):
                return True
            clock = time.clock()
        return False

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

        self.receive_thread = DExtraReceiveThread(self.callsign, self.sock)
        self.receive_thread.start()

        return self._connect()

    def close(self):
        while not self.receive_thread.queue.empty():
            self.receive_thread.queue.get()

        self._disconnect()

        self.receive_thread.join()

        if self.sock:
            self.sock.close()
        self.sock = None

    def __enter__(self):
        if not self.open():
            raise Exception('can not open DExtra connection to %s' % (self.reflector_address,))
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def read(self, timeout=3):
        elapsed = 0
        step = 0.01
        while elapsed < timeout:
            try:
                return self.receive_thread.queue.get(True, step)
            except Queue.Empty:
                time.sleep(step)
                elapsed += step
                continue
        return None

def dextra_recorder():
    import sys
    import argparse

    parser = argparse.ArgumentParser(description='DExtra recorder. Connects to DExtra server and records traffic.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='enable debug output')
    parser.add_argument('callsign', help='your callsign')
    parser.add_argument('reflector', help='reflector\'s callsign')
    parser.add_argument('module', help='reflector\'s module')
    parser.add_argument('address', help='reflector\'s hostname or IP address')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s [%(levelname)7s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if args.verbose else logging.INFO)

    try:
        callsign = DSTARCallsign(args.callsign)
        reflector_callsign = DSTARCallsign(args.reflector)
        reflector_module = DSTARModule(args.module)
        reflector_address = NetworkAddress(args.address, DEXTRA_PORT)
    except ValueError:
        print parser.print_help()
        sys.exit(1)

    try:
        with DExtraConnection(callsign, reflector_callsign, reflector_module, reflector_address) as conn:
            try:
                while True:
                    packet = conn.read()
            except KeyboardInterrupt:
                pass
    except Exception as e:
        print str(e)
        sys.exit(1)

if __name__ == '__main__':
    dextra_recorder()
