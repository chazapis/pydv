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

import socket
import select
import logging

from collections import namedtuple

NetworkAddress = namedtuple('NetworkAddress', ['host', 'port'])

class UDPClientSocket(object):
    def __init__(self, remote_address, local_address=None):
        assert(isinstance(remote_address, NetworkAddress))
        assert(remote_address.port > 0)
        if local_address is not None:
            assert(isinstance(local_address, NetworkAddress))
        else:
            local_address = NetworkAddress('0.0.0.0', 0)

        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with remote %s local %s', remote_address, local_address)

        try:
            self.remote_address = NetworkAddress(self._resolve(remote_address.host), remote_address.port)
        except:
            self.logger.error('cannot find address for host %s', remote_address.host)
            raise
        self.local_address = local_address

        self.sock = None

    def _resolve(self, host):
        try:
            socket.inet_aton(host)
            return host
        except socket.error:
            pass

        try:
            return socket.gethostbyname(host)
        except:
            raise ValueError

    def open(self):
        assert(self.sock is None)

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(self.local_address)
        self.logger.debug('socket opened')

    def close(self):
        assert(self.sock)

        if self.sock:
            self.sock.close()
        self.sock = None
        self.logger.debug('socket closed')

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def read(self, length):
        assert(self.sock)

        # Check that the recvfrom() won't block
        readable, writable, exceptional = select.select([self.sock], [], [], 0) # Return immediately
        if not readable:
            return None

        data, address = self.sock.recvfrom(length)
        self.logger.debug('read %d bytes from %s: %s', len(data), address, data)

        # Check if the data is for us, only check the IP address now (used to include port number too)
        if self.remote_address.host != address[0]:
            return None;

        return data

    def write(self, data):
        assert(self.sock)

        self.logger.debug('write %d bytes to %s: %s', len(data), self.remote_address, data)
        length = self.sock.sendto(data, self.remote_address)
        self.logger.debug('written %d bytes', length)

        if length != len(data):
            return False
        return True

if __name__ == '__main__':
    import threading

    from time import sleep

    logging.basicConfig(format='%(asctime)s [%(levelname)7s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG)

    def server():
        logger = logging.getLogger('server')
    
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        server_address = NetworkAddress('0.0.0.0', 20000)
        sock.bind(server_address)
        logger.debug('server listening at %s', server_address)

        while True:
            data, address = sock.recvfrom(256)
            logger.debug('echoing %d bytes back to %s: %s', len(data), address, data)
            length = sock.sendto(data, address)
            logger.debug('echoed %d bytes', length)

    def client():
        sleep(1)
        data = 'test'
        with UDPClientSocket(NetworkAddress('127.0.0.1', 20000)) as udp_socket:
            udp_socket.write(data)
            while True:
                if udp_socket.read(256) == data:
                    break
                sleep(0.1)

    t = threading.Thread(target=client)
    t.start()

    try:
        server()
    except KeyboardInterrupt:
        pass
