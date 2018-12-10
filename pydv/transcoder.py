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
import wave
import struct

import pydv.mbelib
import pydv.codec2

from stream import DVHeaderPacket, DVFramePacket
from dvtool import DVToolFile

def dv_transcoder():
    parser = argparse.ArgumentParser(description='D-STAR transcoder. Transcodes recordings from AMBE to Codec 2.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='enable debug output')
    parser.add_argument('-m', '--mode', default='3200', help='Codec 2 mode (2400 or 3200)')
    parser.add_argument('-f', '--fec', default=False, action='store_true', help='enable FEC')
    parser.add_argument('input', help='name of file to transcode (DVTool format)')
    parser.add_argument('output', help='name of file to write (DVTool format)')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s [%(levelname)7s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(os.path.basename(sys.argv[0]))

    if args.mode not in ('2400', '3200'):
        logger.error('mode can be either 2400 or 3200')
        sys.exit(1)
    if args.fec:
        logger.error('FEC is not implemented')
        sys.exit(1)

    try:
        with DVToolFile(args.input) as f:
            stream = f.read()
    except Exception as e:
        logger.error(str(e))
        sys.exit(1)

    header = stream[0]
    if not isinstance(header, DVHeaderPacket):
        logger.error('first packet in stream is not a header')
        sys.exit(1)

    # Determine vocoder and set (SV9OAN extension)
    version = header.dstar_header.flag_3 & 0xff
    if version & 0x01 == 0x01:
        logger.info('stream already encoded with Codec 2')
        sys.exit(0)
    
    version = 0x01
    if args.mode == '2400':
        version |= 0x02
    # if args.fec:
    #     version &= 0x04
    header.dstar_header.flag_3 = version

    state_mbelib = pydv.mbelib.init_state()
    mode = pydv.codec2.MODE_2400 if (args.mode == '2400') else pydv.codec2.MODE_3200
    state_codec2 = pydv.codec2.init_state(mode)
    for packet in stream:
        if not isinstance(packet, DVFramePacket):
            continue
        samples = pydv.mbelib.decode_dstar(state_mbelib, packet.dstar_frame.dvcodec)
        data = struct.pack('<160h', *samples)
        packet.dstar_frame.dvcodec = pydv.codec2.encode(state_codec2, data)

    with DVToolFile(args.output) as f:
        f.write(stream)

def main():
    dv_transcoder()

if __name__ == '__main__':
    dv_transcoder()
