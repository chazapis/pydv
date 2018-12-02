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

import sys
import argparse
import logging

from dstar import DSTARCallsign, DSTARModule
from dextra import DExtraConnection, DExtraDisconnectedError
from stream import DVHeaderPacket, DVFramePacket
from network import NetworkAddress
from dvtool import DVToolFile

def dv_recorder():
    parser = argparse.ArgumentParser(description='D-STAR recorder. Connects to reflector and records traffic.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='enable debug output')
    parser.add_argument('callsign', help='your callsign')
    parser.add_argument('reflector', help='reflector\'s callsign')
    parser.add_argument('module', help='reflector\'s module')
    parser.add_argument('address', help='reflector\'s hostname or IP address')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s [%(levelname)7s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(sys.argv[0])

    try:
        callsign = DSTARCallsign(args.callsign)
        reflector_callsign = DSTARCallsign(args.reflector)
        reflector_module = DSTARModule(args.module)
        reflector_address = NetworkAddress(args.address, DExtraConnection.DEFAULT_PORT)
    except ValueError:
        print parser.print_help()
        sys.exit(1)

    try:
        stream_id = None
        with DExtraConnection(callsign, DSTARModule(' '), reflector_callsign, reflector_module, reflector_address) as conn:
            try:
                while True:
                    packet = conn.read()
                    if isinstance(packet, DVHeaderPacket):
                        if packet.stream_id != stream_id:
                            stream_id = packet.stream_id
                            stream = [packet]
                    elif isinstance(packet, DVFramePacket):
                        if packet.stream_id == stream_id:
                            stream.append(packet)
                            if packet.is_last:
                                with DVToolFile('%s.dvtool' % stream_id) as f:
                                    f.write(stream)
                                stream_id = None
                    else:
                        pass
            except (DExtraDisconnectedError, KeyboardInterrupt):
                pass
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

def main():
    dv_recorder()

if __name__ == '__main__':
    dv_recorder()