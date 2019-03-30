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

import pydv.codec2

from dstar import DSTARHeader, DSTARFrame, DSTARCallsign, DSTARSuffix
from stream import DVHeaderPacket, DVFramePacket
from dvtool import DVToolFile

def dv_encoder():
    parser = argparse.ArgumentParser(description='D-STAR encoder. Encodes samples into streams.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='enable debug output')
    parser.add_argument('-t', '--type', default=0, type=int, help='vocoder type (0: Codec 2 mode 3200, 1: Codec 2 mode 2400 with FEC)')
    parser.add_argument('input', help='name of file to encode (WAV format)')
    parser.add_argument('output', help='name of file to write (DVTool format)')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s [%(levelname)7s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(os.path.basename(sys.argv[0]))

    if args.type not in (0, 1):
        logger.error('type can be either 0 or 1')
        sys.exit(1)

    wavef = wave.open(args.input, 'r')
    if (wavef.getnchannels() != 1 or wavef.getsampwidth() != 2 or wavef.getframerate() != 8000):
        logger.error('input file must have 1 channel, 16 bits/sample, and 8000 samples/sec')
        sys.exit(1)

    version = 0x01
    if args.type == 1:
        version |= 0x02
    dstar_header = DSTARHeader(0,
                               0,
                               version,
                               DSTARCallsign('NOCALL'),
                               DSTARCallsign('NOCALL'),
                               DSTARCallsign('NOCALL'),
                               DSTARCallsign('NOCALL'),
                               DSTARSuffix('    '))
    header = DVHeaderPacket(0, 0, 0, 0, dstar_header)
    stream = [header]
    packet_id = 0

    mode = pydv.codec2.CODEC2_MODE_2400 if (args.type == 1) else pydv.codec2.CODEC2_MODE_3200
    state = pydv.codec2.codec2_create(mode)
    if args.type == 1:
        pydv.codec2.golay23_init()
    while True:
        data = wavef.readframes(160)
        if len(data) < 160:
            break

        dvcodec = pydv.codec2.codec2_encode(state, data)
        if args.type == 1:
            fec_input = (ord(dvcodec[0]) << 4) | ((ord(dvcodec[1]) >> 4) & 0xF)
            fec_data = pydv.codec2.golay23_encode(fec_input)
            dvcodec += chr((fec_data >> 3) & 0xFF)
            partial_byte = (fec_data & 0x7) << 5

            fec_input = ((ord(dvcodec[1]) & 0xF) << 8) | ord(dvcodec[2])
            fec_data = pydv.codec2.golay23_encode(fec_input)
            dvcodec += chr(partial_byte | ((fec_data >> 6) & 0x1F))
            dvcodec += chr((fec_data & 0x3F) << 2)

        dstar_frame = DSTARFrame(dvcodec, '\x55\x2d\x16' if (packet_id % 21 == 0) else '')
        packet = DVFramePacket(0, 0, 0, 0, packet_id % 21, dstar_frame)
        stream.append(packet)

        packet_id += 1

    # Mark last packet
    packet = stream[-1]
    packet.packet_id |= 64

    wavef.close()

    with DVToolFile(args.output) as f:
        f.write(stream)

def main():
    dv_encoder()

if __name__ == '__main__':
    dv_encoder()
