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

def dv_decoder():
    parser = argparse.ArgumentParser(description='D-STAR decoder. Decodes streams into samples.')
    parser.add_argument('-v', '--verbose', default=False, action='store_true', help='enable debug output')
    parser.add_argument('input', help='name of file to decode (DVTool format)')
    parser.add_argument('output', help='name of file to write (WAV format)')
    args = parser.parse_args()

    logging.basicConfig(format='%(asctime)s [%(levelname)7s] %(name)s: %(message)s',
                        datefmt='%Y-%m-%d %H:%M:%S',
                        level=logging.DEBUG if args.verbose else logging.INFO)
    logger = logging.getLogger(os.path.basename(sys.argv[0]))

    try:
        with DVToolFile(args.input) as f:
            stream = f.read()
    except Exception as e:
        raise
        logger.error(str(e))
        sys.exit(1)

    header = stream[0]
    if not isinstance(header, DVHeaderPacket):
        logger.error('first packet in stream is not a header')
        sys.exit(1)

    # Determine vocoder (SV9OAN extension)
    version = header.dstar_header.flag_3 & 0xff
    if version == 0:
        vocoder = 'ambe'
        logger.info('stream encoded with AMBE vocoder')
    elif version & 0x01 == 0x01:
        # The first bit controls the vocoder type:
        #   0: AMBE (backwards compatible)
        #   1: Codec 2
        #
        # The second bit differentiates between modes, while the third
        # enables FEC (not implemented):
        # This results in the following combinations of bits 2 and 3:
        #   00: 3200 mode (160 samples/20 ms into 64 bits)
        #   01: 2400 mode (160 samples/20 ms into 48 bits)
        #   10: 3200 mode (160 samples/20 ms into 64 bits + ? bits FEC)
        #   11: 2400 mode (160 samples/20 ms into 48 bits + ? bits FEC)
        #
        # The space available in the frame is 72 bits, so that leaves
        # us with 8 bits in the case of 3200 mode (is it enough?) and
        # 24 in the case of 2400 mode. The latter is enough for 22 bits
        # of FEC, as FreeDV does in 2400 and 1850 modes.
        vocoder = 'codec2'
        mode = pydv.codec2.MODE_2400 if (version & 0x02 == 0x02) else pydv.codec2.MODE_3200
        fec = True if (version & 0x04 == 0x04) else False # Not implemented
        logger.info('stream encoded with Codec 2 vocoder (mode %s, fec: %s)',
                    '2400' if mode == pydv.codec2.MODE_2400 else '3200',
                    'on' if fec else 'off')

        if fec:
            logger.error('FEC is not implemented')
            sys.exit(1)

    wavef = wave.open(args.output,'w')
    wavef.setnchannels(1)
    wavef.setsampwidth(2)
    wavef.setframerate(8000)

    if vocoder == 'ambe':
        state = pydv.mbelib.init_state()
        for packet in stream:
            if not isinstance(packet, DVFramePacket):
                continue
            samples = pydv.mbelib.decode_dstar(state, packet.dstar_frame.dvcodec)
            data = struct.pack('<160h', *samples)
            wavef.writeframes(data)
    else:
        state = pydv.codec2.init_state(mode)
        for packet in stream:
            if not isinstance(packet, DVFramePacket):
                continue
            dvcodec = packet.dstar_frame.dvcodec[:6] if mode == pydv.codec2.MODE_2400 else packet.dstar_frame.dvcodec[:8]
            data = pydv.codec2.decode(state, dvcodec)
            wavef.writeframes(data)

    wavef.close()
    logger.info('output written to %s' % args.output)

def main():
    dv_decoder()

if __name__ == '__main__':
    dv_decoder()
