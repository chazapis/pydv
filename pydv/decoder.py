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
        # The second bit differentiates between modes:
        #   0: Codec 2 3200 (160 samples/20 ms into 64 bits)
        #   1: Codec 2 2400 (160 samples/20 ms into 48 bits) + FEC (22 bits)
        #
        # With Codec 2 2400, we are protecting the first 24 bits of the
        # voice datawith two applications of the (23, 12) Golay code.
        vocoder = 'codec2'
        mode = 0 if (version & 0x03 == 0x01) else 1
        codec2_mode = pydv.codec2.CODEC2_MODE_2400 if mode == 1 else pydv.codec2.CODEC2_MODE_3200
        logger.info('stream encoded with Codec 2 vocoder (mode: %s, fec: %s)',
                    '2400' if mode == 1 else '3200',
                    'on' if mode == 1 else 'off')

    wavef = wave.open(args.output, 'w')
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
        state = pydv.codec2.codec2_create(codec2_mode)
        bit_count = 0
        bit_errors = 0
        if mode == 1:
            pydv.codec2.golay23_init()
        for packet in stream:
            if not isinstance(packet, DVFramePacket):
                continue

            dvcodec = packet.dstar_frame.dvcodec
            if mode == 1:
                received_codeword = ((ord(dvcodec[0]) << 15) |
                                     (((ord(dvcodec[1]) >> 4) & 0xF) << 11) |
                                     (ord(dvcodec[6]) << 3) |
                                     ((ord(dvcodec[7]) >> 5) & 0x7))
                corrected_codeword = pydv.codec2.golay23_decode(received_codeword)
                bit_count += 23
                bit_errors += pydv.codec2.golay23_count_errors(received_codeword, corrected_codeword)

                corrected_dvcodec = chr((corrected_codeword >> 15) & 0xFF)
                partial_byte = ((corrected_codeword >> 11) & 0xF) << 4

                received_codeword = (((ord(dvcodec[1]) & 0xF) << 19) |
                                     (ord(dvcodec[2]) << 11) |
                                     ((ord(dvcodec[7]) & 0x1F) << 6) |
                                     ((ord(dvcodec[8]) >> 2) & 0x3F))
                corrected_codeword = pydv.codec2.golay23_decode(received_codeword)
                bit_count += 23
                bit_errors += pydv.codec2.golay23_count_errors(received_codeword, corrected_codeword)

                corrected_dvcodec += chr(partial_byte | ((corrected_codeword >> 19) & 0xF))
                corrected_dvcodec += chr((corrected_codeword >> 11) & 0xFF)

                dvcodec = corrected_dvcodec + dvcodec[3:]

            dvcodec = dvcodec[:6] if mode == 1 else dvcodec[:8]
            data = pydv.codec2.codec2_decode(state, dvcodec)
            wavef.writeframes(data)
        if mode == 1:
            logger.info('total FEC bits: %d, bit errors: %d', bit_count, bit_errors)

    wavef.close()
    logger.info('output written to %s', args.output)

def main():
    dv_decoder()

if __name__ == '__main__':
    dv_decoder()
