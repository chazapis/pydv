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
import wave
import struct

import pydv.mbelib

from stream import DVFramePacket
from dvtool import DVToolFile

def dv_decoder():
    parser = argparse.ArgumentParser(description='D-STAR decoder. Decodes recordings.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='enable debug output')
    parser.add_argument('input', help='name of file to decode (DVTool format)')
    parser.add_argument('output', help='name of file to write (WAV format)')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s [%(levelname)7s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(sys.argv[0])

    try:
        with DVToolFile(args.input) as f:
            stream = f.read()
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

    wavef = wave.open(args.output,'w')
    wavef.setnchannels(1)
    wavef.setsampwidth(2)
    wavef.setframerate(8000)

    state = pydv.mbelib.init_state()
    for packet in stream:
        if not isinstance(packet, DVFramePacket):
            continue
        samples = pydv.mbelib.decode_dstar(state, packet.dstar_frame.ambe)
        data = struct.pack('<160h', *samples)
        wavef.writeframes(data)

    wavef.close()

def main():
    dv_decoder()

if __name__ == '__main__':
    dv_decoder()
