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

import os
import sys
import argparse
import logging
import random

from time import sleep

from dstar import DSTARCallsign, DSTARSuffix, DSTARModule
from dextra import DExtraConnection, DExtraOpenConnection
from dplus import DPlusConnection
from stream import DisconnectedError
from network import NetworkAddress
from dvtool import DVToolFile

def dv_player():
    parser = argparse.ArgumentParser(description='D-STAR player. Connects to reflector and plays back recordings.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='enable debug output')
    parser.add_argument('-p', '--protocol', default='auto', help='network protocol (dextra, dextraopen, dplus, or auto)')
    parser.add_argument('callsign', help='your callsign')
    parser.add_argument('reflector', help='reflector\'s callsign')
    parser.add_argument('module', help='reflector\'s module')
    parser.add_argument('address', help='reflector\'s hostname or IP address')
    parser.add_argument('input', help='name of file to play back (DVTool format)')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s [%(levelname)7s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(os.path.basename(sys.argv[0]))

    try:
        callsign = DSTARCallsign(args.callsign)
        reflector_callsign = DSTARCallsign(args.reflector)
        reflector_module = DSTARModule(args.module)
        if args.protocol == 'dextra':
            connection_class = DExtraConnection
        elif args.protocol == 'dextraopen':
            connection_class = DExtraOpenConnection
        elif args.protocol == 'dplus':
            connection_class = DPlusConnection
        elif args.protocol == 'auto':
            if str(reflector_callsign).startswith('REF'):
                connection_class = DPlusConnection
            elif str(reflector_callsign).startswith('ORF'):
                connection_class = DExtraOpenConnection
            else:
                connection_class = DExtraConnection
        else:
            raise ValueError
        reflector_address = NetworkAddress(args.address, connection_class.DEFAULT_PORT)
    except ValueError:
        parser.print_help()
        sys.exit(1)

    try:
        with DVToolFile(args.input) as f:
            stream = f.read()
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

    header = stream[0]
    header.dstar_header.my_callsign = callsign
    header.dstar_header.my_suffix = DSTARSuffix('    ')
    header.dstar_header.ur_callsign = DSTARCallsign('CQCQCQ')
    header.dstar_header.repeater_1_callsign = DSTARCallsign(str(reflector_callsign)[:7] + str(reflector_module))
    header.dstar_header.repeater_2_callsign = DSTARCallsign(str(reflector_callsign)[:7] + 'G')
    stream_id = random.getrandbits(16)

    try:
        with connection_class(callsign, DSTARModule(' '), reflector_callsign, reflector_module, reflector_address) as conn:
            try:
                for packet in stream:
                    packet.stream_id = stream_id
                    conn.write(packet)
                    sleep(0.02)
            except (DisconnectedError, KeyboardInterrupt):
                pass
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

def main():
    dv_player()

if __name__ == '__main__':
    dv_player()
