# Copyright (C) 2017 by Antony Chazapis SV9OAN
#
# Based on OpenDV:
# Copyright (C) 2006-2013 by Jonathan Naylor G4KLX
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

from udp import UDPSocket

class DExtraConnection(object):
    def __init__(self, address, port, callsign):
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug('initialized with (\'%s\', %d)', address, port)

        self.address = address
        self.port = port
        self.callsign = callsign

        self.sock = None

    def open(self):
        assert(self.sock is None)

        try:
            self.sock = UDPSocket(address, port)
            self.sock.open()
        except Exception as e:
            self.logger.error('can not open UDP socket: %s', str(e))
            self.sock = None
            return False

        return True

    def close(self):
        assert(self.sock)

        try:
            self.sock.close()
        except:
            pass
        self.sock = None

